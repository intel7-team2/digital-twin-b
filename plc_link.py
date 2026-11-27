"""
Project B · PLC 통신 계층 (기본: MX OPC Server / OPC DA, 선택: Modbus TCP)

measurement_engine.py serve 와 hmi_counter_monitor.py 가 이 모듈로 PLC 디바이스를 읽고 씁니다.
코드에서는 PLC 디바이스 이름(D1700, M1920, X1900 …)만 다루고, 통신 방식별 주소 변환은 여기서 합니다.

1) OPC (기본, 결정 D17 · D21)
   GX Simulator2(또는 실물 PLC) ↔ MX OPC Server 6 ↔ 이 모듈 (OPC DA 클라이언트)
   - 기본(--opc-wrapper auto): **OPC DA 2.0 커스텀 인터페이스로 직접** 붙습니다(ctypes, 추가 설치 없음).
     MX OPC 는 별도 실행 파일(out-of-proc)이라 OPC Core Components 의 프록시만 있으면 **64비트 · 32비트 Python 모두** 됩니다.
     직접 연결이 안 되면 32비트 Python 에서는 아래 Automation 래퍼로 다시 시도합니다.
   - Automation 래퍼(--opc-wrapper OPC.SiemensDAAuto 등): 32비트 Python + pywin32 필요 (이전 방식).
   - MX OPC 는 Configurator 에 **등록된 태그**만 읽고 쓸 수 있습니다.
     태그 이름은 디바이스 이름과 같게 등록합니다(QSIM.D1700 = D1700). 목록: tools/mxopc_tags.py
   - 읽기는 기본으로 장치에서 직접(--opc-source device). Simulate 장치 시험은 --opc-source cache.

2) Modbus TCP (선택, --link modbus)
   Factory I/O Modbus TCP Server 에 직접 붙을 때(구성 다) 또는 Modbus 모듈(QJ71MT91)이 있을 때.
   디바이스 번호 = Modbus 주소로 가정 (D1700 → holding register 1700, M1920 → coil 1920).

3) MC 프로토콜 3E 바이너리 (선택, --link mc, D21)
   MX OPC 를 쓸 수 없는 PC 에서 실물 PLC 내장 이더넷(또는 hmi_mc_relay.py)에 직접 붙을 때. pymcprotocol 필요.
   PLC 쪽 오픈 설정(MC 프로토콜 · TCP · 바이너리 · 포트)이 있어야 합니다. 기본 포트 5000.
"""

import ctypes
import re
import struct
import sys
import threading
import time
import uuid

OPC_DS_CACHE = 1           # OPC 데이터 소스: 서버 캐시 (Simulate 장치 시험용)
OPC_DS_DEVICE = 2          # OPC 데이터 소스: 장치에서 직접 읽기 (핸드셰이크 비트를 캐시 지연 없이 읽음)
QUALITY_GOOD = 192
QUALITY_WAITING = 32       # OPC_QUALITY_WAITING_FOR_INITIAL_DATA

_DEV_RE = re.compile(r"^([DMXYLBW])([0-9A-F]+)$")
_HEX_DEVICES = ("X", "Y", "B", "W")   # 16진 번호 디바이스
_BIT_DEVICES = ("M", "X", "Y", "L", "B")


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


class OpcAutomationLink:
    """MX OPC Server 연결 (OPC DA Automation 래퍼 경유, 32비트 Python + pywin32). 태그 이름 = 디바이스 이름."""

    def __init__(self, server="Mitsubishi.MXOPC.6", device="QSIM", wrapper="OPC.SiemensDAAuto", source=OPC_DS_DEVICE):
        if struct.calcsize("P") * 8 != 32:
            sys.exit("OPC 연결은 32비트 Python 으로 실행하세요 (예: python3.12-32 measurement_engine.py serve). "
                     "OPC DA Automation 래퍼가 32비트 전용입니다. Modbus 로 붙으려면 --link modbus")
        try:
            import win32com.client
        except ImportError:
            sys.exit("pywin32 가 필요합니다: python3.12-32 -m pip install pywin32")
        self.device = device
        self.label = f"OPC {server} / 장치 {device} (래퍼 {wrapper})"
        self.source = source
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
        value, quality, _ = self._item(dev).Read(self.source)
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


class _GUID(ctypes.Structure):
    _fields_ = [("b", ctypes.c_ubyte * 16)]

    def __init__(self, text):
        super().__init__()
        ctypes.memmove(self.b, uuid.UUID(text).bytes_le, 16)


class _FILETIME(ctypes.Structure):
    _fields_ = [("lo", ctypes.c_ulong), ("hi", ctypes.c_ulong)]


