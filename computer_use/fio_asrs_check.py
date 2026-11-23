"""v6 씬 AS/RS 시험: Emitter → 입고점 → 크레인 A가 랙에 넣기 → 크레인 B가 꺼내 출고점 → 1차 분리.

python computer_use/fio_asrs_check.py --scene factoryio_test/ProjectB_v6_mb.factoryio --cells 1,2,19 --part 4
- Factory I/O에서 씬을 열고 Modbus TCP Server 연결 · Play 한 뒤 실행 (pymodbus 3.x).
- 단계마다 걸린 시간과 센서 값을 출력. 팔레트가 떨어졌는지는 출고점 도착(X1610)과 화면으로 판단.
- 포크 방향: 기본 씬과 같이 크레인 A는 입고점 = 왼쪽 · 랙 = 오른쪽, 크레인 B는 랙 = 오른쪽 · 출고점 = 왼쪽.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fio_scene as fs  # noqa: E402
from pymodbus.client import ModbusTcpClient  # noqa: E402


class IO:
    def __init__(self, scene, host):
        t = fs.load(scene)
        tab = fs.modbus_address_table(t)
        self.addr: dict[str, list] = {}
        for tg in fs.tags(t):
            if tg["key"] in tab:
                self.addr.setdefault(tg["name"], []).append(tab[tg["key"]])
        self.c = ModbusTcpClient(host, port=502)
        if not self.c.connect():
            sys.exit(f"Modbus {host}:502 연결 안 됨 (Factory I/O 드라이버 CONNECT · Play 확인)")
        self.t0 = time.time()

    def get(self, name):
        area, i, _ = self.addr[name][0]
        if area == "di":
            return int(self.c.read_discrete_inputs(i, count=1).bits[0])
        if area == "ir":
            return self.c.read_input_registers(i, count=1).registers[0]
        if area == "coil":
            return int(self.c.read_coils(i, count=1).bits[0])
        return self.c.read_holding_registers(i, count=1).registers[0]

    def set(self, name, v):
        for area, i, _ in self.addr[name]:
            if area == "coil":
                self.c.write_coil(i, bool(v))
            else:
                self.c.write_register(i, int(v))

    def log(self, msg):
        print(f"[{time.time() - self.t0:7.1f}s] {msg}", flush=True)

    def wait(self, cond, what, timeout=60.0, settle=0.0):
        t = time.time()
        while time.time() - t < timeout:
            if cond():
                if settle:
                    time.sleep(settle)
                self.log(f"OK  {what} ({time.time() - t:.1f}s)")
                return True
            time.sleep(0.1)
        self.log(f"NG  {what} — {timeout:.0f}s 안에 안 됨")
        return False


def crane_move(io, p, target):
    io.set(f"D160{p}", target)
    time.sleep(0.6)
    mx, mz = ("X1600", "X1601") if p == "1" else ("X1608", "X1609")
    return io.wait(lambda: not io.get(mx) and not io.get(mz), f"크레인 {'A' if p == '1' else 'B'} → {target}", 90, 0.5)


def fork(io, p, side, lift_after):
    """side: left/right. 포크 내밀기 → 들기/내리기 → 가운데로."""
    b = {"1": ("Y1600", "Y1601", "Y1602", "X1602", "X1603", "X1604", "X1601"),
         "2": ("Y1608", "Y1609", "Y160A", "X160A", "X160B", "X160C", "X1609")}[p]
    yl, yr, ylift, xl, xm, xr, mz = b
    io.set(yl if side == "left" else yr, 1)
    ok = io.wait(lambda: io.get(xl if side == "left" else xr), f"  포크 {side} 끝", 20, 0.3)
    io.set(ylift, lift_after)
    time.sleep(0.6)
    ok &= io.wait(lambda: not io.get(mz), f"  {'들기' if lift_after else '내리기'}", 20, 0.3)
    io.set(yl, 0), io.set(yr, 0)
    ok &= io.wait(lambda: io.get(xm), "  포크 가운데", 20, 0.3)
    return ok


def pulse_until(io, on, off_after):
    io.set(on, 1); time.sleep(off_after); io.set(on, 0)


def rfid_read(io, ex, cmd, cid, st, rd, name):
    b = io.get(cid); io.set(cmd, 1); io.set(ex, 1); time.sleep(0.4); io.set(ex, 0); time.sleep(0.4)
    s = io.get(st)
    io.log(f"{'OK' if s == 0 else 'NG'}  {name} 시리얼 읽기 Status={s} 시리얼={io.get(rd)} (명령 {io.get(cid) - b}회)")
    return s == 0


def retest(io, good):
    """CT1 직진 → 메인 검사(RFID ②) → CT2에서 재검사 라인(M1720) → 곡선 롤러 → 재검사(RFID ③) → CT5
    → good: 왼쪽(M1731) → 합류 CT4 → GOOD OUT / ng: 오른쪽(M1732) → NG OUT. CT 위 가운데 맞춤은 시간으로."""
    ct2f, ct5f = "M1720 CT (+) (번지 없음, A31)", "Sorter2 CT (+) (미사용)"
    m_f, m_l = "Merge CT (+) (번지 없음, A31)", "Merge CT left (번지 없음, A31)"
    io.set("M1660", 1); io.set("Y1701", 1); io.set("Y1700", 1); io.set("Y1702", 1); io.set(ct2f, 1)
    ok = io.wait(lambda: io.get("X1700"), "메인 검사 정위치 X1700", 30)
    time.sleep(2.5)
    held = io.get("X1700"); io.log(f"{'OK' if held else 'NG'}  메인 검사 Roller Stop 정지 유지")
    rfid_read(io, "M1521", "D1520", "D1523", "D1524", "D1525", "RFID ②")
    io.set("Y1701", 0)
    ok &= io.wait(lambda: io.get("X1720"), "M1720 분기 앞 X1720", 30)
    time.sleep(CT_T); io.set(ct2f, 0); time.sleep(0.4)
    io.set("M1720", 1); io.set("Y1800", 1); io.set("Y1801", 1); io.set("Y1730", 1)
    ok &= io.wait(lambda: io.get("X1800"), "재검사 라인 입구 X1800", 20)
    io.set("M1720", 0)
    ok &= io.wait(lambda: io.get("X1730"), "재검사 정위치 X1730 (곡선 롤러 지남)", 40)
    time.sleep(2.5)
    held = io.get("X1730"); io.log(f"{'OK' if held else 'NG'}  재검사 Roller Stop 정지 유지")
    rfid_read(io, "M1531", "D1530", "D1533", "D1534", "D1535", "RFID ③")
    io.set("Y1730", 0); io.set(ct5f, 1)
    ok &= io.wait(lambda: io.get("X1731"), "2차 분리 앞 X1731", 30)
    time.sleep(CT_T); io.set(ct5f, 0); time.sleep(0.4)
    if not good:
        io.set("M1732", 1); io.set("Y1732", 1); io.set("Y1901", 1)
        ok &= io.wait(lambda: io.get("X1901"), "NG OUT 게이트 X1901", 30)
        io.set("M1732", 0)
        return ok
    # 합류: CT4 체인을 미리 올리면 롤러보다 4 cm 높아 팔레트가 부딪힘 → 합류 롤러로 CT4 위에 반쯤 밀어 넣은 뒤 체인을 올림
    io.set("M1731", 1); io.set("Y1731", 1)
    time.sleep(CT_SIDE); io.set("M1731", 0)
    time.sleep(MERGE_WAIT)                    # 합류 롤러로 CT4 가장자리까지
    io.set(m_l, 1); time.sleep(MERGE_T); io.set(m_l, 0); time.sleep(0.4)
    io.set(m_f, 1); io.set("Y1900", 1)
    ok &= io.wait(lambda: io.get("X1900"), "GOOD OUT 게이트 X1900 (합류)", 30)
    return ok


CT_T = 2.6      # CT 앞 센서(3~7u 앞)에서 CT 가운데까지 굴리는 시간 (0.45 m/s)
CT_SIDE = 3.0   # CT 옆 이송 시간
MERGE_WAIT = 4.0   # 합류 롤러로 CT4 가장자리까지 가는 시간
MERGE_T = 2.6      # CT4 체인으로 가운데까지 끌어오는 시간 (2.0은 덜 들어와 틀어짐, 사용자 지적 11-23)


def cell_b(cell_a):
    """크레인 A 칸 번호 → 같은 실제 칸의 크레인 B 칸 번호.
    Factory I/O 칸 번호 = (단 - 1) × 9 + 열, 열 1 = 그 크레인의 입출고점(레일 끝) 쪽 (11-23 화면 확인).
    두 크레인이 랙을 양쪽에서 마주 보므로 B 열 = 7 - A 열 (v6 랙 6열 = 랙 2개)."""
    row, col = divmod(cell_a - 1, 9)
    if col >= 6:
        raise SystemExit(f"칸 {cell_a}: 7~9열은 랙이 없음")
    return row * 9 + (6 - col)


def run(io, cell, part):
    io.log(f"=== 칸 {cell} · Part {part} ===")
    for y in ("Y1501", "Y1504", "Y1505"):
        io.set(y, 1)
    io.set("Y1502", 1)                        # Roller Stop 올림(RFID ① 위치에서 세움)
    io.set("Y1505", 1)
    io.set("D1509", BASE), io.set("D1508", part)
    io.set("Y1500", 1); time.sleep(1.5); io.set("Y1500", 0)     # Emitter 배출 간격 1~2초
    if not io.wait(lambda: io.get("X1510"), "RFID ① 정위치 X1510", 60):
        return False
    time.sleep(3.0)
    if not io.get("X1510"):
        io.log("NG  Roller Stop이 팔레트를 못 세움")
    else:
        io.log("OK  Roller Stop 정지 유지 X1510")
    b = io.get("D1513"); io.set("D1510", 1); io.set("M1511", 1); time.sleep(0.4); io.set("M1511", 0); time.sleep(0.4)
    st = io.get("D1514")
    io.log(f"{'OK' if st == 0 else 'NG'}  RFID ① 시리얼 읽기 Status={st} 시리얼={io.get('D1515')}")
    io.set("Y1502", 0)                        # 내림 → 입고점으로
    if not io.wait(lambda: io.get("X1512"), "입고점 도착 X1512", 60):
        return False
    io.set("Y1505", 0)                        # 래더 V02와 같이 도착 즉시 정지
    time.sleep(1.0)
    ok = crane_move(io, "1", 55) and fork(io, "1", "left", 1)
    ok = ok and crane_move(io, "1", cell) and fork(io, "1", "right", 0)
    ok = ok and crane_move(io, "1", 55)
    if not ok:
        return False
    io.log("크레인 A 입고 완료 → 크레인 B 출고")
    cb = cell_b(cell)
    io.log(f"크레인 B 칸 = {cb}")
    ok = crane_move(io, "2", cb) and fork(io, "2", "right", 1)
    ok = ok and crane_move(io, "2", 55) and fork(io, "2", "left", 0)
    if not ok:
        return False
    ok = io.wait(lambda: io.get("X1610"), "출고점 팔레트 있음 X1610", 10)
    io.set("Y1610", 1), io.set("Y1611", 1), io.set("M1660", 1)
    ok &= io.wait(lambda: io.get("X1660"), "1차 분리 CT1 위 X1660", 30)
    if ROUTE == "iso":
        io.set("M1660", 0)                    # 격리: 감지 즉시 CT1 굴림 정지 (래더처럼)
    crane_move(io, "2", 55)
    if not ok:
        return False
    if ROUTE == "iso":                        # 발열 격리: CT1 가운데에서 세우고 오른쪽으로
        io.set("M1660", 0); time.sleep(0.5)      # 감지 즉시 굴림 정지 (더 굴리면 하류로 밀려 모서리에 걸림, 11-23)
        io.set("M1661", 1); io.set("Y1690", 1)
        ok = io.wait(lambda: io.get("X1902"), "격리 게이트 X1902", 30)
        io.set("M1661", 0)
        return ok
    if ROUTE in ("ng", "rgood"):
        return retest(io, ROUTE == "rgood")
    # GOOD 직진: Pop-up 1 직진 → 메인 검사(래더처럼 X1700에서 Y1700 정지) → M1720 · 합류 Pop-up 직진(강제) → GOOD OUT
    io.set("Y1701", 1)                        # Roller Stop 올림 (메인 검사 위치)
    io.set("Y1700", 1), io.set("Y1702", 1)
    ok = io.wait(lambda: io.get("X1700"), "메인 검사 정위치 X1700", 30)
    time.sleep(3.0)
    held = io.get("X1700")
    io.log(f"{'OK' if held else 'NG'}  메인 검사 Roller Stop 정지 유지 X1700={held}")
    b = io.get("D1523"); io.set("D1520", 1); io.set("M1521", 1); time.sleep(0.4); io.set("M1521", 0); time.sleep(0.4)
    st = io.get("D1524")
    io.log(f"{'OK' if st == 0 else 'NG'}  RFID ② 시리얼 읽기 Status={st} 시리얼={io.get('D1525')} (명령 {io.get('D1523') - b}회)")
    io.set("Y1701", 0); io.set("M1660", 0)
    for n in ("M1720 CT (+) (번지 없음, A31)", "Merge CT (+) (번지 없음, A31)"):   # Chain Transfer 직진 (번지 없음)
        if n in io.addr:
            io.set(n, 1)
    io.set("Y1900", 1)
    ok &= io.wait(lambda: io.get("X1900"), "GOOD OUT 게이트 X1900", 40)
    return ok and held


ROUTE = "good"
BASE = 1


def main():
    global ROUTE, BASE
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="factoryio_test/ProjectB_v6_mb.factoryio")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--cells", default="1")
    ap.add_argument("--part", type=int, default=4, help="1 Small · 4 Large")
    ap.add_argument("--route", default="good", choices=["good", "iso", "ng", "rgood"])
    ap.add_argument("--base", type=int, default=1, help="Emitter Base 값 (1 Pallet, 2 Square pallet 추정)")
    a = ap.parse_args()
    ROUTE = a.route
    BASE = a.base
    io = IO(a.scene, a.host)
    res = []
    for c in [int(x) for x in a.cells.split(",")]:
        res.append((c, run(io, c, a.part)))
    for y in ("Y1501", "Y1504", "Y1505", "Y1610", "Y1611", "M1660"):
        io.set(y, 0)
    print("결과:", ", ".join(f"칸 {c} {'통과' if ok else '실패'}" for c, ok in res))


if __name__ == "__main__":
    main()
