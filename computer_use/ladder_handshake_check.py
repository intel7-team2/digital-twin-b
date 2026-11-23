"""
래더(GX Simulator2) ↔ serve 핸드셰이크 G · J · N 을 Factory I/O 없이 확인 — Python이 Factory I/O 쪽(센서 · RFID 리더)을 흉내냅니다.

  plc_side_check.py 는 Python이 PLC 역할(요청 쓰기)을 하지만, 이 스크립트는 **래더가 요청을 내고** serve 가 답하는지 봅니다.
  MX OPC(QSIM = GX Simulator2) · 래더 RUN · serve 실행 중일 때:
    python measurement_engine.py serve --opc-device QSIM --db test_results/opc_1123.db
    python computer_use/ladder_handshake_check.py --opc-device QSIM --db test_results/opc_1123.db [--only G,J,N]

  G: X1902 상승 → 래더 D1650 = 1 → serve D1653 = 1 → 래더 D1650 = 0 → serve D1653 = 0
  J: X1700 ON → RFID ②(흉내) 시리얼 · idx0 · idx4 · idx9 읽기 → 래더 D1710 요청 → serve 판정 → 래더가 RFID에 idx5~8 쓰기 → D1710 = 0 → X1722 → 끝
  N: X1730 ON → RFID ③(흉내) 읽기(idx5 = 2 RETEST) → D1740 요청 → serve 판정 → idx5~8 쓰기 → D1740 = 0 → X1730 OFF → 끝
RFID 흉내: 실행 비트(M1521 / M1531)가 켜지면 명령(D15x0: 1 시리얼 · 2 읽기 · 3 쓰기)을 태그 메모리에 적용하고
읽은 값(D15x5)을 쓴 뒤 명령 ID(D15x3)를 +1 (Factory I/O RFID Command ID와 같은 동작). 상태(D15x4)는 0.
끝나면 건드린 번지를 원래 값으로 되돌립니다(래더 내부 단계 · SET 비트는 래더가 스스로 0으로 돌아오는 것만 확인).
"""
import argparse
import os
import sys
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import measurement_engine as me  # noqa: E402
import plc_link  # noqa: E402

RESTORE = ["D1520", "D1521", "D1522", "D1523", "D1524", "D1525", "D1526", "D1527",
           "D1530", "D1531", "D1532", "D1533", "D1534", "D1535", "D1536", "D1537",
           "D1650", "D1651", "D1652", "D1653", "D1700", "D1701", "D1702", "D1703",
           "D1710", "D1711", "D1712", "D1713", "D1714", "D1730", "D1731", "D1732", "D1733",
           "D1740", "D1741", "D1742", "D1743", "D1744", "D1900", "D1901", "D1902", "D1903", "D1904"]
BITS = ["X1700", "X1720", "X1721", "X1722", "X1730", "X1731", "X1902"]


def pulse(L, dev, on=0.6, off=0.4):
    L.write(dev, True)
    time.sleep(on)
    L.write(dev, False)
    time.sleep(off)