class _VARIANT(ctypes.Structure):          # 16바이트(32비트) / 24바이트(64비트)
    _fields_ = [("vt", ctypes.c_ushort), ("r1", ctypes.c_ushort), ("r2", ctypes.c_ushort), ("r3", ctypes.c_ushort),
                ("v", ctypes.c_ubyte * (2 * ctypes.sizeof(ctypes.c_void_p)))]


class _ITEMDEF(ctypes.Structure):
    _fields_ = [("path", ctypes.c_wchar_p), ("id", ctypes.c_wchar_p), ("active", ctypes.c_long), ("hClient", ctypes.c_ulong),
                ("blobsz", ctypes.c_ulong), ("blob", ctypes.c_void_p), ("vt", ctypes.c_ushort), ("res", ctypes.c_ushort)]


class _ITEMRESULT(ctypes.Structure):
    _fields_ = [("hServer", ctypes.c_ulong), ("vt", ctypes.c_ushort), ("res", ctypes.c_ushort), ("rights", ctypes.c_ulong),
                ("blobsz", ctypes.c_ulong), ("blob", ctypes.c_void_p)]


class _ITEMSTATE(ctypes.Structure):
    _fields_ = [("hClient", ctypes.c_ulong), ("ts", _FILETIME), ("q", ctypes.c_ushort), ("res", ctypes.c_ushort), ("val", _VARIANT)]


class _STATUS(ctypes.Structure):
    _fields_ = [("ft1", _FILETIME), ("ft2", _FILETIME), ("ft3", _FILETIME), ("state", ctypes.c_ulong), ("groups", ctypes.c_ulong),
                ("bw", ctypes.c_ulong), ("maj", ctypes.c_ushort), ("min", ctypes.c_ushort), ("build", ctypes.c_ushort),
                ("res", ctypes.c_ushort), ("vendor", ctypes.c_void_p)]


_IID_IUnknown = "00000000-0000-0000-C000-000000000046"
_IID_IOPCServer = "39c13a4d-011e-11d0-9675-0020afd8adb3"
_IID_IOPCItemMgt = "39c13a54-011e-11d0-9675-0020afd8adb3"
_IID_IOPCSyncIO = "39c13a52-011e-11d0-9675-0020afd8adb3"
_VT_FMT = {2: "<h", 3: "<i", 18: "<H", 19: "<I", 11: "<h", 16: "<b", 17: "<B", 4: "<f", 5: "<d"}


class _WaitingForData(Exception):
    pass


