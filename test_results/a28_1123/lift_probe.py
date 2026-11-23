"""크레인 리프트 동작 시간 재기: 리프트 켬/끔 순간을 출력. 사용: lift_probe.py <씬> A|B up|down"""
import sys, time, re
sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
import fio_scene as F
from pyModbusTCP.client import ModbusClient
txt = F.load(sys.argv[1]); table = F.modbus_address_table(txt)
A = {t["name"]: table[t["key"]] for t in F.tags(txt) if t["key"] in table}
c = ModbusClient("127.0.0.1", 502)
c.write_single_coil(table[re.search(r'RunOutputKey="([0-9a-f-]{36})"', txt).group(1)][1], 1)
n = "Y1602" if sys.argv[2] == "A" else "Y160A"
c.write_single_coil(A[n][1], sys.argv[3] == "up"); print("lift", sys.argv[3], time.time(), flush=True)
