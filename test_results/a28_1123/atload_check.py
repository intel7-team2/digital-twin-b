"""At Load 센서 확인: 빈 상태에서 빔 열림(1)인지 → 팔레트 이송하며 가려지는 시각 → 가려지면 즉시 로딩 정지 · 제동.
사용: atload_check.py <씬> [V]"""
import sys, time
sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
import fio_scene as F
from pyModbusTCP.client import ModbusClient
scene = sys.argv[1]; V = float(sys.argv[2]) if len(sys.argv) > 2 else 4
txt = F.load(scene); table = F.modbus_address_table(txt)
addr = {t["name"]: table[t["key"]][1] for t in F.tags(txt) if t["key"] in table}
run_addr = F.modbus_points(txt)["count"]["BitOutput"] - 1
c = ModbusClient("127.0.0.1", 502)
def speed(v): c.write_single_register(addr["Load speed"], int(round(v * 100)) & 0xFFFF)
def raw(n): return c.read_discrete_inputs(addr[n], 1)[0]
c.write_single_coil(run_addr, 1); time.sleep(1.5)
c.write_single_register(addr["Target Position"], 55)
print(f"빈 상태 At Load = {int(raw('At Load'))} (1 = 빔 열림)", flush=True)
c.write_single_coil(addr["Entry Conveyor"], 1); speed(V); t0 = time.time()
while time.time() - t0 < 25:
    if not raw("At Load"): break
    time.sleep(0.005)
else:
    speed(0); c.write_single_coil(addr["Entry Conveyor"], 0); sys.exit("결과: 25 s 동안 감지 없음")
t_hit = time.time() - t0
c.write_single_coil(addr["Entry Conveyor"], 0); speed(-2); time.sleep(0.15); speed(0)
time.sleep(1.5)
print(f"결과: {t_hit:.2f} s에 감지 → 정지 · 정지 후 At Load = {'가림' if not raw('At Load') else '열림'}", flush=True)