class OpcDirectLink:
    """MX OPC Server 연결 (OPC DA 2.0 커스텀 인터페이스 직접 호출, 래퍼 · pywin32 불필요, 64/32비트). 태그 이름 = 디바이스 이름."""

    def __init__(self, server="Mitsubishi.MXOPC.6", device="QSIM", source=OPC_DS_DEVICE):
        if sys.platform != "win32":
            raise LinkError("OPC 직접 연결은 Windows 에서만 됩니다")
        self.device = device
        self.source = source
        self.label = f"OPC {server} / 장치 {device} (직접 연결, {struct.calcsize('P') * 8}비트)"
        self._lock = threading.Lock()
        self._items = {}           # dev → (서버 핸들, 정식 VARTYPE)
        self._ole32 = ctypes.windll.ole32
        self._ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
        self._ole32.CoTaskMemFree.restype = None
        self._ole32.CoInitializeEx(None, 0)           # COINIT_MULTITHREADED: 다른 스레드(HMI 중계)에서도 같은 객체 사용
        clsid = _GUID("00000000-0000-0000-0000-000000000000")
        hr = self._ole32.CLSIDFromProgID(ctypes.c_wchar_p(server), ctypes.byref(clsid))
        if hr != 0:
            raise LinkError(f"OPC 서버 {server} 가 등록되어 있지 않음 (0x{hr & 0xFFFFFFFF:08X})")
        unk = ctypes.c_void_p()
        hr = self._ole32.CoCreateInstance(ctypes.byref(clsid), None, 4 | 16, ctypes.byref(_GUID(_IID_IUnknown)), ctypes.byref(unk))
        if hr != 0:
            raise LinkError(f"OPC 서버 {server} 생성 실패 0x{hr & 0xFFFFFFFF:08X}"
                            + (" (E_FAIL: MX OPC 실행 설정의 프로젝트 파일이 없거나 열 수 없음 → Configurator 확인)"
                               if hr & 0xFFFFFFFF == 0x80004005 else ""))
        self._srv = self._qi(unk, _IID_IOPCServer)
        self._release(unk)
        st = ctypes.POINTER(_STATUS)()
        self._check(self._call(self._srv, 6, ctypes.POINTER(ctypes.POINTER(_STATUS)))(self._srv, ctypes.byref(st)), "GetStatus")
        state = st.contents.state
        self._ole32.CoTaskMemFree(st.contents.vendor)
        self._ole32.CoTaskMemFree(st)
        if state != 1:
            print(f"[OPC] 경고: ServerState={state} (1=RUNNING 아님)")
        h_group, rate, self._mgt = ctypes.c_ulong(), ctypes.c_ulong(), ctypes.c_void_p()
        add_group = self._call(self._srv, 3, ctypes.c_wchar_p, ctypes.c_long, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_void_p,
                               ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_ulong),
                               ctypes.POINTER(_GUID), ctypes.POINTER(ctypes.c_void_p))
        self._check(add_group(self._srv, "projectB", 1, 100, 1, None, None, 0x409, ctypes.byref(h_group), ctypes.byref(rate),
                              ctypes.byref(_GUID(_IID_IOPCItemMgt)), ctypes.byref(self._mgt)), "AddGroup")
        self._h_group = h_group.value
        self._sio = self._qi(self._mgt, _IID_IOPCSyncIO)
        self._handle = 1

    # --- COM 도우미
    @staticmethod
    def _call(obj, index, *argtypes):
        vtbl = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]
        return ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, *argtypes)(vtbl[index])

    @staticmethod
    def _check(hr, what):
        if hr not in (0, 1):
            raise LinkError(f"OPC {what} 실패 0x{hr & 0xFFFFFFFF:08X}")

    def _qi(self, obj, iid):
        out = ctypes.c_void_p()
        self._check(self._call(obj, 0, ctypes.POINTER(_GUID), ctypes.POINTER(ctypes.c_void_p))(obj, ctypes.byref(_GUID(iid)), ctypes.byref(out)),
                    "QueryInterface")
        return out

    def _release(self, obj):
        if obj:
            ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0][2])(obj)

    def _item(self, dev):
        item = self._items.get(dev)
        if item is None:
            item_id = f"{self.device}.{dev}"
            d = (_ITEMDEF * 1)(_ITEMDEF(None, item_id, 1, self._handle, 0, None, 0, 0))
            res, err = ctypes.POINTER(_ITEMRESULT)(), ctypes.POINTER(ctypes.c_long)()
            hr = self._call(self._mgt, 3, ctypes.c_ulong, ctypes.POINTER(_ITEMDEF), ctypes.POINTER(ctypes.POINTER(_ITEMRESULT)),
                            ctypes.POINTER(ctypes.POINTER(ctypes.c_long)))(self._mgt, 1, d, ctypes.byref(res), ctypes.byref(err))
            code = (err[0] if err else hr) & 0xFFFFFFFF
            if hr not in (0, 1) or code:
                raise LinkError(f"OPC 태그 {item_id} 등록 실패 0x{code:08X}"
                                + (" (없는 태그 → MX OPC Configurator에 tools/mxopc_tags.py 목록 등록 필요)" if code == 0xC0040007 else ""))
            item = (res[0].hServer, res[0].vt)
            self._ole32.CoTaskMemFree(res)
            self._ole32.CoTaskMemFree(err)
            self._handle += 1
            self._items[dev] = item
        return item

    @staticmethod
    def _value(var):
        fmt = _VT_FMT.get(var.vt)
        if fmt is None:
            raise LinkError(f"OPC 값 형식 VT={var.vt} 미지원")
        v = struct.unpack_from(fmt, bytes(var.v))[0]
        return int(v != 0) if var.vt == 11 else int(v)

    def read(self, dev):
        for _ in range(40):                       # 캐시 읽기: 등록 직후 초기 데이터 대기(품질 32)면 최대 약 4초 재시도
            try:
                return self._read_once(dev)
            except _WaitingForData:
                time.sleep(0.1)
        raise LinkError(f"OPC {self.device}.{dev} 초기 데이터 대기 시간 초과 (품질 32)")

    def _read_once(self, dev):
        with self._lock:
            h, _ = self._item(dev)
            hs = (ctypes.c_ulong * 1)(h)
            st, err = ctypes.POINTER(_ITEMSTATE)(), ctypes.POINTER(ctypes.c_long)()
            hr = self._call(self._sio, 3, ctypes.c_ulong, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong),
                            ctypes.POINTER(ctypes.POINTER(_ITEMSTATE)), ctypes.POINTER(ctypes.POINTER(ctypes.c_long)))(
                self._sio, self.source, 1, hs, ctypes.byref(st), ctypes.byref(err))
            if hr not in (0, 1) or not st:
                raise LinkError(f"OPC {self.device}.{dev} 읽기 실패 0x{hr & 0xFFFFFFFF:08X}")
            code, quality = err[0] & 0xFFFFFFFF, st[0].q
            try:
                if quality == QUALITY_WAITING and not code:
                    raise _WaitingForData()
                if code or quality != QUALITY_GOOD:
                    raise LinkError(f"OPC {self.device}.{dev} 품질 {quality} (192 = Good 아님) 결과 0x{code:08X}")
                return self._value(st[0].val)
            finally:
                ctypes.windll.oleaut32.VariantClear(ctypes.byref(st[0].val))
                self._ole32.CoTaskMemFree(st)
                self._ole32.CoTaskMemFree(err)

    def write(self, dev, value):
        with self._lock:
            h, vt = self._item(dev)
            var = _VARIANT()
            var.vt = vt if vt in _VT_FMT else 2
            fmt = _VT_FMT[var.vt]
            if var.vt == 11:
                v = -1 if value else 0
            elif fmt in ("<f", "<d"):
                v = float(value)
            elif fmt in ("<H", "<I", "<B"):
                v = int(value) & {"<H": 0xFFFF, "<I": 0xFFFFFFFF, "<B": 0xFF}[fmt]
            else:
                v = int(value)
            struct.pack_into(fmt, var.v, 0, v)
            hs, vs, err = (ctypes.c_ulong * 1)(h), (_VARIANT * 1)(var), ctypes.POINTER(ctypes.c_long)()
            hr = self._call(self._sio, 4, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(_VARIANT),
                            ctypes.POINTER(ctypes.POINTER(ctypes.c_long)))(self._sio, 1, hs, vs, ctypes.byref(err))
            code = (err[0] & 0xFFFFFFFF) if err else (hr & 0xFFFFFFFF)
            if err:
                self._ole32.CoTaskMemFree(err)
            if hr not in (0, 1) or code:
                raise LinkError(f"OPC {self.device}.{dev} 쓰기 실패 0x{code:08X}")

    def read_words(self, start, count=1):
        return [self.read(d) for d in word_range(start, count)]

    def write_words(self, start, values):
        """11-27 검토: 여러 워드를 SyncIO.Write 한 번으로(전에는 워드마다 약 0.6 s → 결과 4워드에 약 2.4 s)"""
        devs = list(word_range(start, len(values)))
        if len(devs) == 1:
            return self.write(devs[0], values[0])
        with self._lock:
            n = len(devs)
            hs, vs = (ctypes.c_ulong * n)(), (_VARIANT * n)()
            for i, (dev, value) in enumerate(zip(devs, values)):
                h, vt = self._item(dev)
                hs[i] = h
                vs[i].vt = vt if vt in _VT_FMT else 2
                fmt = _VT_FMT[vs[i].vt]
                if vs[i].vt == 11:
                    v = -1 if value else 0
                elif fmt in ("<f", "<d"):
                    v = float(value)
                elif fmt in ("<H", "<I", "<B"):
                    v = int(value) & {"<H": 0xFFFF, "<I": 0xFFFFFFFF, "<B": 0xFF}[fmt]
                else:
                    v = int(value)
                struct.pack_into(fmt, vs[i].v, 0, v)
            err = ctypes.POINTER(ctypes.c_long)()
            hr = self._call(self._sio, 4, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(_VARIANT),
                            ctypes.POINTER(ctypes.POINTER(ctypes.c_long)))(self._sio, n, hs, vs, ctypes.byref(err))
            codes = [(err[i] & 0xFFFFFFFF) for i in range(n)] if err else [hr & 0xFFFFFFFF] * n
            if err:
                self._ole32.CoTaskMemFree(err)
            bad = [f"{devs[i]}(0x{codes[i]:08X})" for i in range(n) if codes[i]]
            if hr not in (0, 1) or bad:
                raise LinkError(f"OPC {self.device} 쓰기 실패 {bad or hex(hr & 0xFFFFFFFF)}")

    def write_bit(self, dev, state):
        self.write(dev, bool(state))

    def close(self):
        try:
            self._release(self._sio)
            self._call(self._srv, 7, ctypes.c_ulong, ctypes.c_long)(self._srv, self._h_group, 1)   # RemoveGroup(force)
            self._release(self._mgt)
            self._release(self._srv)
        except Exception:
            pass


