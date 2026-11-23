"""GX Simulator2(분할 래더)에서 STEP 01 · RFID ① 순서를 OPC로 시험. Python이 RFID 리더 역할.
사용: sim_infeed_test.py [normal|dup]   — 시험 뒤 쓴 값은 0으로 되돌림"""
import sys, time
sys.path.insert(0, r"D:\seojung\digital-twin-b")
from plc_link import OpcLink, OPC_DS_DEVICE
mode = sys.argv[1] if len(sys.argv) > 1 else "normal"
L = OpcLink("Mitsubishi.MXOPC.6", "CSIM", "auto", OPC_DS_DEVICE)
r, w = L.read, L.write
T0 = time.time()
def log(m): print(f"{time.time()-T0:5.1f}s {m}", flush=True)
touched = ["X1500", "X1501", "X1502", "X1510", "X1511", "M1510", "D1513", "D1514", "D1515", "D1516", "D1518"]
tag = {0: 55} if mode == "dup" else {}
cmds = []
try:
    # 초기화: 정지 → 값 0
    w("X1502", 1); time.sleep(0.3); w("X1502", 0)
    for d in ("X1510", "X1511", "D1513", "D1514", "D1515"): w(d, 0)
    w("X1500", 1)                      # 비상정지 NC = 정상
    w("D1516", 101); w("D1518", 4); w("M1510", 1)
    w("X1501", 1); time.sleep(0.3); w("X1501", 0); log("시작 버튼(X1501) → 운전 중")
    st = time.time(); seen_emit = False
    while time.time() - st < 5:
        if r("Y1500"): seen_emit = True; break
        time.sleep(0.05)
    log(f"투입 펄스 Y1500 = {'○' if seen_emit else '×'} · 스토퍼 Y1502 = {r('Y1502')}")
    time.sleep(0.5); w("X1510", 1); log("팩 도착 X1510 ON (높이 센서 X1511 OFF = Small)")
    prev, cid, idle = 0, 0, time.time()
    while time.time() - idle < 4:
        exe = r("M1511")
        if exe and not prev:
            cmd, idx, data = r("D1510"), r("D1511"), r("D1512")
            if cmd == 3: tag[idx] = data
            out = tag.get(idx, 0) if cmd == 2 else (777 if cmd == 1 else 0)
            w("D1515", out); w("D1514", 0); cid += 1; w("D1513", cid)
            cmds.append((cmd, idx, data if cmd == 3 else None, out if cmd == 2 else None))
            log(f"RFID① 명령 {cmd} · idx {idx}" + (f" · 쓰기 {data}" if cmd == 3 else "") + (f" · 읽기 → {out}" if cmd == 2 else ""))
            idle = time.time()
        prev = exe
        if r("M1510") == 0: log("M1510 인계 수신 비트 내려감(STEP 01 완료)"); break
        time.sleep(0.02)
    time.sleep(0.5)
    log(f"끝 상태: M1510 = {r('M1510')} · 스토퍼 Y1502 = {r('Y1502')} · 명령 {len(cmds)}개")
    if mode == "normal":
        want = [(0, 0), (1, 0), (2, 0), (3, 0), (3, 1), (3, 2), (3, 4), (3, 5), (3, 9), (2, 0)]
        got = [(c, i) for c, i, *_ in cmds]
        ok = got == want and r("M1510") == 0 and tag.get(0) == 101 and tag.get(9) == 4
        print("결과:", "통과" if ok else f"실패 got={got} tag={tag}")
    else:
        ok = [(c, i) for c, i, *_ in cmds] == [(0, 0), (1, 0), (2, 0)] and r("M1510") == 1 and r("Y1502") == 1
        print("결과:", "통과(중복 투입 → 등록 중단 · 스토퍼 유지)" if ok else f"실패 cmds={cmds}")
finally:
    w("X1502", 1); time.sleep(0.3); w("X1502", 0)    # 정지
    for d in touched:
        try: w(d, 0)
        except Exception: pass
    L.close()
