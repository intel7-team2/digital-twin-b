"""RFID ① 정지 위치에서 어느 태그를 읽는지: D1508(0 = 받침만?, 1 Small, 4 Large)로 투입 → 명령 1(시리얼) · 명령 2 idx0 를 몇 번.
사용: tag_probe.py <씬> <D1508 값...>"""
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
    for ar, a, _ in T[n]: c.write_single_register(a, v & 0xFFFF)
def ir(n): return c.read_input_registers(T[n][0][1], 1)[0]
def di(n): return c.read_discrete_inputs(T[n][0][1], 1)[0]
def cmd(base, k, idx=0, data=None):
    co(f"M{base+1}", 0); hr(f"D{base+1}", idx); hr(f"D{base}", k)
    if data is not None: hr(f"D{base+2}", data)
    cid = ir(f"D{base+3}"); time.sleep(0.2); co(f"M{base+1}", 1); st = time.time()
    while time.time() - st < 2 and ir(f"D{base+3}") == cid: time.sleep(0.02)
    co(f"M{base+1}", 0); time.sleep(0.2)
    return ir(f"D{base+4}"), ir(f"D{base+5}")
c.write_single_coil(table[re.search(r'RunOutputKey="([0-9a-f-]{36})"', txt).group(1)][1], 1); time.sleep(1)
co("Y1501", 1); co("Y1502", 1); hr("D1509", 2)
for v in [int(x) for x in sys.argv[2:]]:
    co("Y1502", 1); co("Y1501", 1); hr("D1508", v); time.sleep(0.3); co("Y1500", 1); time.sleep(0.5); co("Y1500", 0)
    st = time.time()
    while time.time() - st < 12 and di("X1510"): time.sleep(0.05)
    time.sleep(1.2); co("Y1501", 0); time.sleep(0.5)
    r = [cmd(1510, 1) for _ in range(3)]
    w = cmd(1510, 3, 0, 4321); rd = cmd(1510, 2, 0)
    print(f"D1508={v}: X1510={'가림' if not di('X1510') else '빔(박스 없음?)'} · 시리얼(상태,값)×3 {r} · 쓰기 4321 상태 {w[0]} → 읽기 {rd}", flush=True)
    co("Y1502", 0); co("Y1501", 1); time.sleep(5)