def OpcLink(server="Mitsubishi.MXOPC.6", device="QSIM", wrapper="auto", source=OPC_DS_DEVICE):
    """MX OPC 연결을 엽니다. wrapper: auto(직접 → 32비트면 래퍼로 재시도) · direct · 래퍼 ProgID(OPC.SiemensDAAuto 등)."""
    if wrapper in ("auto", "direct"):
        try:
            return OpcDirectLink(server, device, source)
        except LinkError as e:
            if wrapper == "direct" or struct.calcsize("P") * 8 != 32:
                raise LinkError(f"OPC 연결 실패: {e}")   # 11-27 검토: sys.exit면 serve 재접속 루프가 못 잡고 끝남
            print(f"[OPC] 직접 연결 실패 ({e}) → Automation 래퍼 OPC.SiemensDAAuto 로 재시도")
            wrapper = "OPC.SiemensDAAuto"
    return OpcAutomationLink(server, device, wrapper, source)


class McLink:
    """MC 프로토콜 3E 바이너리 직접 연결 (pymcprotocol, Q 시리즈 형식). D21: MX OPC 를 쓸 수 없을 때의 선택지."""

    def __init__(self, host, port=5000, plctype="Q"):
        try:
            import pymcprotocol
        except ImportError:
            sys.exit("pymcprotocol 이 필요합니다: python -m pip install pymcprotocol")
        self.label = f"MC 3E {host}:{port} ({plctype})"
        self._lock = threading.Lock()
        self._c = pymcprotocol.Type3E(plctype=plctype)
        self._c.setaccessopt(commtype="binary")
        try:
            self._c.connect(host, port)
        except Exception as e:
            raise LinkError(f"MC 접속 실패 {host}:{port} ({e})") from None

    def _do(self, fn, *a, **kw):
        with self._lock:
            try:
                return fn(*a, **kw)
            except Exception as e:
                raise LinkError(f"MC 통신 오류: {e}") from None

    def read(self, dev):
        kind, _ = split_device(dev)
        if kind in _BIT_DEVICES:
            return self._do(self._c.batchread_bitunits, dev, 1)[0]
        return self._do(self._c.batchread_wordunits, dev, 1)[0]

    def write(self, dev, value):
        kind, _ = split_device(dev)
        if kind in _BIT_DEVICES:
            self._do(self._c.batchwrite_bitunits, dev, [1 if value else 0])
        else:
            self._do(self._c.batchwrite_wordunits, dev, [int(value)])

    def read_words(self, start, count=1):
        return list(self._do(self._c.batchread_wordunits, start, count))

    def write_words(self, start, values):
        self._do(self._c.batchwrite_wordunits, start, [int(v) for v in values])

    def write_bit(self, dev, state):
        self._do(self._c.batchwrite_bitunits, dev, [1 if state else 0])

    def close(self):
        try:
            self._c.close()
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


