"""실제 PLC 시험 전 초기화(11-24): 운전 비트를 끄고 MX OPC에 등록된 M · D 번지를 모두 0으로 씀.
GX Simulator2 창을 조작하지 않고 이전 회차의 스텝 · 알람 · 래치 값을 지움(타이머 · 출력은 다음 스캔에서 다시 계산).
사용: py -3.12 opc_reset.py [mdb 경로]"""
import sys, time
sys.argv = [sys.argv[0], "1", "1"] + sys.argv[1:]
src = open(__file__.replace("opc_reset.py", "opc_outside.py"), encoding="utf-8").read()
exec(src.split("L = Link(")[0])
mdb = sys.argv[3] if len(sys.argv) > 3 else r"D:\seojung\digital-twin-b\test_results\MXOPC_B_v6_d24d.mdb"
L = Link(device="CSIM", source=P.OPC_DS_CACHE)
sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
import mxopc_db as M
out = M.run_vbs('Set rs = cn.Execute("SELECT Name FROM MX_DataTagsRoot WHERE ParentID=1 AND RegisterName IN (\'M\',\'D\')")\r\n'
                'Do While Not rs.EOF\r\n  WScript.Echo rs("Name")\r\n  rs.MoveNext\r\nLoop\r\n', mdb)
names = [n for n in out.split() if n[0] in "MD" and n[1:].isdigit()]
L.write("M1950", 0); time.sleep(0.5)
bad = []
for i in range(0, len(names), 40):
    bad += L.write_many([(n, 0) for n in names[i:i + 40]])
time.sleep(1)
print(f"초기화: M · D {len(names)}개를 0으로 · 실패 {bad} · 확인 {L.read_many(['M1950', 'D1541', 'M1510', 'D1750', 'D1760'])}")
