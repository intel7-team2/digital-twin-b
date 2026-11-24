"""Factory I/O 쪽 실제 출력(코일) · 센서(입력 비트)를 Modbus로 읽어 바뀔 때만 기록(11-24, 소프트 PLC ↔ 중계 비교용).
사용: py -3.12 mb_watch.py <출력 csv> <초> [코일 시작 끝] [입력 시작 끝]"""
import sys, time, csv
sys.path.insert(0, r"D:\seojung\digital-twin-b\test_results\a28_1123")   # pyModbusTCP가 이 폴더에 있음
from pyModbusTCP.client import ModbusClient
out, lim = sys.argv[1], float(sys.argv[2])
c0, c1 = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (13, 27)
d0, d1 = (int(sys.argv[5]), int(sys.argv[6])) if len(sys.argv) > 6 else (15, 20)
M = ModbusClient("127.0.0.1", 502); t0 = time.time(); prev = None
f = open(out, "w", newline="", encoding="utf-8"); w = csv.writer(f)
w.writerow(["t"] + [f"c{i}" for i in range(c0, c1 + 1)] + [f"d{i}" for i in range(d0, d1 + 1)])
while time.time() - t0 < lim:
    c = M.read_coils(c0, c1 - c0 + 1); d = M.read_discrete_inputs(d0, d1 - d0 + 1)
    if c and d:
        r = [int(x) for x in c] + [int(x) for x in d]
        if r != prev: w.writerow([f"{time.time()-t0:.2f}"] + r); f.flush(); prev = r
    time.sleep(0.02)
