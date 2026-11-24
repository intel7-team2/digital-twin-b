"""판독 실패로 멈춘 팔레트에 본 리더 · 후보 리더를 한 개씩 차례로 명령 1(시리얼)을 내 결과를 봄(11-24).
동시에 명령하면 리더가 멈추므로(같은 날 확인) 반드시 하나씩. 사용: python rfid_seq.py <씬> <② 또는 ③>"""
import sys, time
sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
sys.path.insert(0, r"D:\seojung\digital-twin-b\test_results\a28_1123")   # pyModbusTCP 대체 모듈
import fio_scene as F
from pyModbusTCP.client import ModbusClient
scene, st = sys.argv[1], sys.argv[2]
txt = F.load(scene); tb = F.modbus_address_table(txt)
T = {tg["name"]: tb[tg["key"]][1] for tg in F.tags(txt) if tg["key"] in tb}
c = ModbusClient("127.0.0.1", 502)
def one(b, cmd=1):
    ex = T[f"M{b+1}"]; c.write_single_coil(ex, 0); c.write_single_register(T[f"D{b+1}"], 0); c.write_single_register(T[f"D{b}"], cmd)
    cid = c.read_input_registers(T[f"D{b+3}"], 1)[0]; time.sleep(0.2); c.write_single_coil(ex, 1); t0 = time.time()
    while time.time() - t0 < 2.5:
        if c.read_input_registers(T[f"D{b+3}"], 1)[0] != cid: break
        time.sleep(0.03)
    else:
        c.write_single_coil(ex, 0); return "응답 없음"
    c.write_single_coil(ex, 0); time.sleep(0.1)
    return f"상태 {c.read_input_registers(T[f'D{b+4}'], 1)[0]} · 값 {c.read_input_registers(T[f'D{b+5}'], 1)[0]}"
NAME = ["B 1칸 가깝게", "D 범위 1.2m", "E 라인 +1", "F 라인 −1", "G 높이 Y3", "H 높이 Y5", "I 반대쪽(−Z)"]
main, base = (1520, 2000) if st == "②" else (1530, 2100)
time.sleep(1.0)
print(f"{st} 본 리더 D{main}: {one(main)}", flush=True)
for i, nm in enumerate(NAME):
    b = base + i * 10
    if f"M{b+1}" in T: print(f"{st} {nm} D{b}: {one(b)}", flush=True); time.sleep(0.3)
print(f"{st} 본 리더 다시 D{main}: {one(main)}", flush=True)
