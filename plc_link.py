"""
Project B · PLC 통신 계층 (기본: MX OPC Server / OPC DA, 선택: Modbus TCP)

measurement_engine.py serve 와 hmi_counter_monitor.py 가 이 모듈로 PLC 디바이스를 읽고 씁니다.
코드에서는 PLC 디바이스 이름(D1700, M1920, X1900 …)만 다루고, 통신 방식별 주소 변환은 여기서 합니다.

1) OPC (기본, 결정 D17)
   GX Simulator2(또는 실물 PLC) ↔ MX OPC Server 6 ↔ 이 모듈 (OPC DA 클라이언트)
   - OPC DA 는 32비트 COM 이므로 **32비트 Python + pywin32** 로 실행합니다.
       pymanager install 3.12-32
       python3.12-32 -m pip install pywin32
   - MX OPC 는 Configurator 에 **등록된 태그**만 읽고 쓸 수 있습니다.
     태그 이름은 디바이스 이름과 같게 등록합니다(QSIM.D1700 = D1700). 목록: tools/mxopc_tags.py
   - COM 래퍼: OPC.SiemensDAAuto (OPC DA Automation 2.0, 32비트). OPC.Automation 이 있으면 --opc-wrapper 로 변경.

2) Modbus TCP (선택, --link modbus)
   Factory I/O Modbus TCP Server 에 직접 붙을 때(구성 다) 또는 Modbus 모듈(QJ71MT91)이 있을 때.
   디바이스 번호 = Modbus 주소로 가정 (D1700 → holding register 1700, M1920 → coil 1920).
"""

import re
import struct
import sys

OPC_DS_DEVICE = 2          # OPC 데이터 소스: 장치에서 직접 읽기 (핸드셰이크 비트를 캐시 지연 없이 읽음)
QUALITY_GOOD = 192

_DEV_RE = re.compile(r"^([DMXYLBW])([0-9A-F]+)$")
_HEX_DEVICES = ("X", "Y", "B", "W")   # 16진 번호 디바이스


def split_device(dev):
    """'D1700' → ('D', 1700), 'X1903' → ('X', 0x1903)."""
    m = _DEV_RE.match(dev.upper())
    if not m:
        raise ValueError(f"디바이스 이름 형식 오류: {dev}")
    kind, num = m.groups()
    return kind, int(num, 16 if kind in _HEX_DEVICES else 10)


def device_name(kind, number):
    return f"{kind}{number:X}" if kind in _HEX_DEVICES else f"{kind}{number}"


def word_range(start, count):
    """'D1700', 4 → ['D1700', 'D1701', 'D1702', 'D1703']"""
    kind, n = split_device(start)
    return [device_name(kind, n + i) for i in range(count)]


class LinkError(IOError):
    pass


class OpcLink:
    """MX OPC Server(OPC DA) 연결. 태그 이름 = 디바이스 이름."""

    def __init__(self, server="Mitsubishi.MXOPC.6", device="QSIM", wrapper="OPC.SiemensDAAuto"):
        if struct.calcsize("P") * 8 != 32:
            sys.exit("OPC 연결은 32비트 Python 으로 실행하세요 (예: python3.12-32 measurement_engine.py serve). "
                     "OPC DA Automation 래퍼가 32비트 전용입니다. Modbus 로 붙으려면 --link modbus")
        try:
            import win32com.client
        except ImportError:
            sys.exit("pywin32 가 필요합니다: python3.12-32 -m pip install pywin32")
        self.device = device
        self.label = f"OPC {server} / 장치 {device}"
        try:
            self._srv = win32com.client.Dispatch(wrapper)
            self._srv.Connect(server)
        except Exception as e:
            sys.exit(f"OPC 서버 연결 실패: {server} ({e}). MX OPC Server 설치 · 실행 상태를 확인하세요.")
        if self._srv.ServerState != 1:
            print(f"[OPC] 경고: ServerState={self._srv.ServerState} (1=RUNNING 아님)")
        self._group = self._srv.OPCGroups.Add("projectB")
        self._group.IsActive = True
        self._items = {}
        self._handle = 1

    def _item(self, dev):
        item = self._items.get(dev)
        if item is None:
            item_id = f"{self.device}.{dev}"
            try:
                item = self._group.OPCItems.AddItem(item_id, self._handle)
            except Exception as e:
                hr = _com_hresult(e)
                raise LinkError(f"OPC 태그 {item_id} 등록 실패 0x{hr:08X}"
                                + (" (없는 태그 → MX OPC Configurator에 tools/mxopc_tags.py 목록 등록 필요)"
                                   if hr == 0xC0040007 else "")) from None
            self._handle += 1
            self._items[dev] = item
        return item

    def read(self, dev):
        value, quality, _ = self._item(dev).Read(OPC_DS_DEVICE)
        if quality != QUALITY_GOOD:
            raise LinkError(f"OPC {self.device}.{dev} 품질 {quality} (192 = Good 아님)")
        return int(value)

    def write(self, dev, value):
        kind, _ = split_device(dev)
        self._item(dev).Write(bool(value) if kind in ("M", "X", "Y", "L", "B") else int(value))

    def read_words(self, start, count=1):
        return [self.read(d) for d in word_range(start, count)]

    def write_words(self, start, values):
        for d, v in zip(word_range(start, len(values)), values):
            self.write(d, v)

    def write_bit(self, dev, state):
        self.write(dev, bool(state))

    def close(self):
        try:
            self._srv.OPCGroups.RemoveAll()
            self._srv.Disconnect()
        except Exception:
            pass