def add_link_args(p, default_port=None):
    """serve / HMI 모니터 공통 통신 옵션."""
    g = p.add_argument_group("PLC 통신 (기본 OPC: MX OPC Server)")
    g.add_argument("--link", choices=("opc", "modbus", "mc"), default="opc",
                   help="opc: MX OPC Server 경유(기본) / modbus: Modbus TCP 직접 / mc: MC 프로토콜 3E 직접(D21)")
    g.add_argument("--opc-server", default="Mitsubishi.MXOPC.6")
    g.add_argument("--opc-device", default="QSIM", help="MX OPC Configurator 장치 이름 (기본 QSIM = GX Simulator2)")
    g.add_argument("--opc-wrapper", default="auto",
                   help="auto(기본: 직접 연결, 실패 시 32비트면 래퍼) / direct / OPC.SiemensDAAuto 등 래퍼 ProgID")
    g.add_argument("--opc-source", choices=("device", "cache"), default="device",
                   help="읽기 데이터 소스 (기본 device. Simulate 장치 시험은 cache)")
    g.add_argument("--host", default="192.168.0.214",
                   help="--link modbus/mc 일 때 접속 주소. 기본 = 시연 PC(이 PC SmST14, 11-27 A21). 같은 PC 안이면 127.0.0.1")
    g.add_argument("--port", type=int, default=default_port, help="기본 modbus 502 / mc 5000")
    g.add_argument("--unit", type=int, default=1)


def open_link(args):
    if args.link == "opc":
        source = OPC_DS_CACHE if getattr(args, "opc_source", "device") == "cache" else OPC_DS_DEVICE
        return OpcLink(args.opc_server, args.opc_device, args.opc_wrapper, source)
    if args.link == "mc":
        try:
            return McLink(args.host, args.port or 5000)
        except LinkError as e:
            sys.exit(str(e))
    return ModbusLink(args.host, args.port or 502, args.unit)
