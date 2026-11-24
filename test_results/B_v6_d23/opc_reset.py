"""실제 PLC 시험 전 초기화(11-24): 운전 비트를 끄고 MX OPC에 등록된 M · D 번지를 모두 0으로 씀.
GX Simulator2 창을 조작하지 않고 이전 회차의 스텝 · 알람 · 래치 값을 지움(타이머 · 출력은 다음 스캔에서 다시 계산).
사용: py -3.12 opc_reset.py [mdb 경로]"""
import sys, time, os
sys.argv = [sys.argv[0], "1", "1"] + sys.argv[1:]
src = open(__file__.replace("opc_reset.py", "opc_outside.py"), encoding="utf-8").read()
exec(src.split("L = Link(")[0])
mdb = sys.argv[3] if len(sys.argv) > 3 else r"D:\seojung\digital-twin-b\test_results\MXOPC_B_v6_d24e.mdb"
L = Link(device="CSIM", source=P.OPC_DS_CACHE)
sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
import mxopc_db as M
out = M.run_vbs('Set rs = cn.Execute("SELECT Name FROM MX_DataTagsRoot WHERE ParentID=1 AND RegisterName IN (\'M\',\'D\')")\r\n'
                'Do While Not rs.EOF\r\n  WScript.Echo rs("Name")\r\n  rs.MoveNext\r\nLoop\r\n', mdb)
names = [n for n in out.split() if n[0] in "MD" and n[1:].isdigit()]
# RUN 첫 스캔(SM402)에서 한 번 채우는 상수(크레인 랙 칸 변환표 D1870~ 등)는 지우지 않음(11-24: 지웠더니 크레인 목표 칸이 0이 되어 제자리에서 포크만 움직임)
import re as _re
mn = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "plc", "ladder_mnemonic_v6.txt"), encoding="utf-8").read()
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
time.sleep(1)
print(f"초기화: M · D {len(names)}개를 0으로 · 실패 {bad} · 확인 {L.read_many(['M1950', 'D1541', 'M1510', 'D1750', 'D1760'])}")