def client_call(fn, *a, unit, **kw):
    """pymodbus 버전별 unit 인자명 차이(slave / device_id / unit) 흡수 (tools/modbus_probe.py 도 사용)."""
    for key in ("device_id", "slave", "unit"):
        try:
            return fn(*a, **{key: unit}, **kw)
        except TypeError:
            continue
    return fn(*a, **kw)


class ModbusLink:
    """Modbus TCP 연결. D → holding register, M/X/Y → coil (번호 그대로)."""

    def __init__(self, host, port=502, unit=1):
        try:
            from pymodbus.client import ModbusTcpClient
        except ImportError:
            sys.exit("pymodbus 가 필요합니다: pip install pymodbus")
        self.unit = unit
        self.label = f"Modbus {host}:{port}"
        self._c = ModbusTcpClient(host, port=port)
        if not self._c.connect():
            sys.exit(f"Modbus 연결 실패: {host}:{port}")

    def _call(self, fn, *a, **kw):
        rr = client_call(fn, *a, unit=self.unit, **kw)
        if rr.isError():
            raise LinkError(str(rr))
        return rr

    def read_words(self, start, count=1):
        kind, n = split_device(start)
        if kind != "D":
            raise ValueError("Modbus 워드 읽기는 D 디바이스만")
        return list(self._call(self._c.read_holding_registers, n, count=count).registers)

    def write_words(self, start, values):
        kind, n = split_device(start)
        self._call(self._c.write_registers, n, list(values))

    def write_bit(self, dev, state):
        kind, n = split_device(dev)
        self._call(self._c.write_coil, n, bool(state))

    def close(self):
        self._c.close()


def _com_hresult(e):
    hr = getattr(e, "hresult", None) or (e.args[0] if getattr(e, "args", None) else 0)
    exc = getattr(e, "excepinfo", None) or (e.args[2] if len(getattr(e, "args", ())) > 2 else None)
    if exc and len(exc) > 5 and exc[5]:
        hr = exc[5]   # DISP_E_EXCEPTION 안의 실제 OPC 오류 코드
    return (hr or 0) & 0xFFFFFFFF


def add_link_args(p, default_port=502):
    """serve / HMI 모니터 공통 통신 옵션."""
    g = p.add_argument_group("PLC 통신 (기본 OPC: MX OPC Server)")
    g.add_argument("--link", choices=("opc", "modbus"), default="opc",
                   help="opc: MX OPC Server 경유(기본, 32비트 Python) / modbus: Modbus TCP 직접")
    g.add_argument("--opc-server", default="Mitsubishi.MXOPC.6")
    g.add_argument("--opc-device", default="QSIM", help="MX OPC Configurator 장치 이름 (기본 QSIM = GX Simulator2)")
    g.add_argument("--opc-wrapper", default="OPC.SiemensDAAuto")
    g.add_argument("--host", default="192.168.0.XXX",
                   help="--link modbus 일 때 접속 주소. 시연 PC가 정해지면 192.168.0.XXX 를 실제 주소로 바꿉니다")
    g.add_argument("--port", type=int, default=default_port)
    g.add_argument("--unit", type=int, default=1)


def open_link(args):
    if args.link == "opc":
        return OpcLink(args.opc_server, args.opc_device, args.opc_wrapper)
    if "XXX" in args.host:
        sys.exit("--link modbus 는 --host 에 실제 주소가 필요합니다 (시연 PC 미정: 192.168.0.XXX). 예: --host 192.168.0.213")
    return ModbusLink(args.host, args.port, args.unit)
