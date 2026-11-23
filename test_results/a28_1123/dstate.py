import sys
sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
import fio_scene as F
from pyModbusTCP.client import ModbusClient
txt=F.load(sys.argv[1]); table=F.modbus_address_table(txt)
c=ModbusClient("127.0.0.1",502)
for t in F.tags(txt):
    if t["key"] in table and table[t["key"]][0]=="di" and (t["name"].startswith("X") or "loaded" in t["name"]):
        v=c.read_discrete_inputs(table[t["key"]][1],1)[0]
        print(f"{t['name']}={int(v)}", end="  ")
print()