class Rfid(threading.Thread):
    """Factory I/O RFID 리더 흉내 (base = 1520 → RFID ②, 1530 → RFID ③). 별도 스레드: 래더 실행기는 2초 안에
    명령 ID가 바뀌지 않으면 실패로 보므로(T1506 K20) 주 루프와 같이 돌리면 늦음(11-23 첫 시험에서 idx7 · 8 쓰기 놓침)."""

    def __init__(self, link, base, execute, serial, mem):
        super().__init__(daemon=True)
        self.l, self.b, self.ex, self.serial, self.mem = link, base, execute, serial, dict(mem)
        self.log, self.stop, self.prev = [], False, False
        self.l.write(f"D{self.b + 4}", 0)                   # 상태 0 (래더는 보지 않음, A31)
        self.cid = self.l.read(f"D{self.b + 3}")

    def run(self):
        while not self.stop:
            on = bool(self.l.read(self.ex))
            if on and not self.prev:
                cmd, addr, data = (self.l.read(f"D{self.b + k}") for k in (0, 1, 2))
                if cmd == 1:
                    val = self.serial
                elif cmd == 3:
                    self.mem[addr] = data
                    val = data
                else:
                    val = self.mem.get(addr, 0) if cmd == 2 else 0
                self.l.write(f"D{self.b + 5}", val)
                self.cid = (self.cid + 1) & 0x7FFF
                self.l.write(f"D{self.b + 3}", self.cid)
                self.log.append((cmd, addr, val))
            self.prev = on


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    plc_link.add_link_args(ap)
    ap.add_argument("--db", default=me.DEFAULT_DB)
    ap.add_argument("--pack", type=int, default=3, help="J(메인) PACK ID, N(재검사)은 +1. handoff 로 DB에 있어야 함")
    ap.add_argument("--only", default="G,J,N")
    ap.add_argument("--timeout", type=float, default=90.0, help="J · N 한 번 최대 시간(OPC 읽기가 한 번에 수백 ms라 30초로는 모자람, 11-23)")
    a = ap.parse_args()
    conn = me.open_db(a.db)
    L = plc_link.open_link(a)
    saved = {d: L.read(d) for d in RESTORE + BITS}
    results = []

    def watch(name, keys, done, tick=None, timeout=None):
        timeout = timeout or a.timeout
        t0, last = time.time(), None
        while time.time() - t0 < timeout:
            if tick:
                tick()
            v = {k: L.read(k) for k in keys}
            if v != last:
                print(f"  {time.time() - t0:6.2f}s " + " ".join(f"{k}={x}" for k, x in v.items()))
                last = v
            r = done(v, time.time() - t0)
            if r:
                return True, time.time() - t0
            time.sleep(0.2)
        return False, time.time() - t0

    try:
        only = a.only.upper().split(",")
        if "G" in only:
            print("[G] 발열 격리 기록 (X1902 상승)")
            seen = {"req": False}
            L.write("X1902", True)
            time.sleep(0.3)
            L.write("X1902", False)

            def g_done(v, t):
                seen["req"] |= v["D1650"] == 1 or v["D1653"] == 1
                return seen["req"] and v["D1650"] == 0 and v["D1653"] == 0 and t > 0.5
            ok, t = watch("G", ["D1650", "D1651", "D1653"], g_done, timeout=10)
            results.append(("G", ok, f"{t:.1f}s"))

        for name in ("J", "N"):
            if name not in only:
                continue
            main_ = name == "J"
            pack = a.pack if main_ else a.pack + 1
            rc = 0 if main_ else 1
            cells = me.pack_info(conn, pack)[0]
            base, ex, sensor = (1520, "M1521", "X1700") if main_ else (1530, "M1531", "X1730")
            req, res = (1710, 1700) if main_ else (1740, 1730)
            mem = {0: pack, 4: rc, 9: cells}
            if not main_:
                mem[5] = 2                       # 메인 판정 RETEST → 재검사기에서 다시 계측
            serial = 6100 + pack + int(time.time()) % 1000
            rf = Rfid(L, base, ex, serial, mem)
            exp = me.judge(me.measure(pack, rc, "id", cells), rc, cells)
            print(f"[{name}] PACK {pack} 셀 {cells} RC {rc} · 태그 시리얼 {serial} · 기대 판정 {exp}")
            rf.start()
            L.write(sensor, True)
            st = {"req": False, "done": False, "out": None, "exit": False}

            def j_done(v, t):
                if not rf.log and t > 15:
                    raise TimeoutError(f"래더가 RFID 명령을 내지 않음 — {name} 단계(D{1750 if main_ else 1760})가 0이 아닐 수 있음(이전 시험 잔여)")
                if v[f"D{req}"] == 1:
                    st["req"] = True
                if v[f"D{req + 3}"] == 1 and not st["done"]:
                    st["done"] = True
                    st["out"] = [L.read(f"D{res + k}") for k in range(4)]
                # 래더가 요청을 내리면(태그 쓰기 끝) 팩을 내보냄: 메인 = 분기 CT 센서 X1722 펄스, 재검사 = X1730 OFF
                if st["req"] and st["done"] and v[f"D{req}"] == 0 and not st["exit"]:
                    st["exit"] = True
                    # 메인: 분기 CT 도착 X1722(K04 → M1750 해제) · 재검사 분기 X1720 → X1721(K01 · K02, 재검사로 갈 때 M1720 · M1754 해제)
                    # 재검사: X1730 OFF 뒤 2차 분리 진입 X1731(P01~P06 → M1760 해제). 실제로는 Factory I/O 센서가 함
                    if main_:
                        pulse(L, "X1722")
                        L.write(sensor, False)
                        pulse(L, "X1720")
                        pulse(L, "X1721")
                    else:
                        L.write(sensor, False)
                        time.sleep(1.0)
                        pulse(L, "X1731", on=1.0, off=1.2)
                return st["exit"] and v[f"D{req + 3}"] == 0 and t > 1.0
            try:
                ok, t = watch(name, [f"D{req}", f"D{req + 3}", f"D{res}", ex], j_done)
            except TimeoutError as e:
                print(f"  {e}")
                ok, t = False, 15.0
            finally:
                time.sleep(1.0)
                rf.stop = True
                rf.join(5)
                L.write(sensor, False)
            # 쓰기 확인: 래더가 RFID 에 판정 · 계측값을 썼는지
            writes = {addr: d for c, addr, d in rf.log if c == 3}
            out = st["out"] or [None] * 4
            wexp = {5: out[0], 6: out[1], 7: out[2], 8: out[3]}
            wok = all(writes.get(k) == v for k, v in wexp.items())
            good = ok and out[0] == exp and wok
            print(f"  RFID 명령 {len(rf.log)}회 {rf.log}")
            print(f"  결과 D{res}~ {out} · 태그 쓰기 idx5~8 {[writes.get(k) for k in (5, 6, 7, 8)]}")
            results.append((name, good, f"{t:.1f}s · 판정 {out[0]}(기대 {exp}) · 태그 쓰기 {'일치' if wok else '불일치'}"))
    finally:
        time.sleep(1.0)
        for d, v in saved.items():
            try:
                L.write(d, v)
            except Exception as e:  # noqa: BLE001
                print(f"[복원 실패] {d}: {e}")
        print(f"[복원] {len(saved)}개 번지")
        L.close()
    print()
    for n, ok, msg in results:
        print(f"[{'OK' if ok else 'NG'}] {n} {msg}")
    print(f"래더 핸드셰이크 {sum(1 for _, ok, _ in results if ok)}/{len(results)} 통과")
    sys.exit(0 if results and all(ok for _, ok, _ in results) else 1)


if __name__ == "__main__":
    main()
