"""
PLC 쪽 흉내로 serve 핸드셰이크 3개 확인 — GX Works2에 값을 손으로 넣지 않고 OPC(또는 MC)로 요청을 보냅니다.

먼저 다른 창에서 serve 를 같은 링크 · 같은 DB로 띄워 둡니다.
  python measurement_engine.py handoff --count 20 --db test_results/monday.db
  python measurement_engine.py serve --opc-device CSIM --db test_results/monday.db
그다음
  python computer_use/plc_side_check.py --opc-device CSIM --db test_results/monday.db [--pack 3]

메인(D1710 → D1700~D1703 · D1713) · 재검사(D1740 → D1730~D1733 · D1743) · 발열 격리(D1650 → D1653)를 차례로 보내고,
판정이 measure · judge 기대값과 같은지, 응답 시간, DB 행을 확인합니다. 끝나면 건드린 번지를 원래 값으로 되돌립니다.
링크 옵션은 serve 와 같음(--link opc|mc|modbus, --opc-device, --host, --port).
"""
import argparse
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import measurement_engine as me  # noqa: E402
import plc_link  # noqa: E402

TOUCH = [(1700, 4), (1710, 5), (1730, 4), (1740, 5), (1650, 4)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    plc_link.add_link_args(ap)
    ap.add_argument("--db", default=me.DEFAULT_DB)
    ap.add_argument("--pack", type=int, default=3, help="메인 검사 PACK ID (재검사는 +1, 격리는 +2). handoff 로 DB에 있어야 함")
    ap.add_argument("--timeout", type=float, default=5.0)
    a = ap.parse_args()
    conn = me.open_db(a.db)
    link = plc_link.open_link(a)
    saved = {s: link.read_words(f"D{s}", n) for s, n in TOUCH}
    res = []

    def wait(dev, val):
        end = time.time() + a.timeout
        while time.time() < end:
            if link.read_words(f"D{dev}", 1)[0] == val:
                return True
            time.sleep(0.05)
        return False

    def station(req, result, pack, rc, name):
        info = me.pack_info(conn, pack)
        if not info:
            sys.exit(f"PACK {pack} 이 DB에 없습니다 → measurement_engine.py handoff --db {a.db}")
        cells = info[0]
        link.write_words(f"D{req + 1}", [pack, rc, 0, cells])
        t0 = time.time()
        link.write_words(f"D{req}", [1])
        ok = wait(req + 3, 1)
        ms = (time.time() - t0) * 1000
        out = link.read_words(f"D{result}", 4)
        link.write_words(f"D{req}", [0])
        ok2 = wait(req + 3, 0)
        exp = me.judge(me.measure(pack, rc, "id", cells), rc, cells)
        good = ok and ok2 and out[0] == exp
        res.append(good)
        print(f"[{'OK' if good else 'NG'}] {name} D{req}: PACK {pack} 셀 {cells} → 결과 D{result}~ {out} "
              f"(기대 판정 {exp}) · 응답 {ms:.0f} ms" + ("" if ok else " · 완료 신호 없음(serve가 떠 있는지)"))

    try:
        for k, (pack, rc) in ((1, (a.pack, 0)), (2, (a.pack + 1, 1))):
            st = me.STATIONS[k]
            station(st["req"], st["result"], pack, rc, st["name"])
        n0 = conn.execute("SELECT COUNT(*) FROM measurements WHERE station=0").fetchone()[0]
        link.write_words("D1651", [a.pack + 2, 412, 0])
        t0 = time.time()
        link.write_words("D1650", [1])
        ok = wait(1653, 1)
        ms = (time.time() - t0) * 1000
        link.write_words("D1650", [0])
        ok2 = wait(1653, 0)
        n1 = conn.execute("SELECT COUNT(*) FROM measurements WHERE station=0").fetchone()[0]
        good = ok and ok2 and n1 > n0
        res.append(good)
        print(f"[{'OK' if good else 'NG'}] 발열 격리 D1650: PACK {a.pack + 2} 41.2 °C → DB 격리 기록(measurements station 0) {n0}→{n1}행 · 응답 {ms:.0f} ms")
    finally:
        for s, vals in saved.items():
            link.write_words(f"D{s}", vals)
        print("[복원] " + " · ".join(f"D{s}~D{s + len(v) - 1}" for s, v in saved.items()))
        link.close()
    print(f"\n핸드셰이크 {sum(res)}/{len(res)} 통과")
    sys.exit(0 if all(res) and len(res) == 3 else 1)


if __name__ == "__main__":
    main()
