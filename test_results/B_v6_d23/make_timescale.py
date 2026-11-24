"""시뮬레이터 느린 재생용 래더 사본 — 타이머 설정값 · 타이머 현재값 비교 상수를 N배(11-24).
MX OPC ↔ GX Simulator2 지연(쓰기 약 0.6 s, 왕복 0.8~1.3 s 측정)은 실제 시간이라 Factory I/O를 1/N배로 느리게 돌리면
기계 동작 대비 지연이 1/N로 줄어듦. 이때 PLC 타이머도 N배로 늘려야 기계 동작과 시간이 맞음(RFID 응답 대기 · 높이 판정 창 등).
설계서 · 원본 명령어 목록은 그대로, 이 사본만 GX Simulator2에 씀. Factory I/O 콘솔: scene.time_scale = 1/N, 툴바 Time Scale을 그 값으로.
사용: python make_timescale.py <N=3>"""
import re, sys, io, os, subprocess
N = int(sys.argv[1]) if len(sys.argv) > 1 else 3
ROOT = r"D:\seojung\digital-twin-b"
src = os.path.join(ROOT, "plc", "ladder_mnemonic_v6.txt")
out = os.path.join(ROOT, "plc", f"ladder_mnemonic_v6_x{N}.txt")
t = io.open(src, encoding="utf-8").read()
n = [0]
def k(m):
    n[0] += 1
    return f"{m.group(1)}T{m.group(2)} K{int(m.group(3)) * N}"
t2 = re.sub(r"((?:OUTH?|AND[<>=]+|LD[<>=]+|OR[<>=]+) )T(\d+) K(\d+)", k, t)
io.open(out, "w", encoding="utf-8", newline="").write(t2)
print(f"타이머 상수 {n[0]}곳 × {N} → {out}")
d = os.path.join(ROOT, "test_results", "B_v6_d23", f"x{N}")
os.makedirs(d, exist_ok=True)
subprocess.run([sys.executable, os.path.join(ROOT, "plc", "mnemonic_to_gxw_csv.py"), out, os.path.join(d, "B_v6.csv")], check=True)
