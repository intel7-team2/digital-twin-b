"""실제 PLC 시험 전 초기화(11-24): 운전 비트를 끄고 MX OPC에 등록된 M · D 번지를 모두 0으로 씀.
GX Simulator2 창을 조작하지 않고 이전 회차의 스텝 · 알람 · 래치 값을 지움(타이머 · 출력은 다음 스캔에서 다시 계산).
사용: py -3.12 opc_reset.py [mdb 경로] — 11-27: v7d(가상 래더 태그 200개 추가)를 주면 새 태그까지 0으로 써서 2층이 멈춤 → 초기화 목록은 v7c로 줌(one5.sh · one6.sh)"""
import sys, time, os
sys.argv = [sys.argv[0], "1", "1"] + sys.argv[1:]
src = open(__file__.replace("opc_reset.py", "opc_outside.py"), encoding="utf-8").read()
exec(src.split("L = Link(")[0])
mdb = sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "opc_reset_names.txt")
L = Link(device="CSIM", source=P.OPC_DS_CACHE)
sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
import mxopc_db as M
# 11-27: 인자가 .txt면 그 목록(한 줄에 번지 하나)만 0으로 씀. 기본 = 같은 폴더 opc_reset_names.txt
#   (실제 PLC 회귀로 검증된 MXOPC_B_v7c.mdb의 M · D 번지 + D1540 운전 시간). MX OPC에 태그를 더해도 초기화 범위가 바뀌지 않게
#   (11-27 v8i: v7d 목록으로 초기화하자 새로 등록한 스텝 · 내부 비트까지 0이 되어 2층이 멈춤)
if mdb.lower().endswith(".txt"):
    names = [l.strip() for l in open(mdb, encoding="utf-8") if l.strip() and not l.startswith("#")]
else:
    out = M.run_vbs('Set rs = cn.Execute("SELECT Name FROM MX_DataTagsRoot WHERE ParentID=1 AND RegisterName IN (\'M\',\'D\')")\r\n'
                    'Do While Not rs.EOF\r\n  WScript.Echo rs("Name")\r\n  rs.MoveNext\r\nLoop\r\n', mdb)
    names = [n for n in out.split() if n[0] in "MD" and n[1:].isdigit()]
# RUN 첫 스캔(SM402)에서 한 번 채우는 상수는 지우지 않음(v1 래더는 크레인 칸 변환표 D1870~, v3는 해당 없음 — 11-27 v3 목록으로)(11-24: 지웠더니 크레인 목표 칸이 0이 되어 제자리에서 포크만 움직임)
import re as _re
mn = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "plc", "v3", "ladder_mnemonic_v3.txt"), encoding="utf-8").read()
keep = set()
for line in mn.splitlines():
    if _re.match(r"^\S+\s+LD SM402\s+=>", line):
        keep.update(_re.findall(r"MOV K-?\d+ ([DM]\d+)", line))
names = [n for n in names if n not in keep]
print(f"첫 스캔 상수 {len(keep)}개는 그대로 둠")
L.write("M1950", 0); time.sleep(0.5)
bad = []
for i in range(0, len(names), 40):
    bad += L.write_many([(n, 0) for n in names[i:i + 40]])
# 11-26: 정지 중 초기화 입력 M1961 — v3 래더는 스텝 릴레이 · 구간 기억 비트(MX OPC에 없는 번지 포함)를 첫 스캔처럼 다시 잡음
# (GX Simulator2를 다시 띄우지 않아도 중단한 회차 뒤에 바로 다음 회차를 돌릴 수 있음. v1 · v2 래더에서는 LOCK 해제만 함)
# 11-27: 초기화 입력은 M1964(래더 Z01, LAMP W08이 끔)로 분리, M1961은 랙 LOCK 해제만. 둘 다 비트 셋 → 래더가 끔
for b in ("M1964", "M1961"):
    try:
        L.write(b, 1); time.sleep(1.5)
    except Exception as e:
        print(f"{b} 쓰기 실패(태그 없음? MX OPC v7f 이상 필요):", e)
time.sleep(1)
print(f"초기화: M · D {len(names)}개를 0으로 · 실패 {bad} · 확인 {L.read_many(['M1950', 'D1541', 'M1510', 'D1750', 'D1760'])}")
sys.exit(1 if bad else 0)   # 11-28 재점검: 쓰기 실패가 있으면 run_real.sh가 멈추게
