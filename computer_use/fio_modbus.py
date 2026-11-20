"""
Factory I/O Modbus TCP Server 조작 도구 — 씬 파일에서 "태그 이름 → Modbus 번지"를 읽어 값을 읽고 씁니다.

F2~F4 시험에서 크레인 목표 칸 · RFID 명령 · 센서 값을 화면 클릭 대신 Python으로 다룹니다.
Factory I/O 쪽 준비: 드라이버 = Modbus TCP/IP Server, Connect(초록). 이 PC 어댑터는 Software Loopback → --host 127.0.0.1.
번지는 씬 파일의 ModbusTCPServer 블록에서 읽으므로, 씬을 고친 뒤(fio_scene.py map-modbus) 같은 파일을 주면 됩니다.

  tags  --scene S                               태그 → 번지 목록
  get   --scene S NAME [NAME ...]               값 읽기
  set   --scene S NAME=VALUE [...]              액추에이터 쓰기 (on/off/숫자)
  watch --scene S [NAME ...] [--sec 30]         값이 바뀔 때마다 출력
  crane --scene S --target N [--fork left|right|middle] [--lift on|off] [--prefix P]
  rfid  --scene S --reader P --cmd 0~4 [--index I] [--data V]     RFID 명령 1회
  rfid-check --scene S --reader P               F4 연속 시험: 0 → 1 → 3(22200) → 2 → 3(40000) → 2

예) python computer_use/fio_modbus.py tags --scene factoryio_test/F2a_asrs_pallet_SL.factoryio
    python computer_use/fio_modbus.py crane --scene factoryio_test/F2a_asrs_pallet_SL.factoryio --target 1
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fio_scene  # noqa: E402

RFID_ROLES = {           # 역할 → (이름에 들어갈 글자, 빠져야 할 글자)
    "command": (["command"], ["execute", " id", "(id"]),
    "execute": (["execute"], []),
    "index": (["index"], []),
    "write": (["write"], []),
    "cmd_id": (["command id"], []),
    "status": (["status"], []),
    "read": (["read data"], []),
}


class Link:
    def __init__(self, host, port, unit=1, timeout=2.0):
        try:
            from pyModbusTCP.client import ModbusClient
        except ImportError:
            sys.exit("pyModbusTCP 가 필요합니다 (이 PC의 Python 3.12에는 있음).")
        self.c = ModbusClient(host=host, port=port, unit_id=unit, timeout=timeout, auto_open=True)
        self.where = f"{host}:{port}"

    def _chk(self, v, what):
        if v is None:
            sys.exit(f"Modbus {what} 실패 ({self.where}): {self.c.last_error_as_txt} "
                     f"— Factory I/O 드라이버가 Modbus TCP/IP Server · 연결됨인지, 씬이 실행(Play) 중인지 확인")
        return v

    def read(self, area, addr):
        if area == "di":
            return self._chk(self.c.read_discrete_inputs(addr, 1), "di 읽기")[0]
        if area == "coil":
            return self._chk(self.c.read_coils(addr, 1), "coil 읽기")[0]
        if area == "ir":
            return self._chk(self.c.read_input_registers(addr, 1), "ir 읽기")[0]
        return self._chk(self.c.read_holding_registers(addr, 1), "hr 읽기")[0]

    def write(self, area, addr, value):
        if area == "coil":
            return self._chk(self.c.write_single_coil(addr, bool(value)), "coil 쓰기")
        if area == "hr":
            return self._chk(self.c.write_single_register(addr, int(value) & 0xFFFF), "hr 쓰기")
        sys.exit(f"{area}:{addr} 는 센서(읽기 전용) 번지입니다.")


class Scene:
    def __init__(self, path):
        text = fio_scene.load(path)
        self.table = fio_scene.modbus_address_table(text)
        self.tags = [t for t in fio_scene.tags(text) if t["key"] in self.table]
        self.unmapped = [t["name"] for t in fio_scene.tags(text) if t["key"] not in self.table and t["forced"] is None]
        if fio_scene.current_driver(text) != fio_scene.DRIVER["modbus-server"]:
            print("[주의] 이 씬의 선택 드라이버가 Modbus TCP Server(32)가 아닙니다. Factory I/O에서 드라이버를 확인하세요.")

    def find(self, name, prefix=""):
        cand = [t for t in self.tags if t["name"] == name] or \
               [t for t in self.tags if t["name"].lower() == name.lower()] or \
               [t for t in self.tags if t["name"].lower().startswith(prefix.lower()) and name.lower() in t["name"].lower()]
        if not cand:
            sys.exit(f"태그를 찾지 못함: '{name}' (Modbus 연결된 태그만 찾습니다. 'tags'로 목록 확인)")
        if len(cand) > 1:
            exact = [t for t in cand if t["name"].lower() == (prefix + name).lower()]
            if len(exact) == 1:
                cand = exact
            else:
                sys.exit(f"'{name}' 후보가 여럿입니다: {[t['name'] for t in cand]} — 정확한 이름이나 --prefix 를 주세요.")
        t = cand[0]
        area, addr, _ = self.table[t["key"]]
        return t, area, addr

    def role(self, prefix, role):
        need, avoid = RFID_ROLES[role]
        c = [t for t in self.tags if t["name"].lower().startswith(prefix.lower())
             and all(n in t["name"].lower() for n in need) and not any(a in t["name"].lower() for a in avoid)]
        if len(c) != 1:
            sys.exit(f"RFID '{prefix}' 의 {role} 태그를 하나로 못 찾음: {[t['name'] for t in c]}")
        area, addr, _ = self.table[c[0]["key"]]
        return c[0], area, addr


def fmt(t, v):
    if t["kind"] == "Bool":
        return "ON" if v else "off"
    s = v - 0x10000 if v >= 0x8000 else v
    return f"{v}" + (f" (부호 {s})" if s != v else "")


def parse_val(v):
    lv = str(v).strip().lower()
    if lv in ("on", "true"):
        return 1
    if lv in ("off", "false"):
        return 0
    return int(lv, 16) if lv.startswith("0x") else int(lv)


def wait_until(fn, timeout, step=0.05):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if fn():
            return time.time() - t0
        time.sleep(step)
    return None


def rfid_once(link, sc, prefix, cmd, index=0, data=0, timeout=3.0):
    tc, ac, nc = sc.role(prefix, "command")
    te, ae, ne = sc.role(prefix, "execute")
    ti, ai, ni = sc.role(prefix, "index")
    tw, aw, nw = sc.role(prefix, "write")
    tid, aid, nid = sc.role(prefix, "cmd_id")
    ts, as_, ns = sc.role(prefix, "status")
    tr, ar, nr = sc.role(prefix, "read")
    link.write(ae, ne, 0)
    link.write(ac, nc, cmd)
    link.write(ai, ni, index)
    link.write(aw, nw, data)
    before = link.read(aid, nid)
    time.sleep(0.1)
    link.write(ae, ne, 1)
    took = wait_until(lambda: link.read(aid, nid) != before, timeout)
    link.write(ae, ne, 0)
    st, rd = link.read(as_, ns), link.read(ar, nr)
    names = {0: "정상", 1: "태그 없음", 2: "태그 여러 개", 3: "주소 오류", 4: "명령 오류"}
    res = dict(cmd=cmd, index=index, data=data, status=st, status_txt=names.get(st, "?"), read=rd,
               cmd_id=(before, link.read(aid, nid)), ms=None if took is None else round(took * 1000))
    print(f"  RFID {prefix!r} cmd={cmd} idx={index} data={data} → Status {st}({res['status_txt']}) "
          f"Read Data {fmt(tr, rd)} · Command ID {before}→{res['cmd_id'][1]} · "
          f"{'응답 없음(시간 초과)' if took is None else str(res['ms']) + ' ms'}")
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=502)
    sp = ap.add_subparsers(dest="action", required=True)
    for name in ("tags", "get", "set", "watch", "crane", "rfid", "rfid-check"):
        p = sp.add_parser(name)
        p.add_argument("--scene", required=True)
        if name in ("get", "set", "watch"):
            p.add_argument("names", nargs="*")
        if name == "watch":
            p.add_argument("--sec", type=float, default=30)
        if name == "crane":
            p.add_argument("--target", type=int)
            p.add_argument("--fork", choices=["left", "right", "middle"])
            p.add_argument("--lift", choices=["on", "off"])
            p.add_argument("--prefix", default="")
            p.add_argument("--timeout", type=float, default=60)
        if name in ("rfid", "rfid-check"):
            p.add_argument("--reader", required=True, help="RFID 태그 이름 앞부분 (예: 'RFID Reader 0')")
        if name == "rfid":
            p.add_argument("--cmd", type=int, required=True)
            p.add_argument("--index", type=int, default=0)
            p.add_argument("--data", type=int, default=0)
    a = ap.parse_args()
    sc = Scene(a.scene)

    if a.action == "tags":
        for t in sorted(sc.tags, key=lambda t: (sc.table[t["key"]][0], sc.table[t["key"]][1])):
            area, addr, kind = sc.table[t["key"]]
            print(f"  {area:4s} {addr:4d}  {t['io']:6s} {t['kind']:5s} {t['name']}  [{t['prefab']}]")
        if sc.unmapped:
            print(f"  (연결 안 된 태그 {len(sc.unmapped)}개: {', '.join(sc.unmapped[:12])}{' …' if len(sc.unmapped) > 12 else ''}"
                  f" → fio_scene.py map-modbus)")
        return

    link = Link(a.host, a.port)
    if a.action == "get":
        for n in a.names:
            t, area, addr = sc.find(n)
            print(f"  {t['name']} [{area}:{addr}] = {fmt(t, link.read(area, addr))}")
    elif a.action == "set":
        for p in a.names:
            n, v = p.split("=", 1)
            t, area, addr = sc.find(n)
            link.write(area, addr, parse_val(v))
            print(f"  {t['name']} [{area}:{addr}] ← {v}")
    elif a.action == "watch":
        sel = [sc.find(n) for n in a.names] if a.names else [(t,) + sc.table[t["key"]][:2] for t in sc.tags]
        last = {}
        t0 = time.time()
        while time.time() - t0 < a.sec:
            for t, area, addr in sel:
                v = link.read(area, addr)
                if last.get(t["key"]) != v:
                    print(f"  {time.time() - t0:6.2f}s  {t['name']} = {fmt(t, v)}")
                    last[t["key"]] = v
            time.sleep(0.1)
    elif a.action == "crane":
        tx, ax, nx = sc.find("Moving X", a.prefix)
        tz, az, nz = sc.find("Moving Z", a.prefix)
        if a.target is not None:
            tt, at, nt = sc.find("Target Position", a.prefix)
            link.write(at, nt, a.target)
            started = wait_until(lambda: link.read(ax, nx) or link.read(az, nz), 2.0)
            done = wait_until(lambda: not link.read(ax, nx) and not link.read(az, nz), a.timeout)
            print(f"  목표 {a.target}: 출발 {'감지' if started is not None else '못 봄(이미 그 칸?)'} · "
                  f"{'도착 %.1f s' % done if done is not None else '시간 초과'}")
        if a.fork:
            fl = sc.find("Forks Left", a.prefix)
            fr = sc.find("Forks Right", a.prefix)
            link.write(fl[1], fl[2], a.fork == "left")
            link.write(fr[1], fr[2], a.fork == "right")
            lim = {"left": "At Left", "right": "At Right", "middle": "At Middle"}[a.fork]
            tl, al, nl = sc.find(lim, a.prefix)
            d = wait_until(lambda: link.read(al, nl), 10)
            print(f"  포크 {a.fork}: {'%.1f s' % d if d is not None else '시간 초과'}")
        if a.lift:
            tl, al, nl = sc.find("Lift", a.prefix)
            link.write(al, nl, a.lift == "on")
            time.sleep(1.0)
            print(f"  리프트 {a.lift}")
    elif a.action == "rfid":
        rfid_once(link, sc, a.reader, a.cmd, a.index, a.data)
    elif a.action == "rfid-check":
        print("[F4] 같은 박스를 리더 앞에 세운 상태에서 실행합니다.")
        r0 = rfid_once(link, sc, a.reader, 0)
        r1 = rfid_once(link, sc, a.reader, 1)
        rfid_once(link, sc, a.reader, 3, 1, 22200)
        r2 = rfid_once(link, sc, a.reader, 2, 1)
        rfid_once(link, sc, a.reader, 3, 2, 40000)
        r3 = rfid_once(link, sc, a.reader, 2, 2)
        print(f"  결과: 태그 있음={r0['status'] == 0} · 시리얼 {r1['read']} · 22200 → {r2['read']} · "
              f"40000 → {r3['read']} ({'16비트로 읽힘' if r3['read'] == 40000 else '값이 바뀜'})")


if __name__ == "__main__":
    main()
