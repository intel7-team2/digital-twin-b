"""Emitter Controller 모드 D1508 값별 박스 확인: 높이 센서 X1510(Y5) · X1511(Y8) 가림으로 판별. 사용: emit_probe.py <씬> <값...>"""
import sys, re, time
sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
import fio_scene as F
from pyModbusTCP.client import ModbusClient
txt = F.load(sys.argv[1]); table = F.modbus_address_table(txt)
T = {}
for t in F.tags(txt):
    if t["key"] in table: T.setdefault(t["name"], []).append(table[t["key"]])
c = ModbusClient("127.0.0.1", 502)
def co(n, v):
    for ar, a, _ in T[n]: c.write_single_coil(a, v)
def hr(n, v):
    for ar, a, _ in T[n]: c.write_single_register(a, v)
def di(n): return c.read_discrete_inputs(T[n][0][1], 1)[0]
c.write_single_coil(table[re.search(r'RunOutputKey="([0-9a-f-]{36})"', txt).group(1)][1], 1); time.sleep(1)
co("Y1501", 1); co("Y1502", 1); co("Y1504", 1); hr("D1509", 2)
for v in [int(x) for x in sys.argv[2:]]:
    co("Y1502", 1); hr("D1508", v); time.sleep(0.3); co("Y1500", 1); time.sleep(0.5); co("Y1500", 0)
    st = time.time()
    while time.time() - st < 15 and di("X1510"): time.sleep(0.05)
    time.sleep(1.5)
    print(f"D1508={v}: X1510(Y5)={'가림' if not di('X1510') else '빔'} · X1511(Y8)={'가림' if not di('X1511') else '빔'} ({time.time()-st:.1f}s)", flush=True)
    co("Y1502", 0); time.sleep(4)
