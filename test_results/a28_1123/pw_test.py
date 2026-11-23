"""Pop-up Wheel 좌/우/직진. 앞 팔레트가 출구를 지나 Remover로 사라진 뒤 다음 1개 투입.
판정 = 목표 출구 센서(반사형: 평소 ON, 가리면 OFF)만 가려짐."""
import sys, time
sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
import fio_scene as F
from pyModbusTCP.client import ModbusClient
scene = sys.argv[1]
txt = F.load(scene); table = F.modbus_address_table(txt)
addr = {t["name"]: table[t["key"]][1] for t in F.tags(txt) if t["key"] in table}
run_addr = F.modbus_points(txt)["count"]["BitOutput"] - 1
c = ModbusClient("127.0.0.1", 502)
EXIT = {"left": "At exit left", "right": "At exit right", "forward": "At exit front"}
# 설명서: (+)="Send forward" 바퀴 올림+회전, (Left)/(Right) 방향만 → 좌·우는 회전과 같이 켬
CMD = {"left": ["Send forward", "Send left"], "right": ["Send forward", "Send right"], "forward": ["Send forward"]}
ALL = ["Send forward", "Send left", "Send right"]
def di():
    r = c.read_discrete_inputs(0, 32)
    if r is None: sys.exit("Modbus 읽기 실패: " + c.last_error_as_txt)
    return {k: r[addr[n]] for k, n in EXIT.items()}
def co(name, v): c.write_single_coil(addr[name], v)
def run_one(mode, timeout=40):
    for k in ALL: co(k, 0)
    for k in CMD[mode]: co(k, 1)              # 방향을 먼저 정해 둠
    co("Emitter", 1); time.sleep(0.3); co("Emitter", 0)
    st = time.time(); hit = set(); t_hit = None
    while time.time() - st < timeout:
        d = di()
        new = {k for k, v in d.items() if not v}
        if new and t_hit is None: t_hit = time.time() - st
        hit |= new
        if mode in hit and all(d.values()):   # 목표 출구를 지나 다 비워짐
            break
        time.sleep(0.05)
    for k in ALL: co(k, 0)
    ok = hit == {mode}
    tt = f"{t_hit:.1f} s" if t_hit is not None else "없음"
    return f"{mode}: {'통과' if ok else '실패'} · 출구 감지 {tt} · 가려진 출구 {sorted(hit) or '없음'}"
c.write_single_coil(run_addr, 1); time.sleep(1)
print("시작 센서", di(), flush=True)
for m in sys.argv[2:]:
    print(run_one(m), flush=True)
