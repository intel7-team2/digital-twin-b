"""A28 시험: Chain Transfer 좌/우/직진. 팔레트를 한 번에 1개만 내보냄.
판정 = 목표 출구 센서만 가려짐(반사형 센서: 평소 ON, 가리면 OFF)."""
import sys, time
sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
import fio_scene as F
from pyModbusTCP.client import ModbusClient
scene = sys.argv[1]
NOLOAD = "noLoaded" in scene   # Loaded 센서를 라인 밖으로 옮긴 씬: 도착은 시간으로
txt = F.load(scene); table = F.modbus_address_table(txt)
addr = {t["name"]: table[t["key"]][1] for t in F.tags(txt) if t["key"] in table}
run_addr = F.modbus_points(txt)["count"]["BitOutput"] - 1
c = ModbusClient("127.0.0.1", 502)
SEN = {"Loaded": "Loaded", "left": "At left exit", "right": "At right exit", "straight": "At straight exit"}
def di():
    r = c.read_discrete_inputs(0, 32)
    if r is None: sys.exit("Modbus 읽기 실패: " + c.last_error_as_txt)
    return {k: (r[addr[n]] if n in addr else None) for k, n in SEN.items()}
def co(name, v): c.write_single_coil(addr[name], v)
def stop_all():
    for n in ("Load", "Unload", "Transf. left", "Transf. right"): co(n, 0)
def run_one(mode, timeout=25):
    stop_all(); co("Emitter", 1); time.sleep(0.3); co("Emitter", 0)   # 1개만
    co("Load", 1); st = time.time()
    if not NOLOAD and di()["Loaded"]: stop_all(); return f"{mode}: 건너뜀 · 앞 팔레트가 아직 Chain Transfer 위에 있음"
    if NOLOAD: time.sleep(10)        # 센서 없음: 도착 8.6 s(앞 시험) + 여유
    while not NOLOAD and not di()["Loaded"]:
        if time.time() - st > 40: stop_all(); return f"{mode}: 실패 · 팔레트가 Chain Transfer에 도착 안 함(40 s)"
        time.sleep(0.05)
    t_load = time.time() - st
    time.sleep(0.5)
    if mode == "left": co("Load", 0); co("Transf. left", 1)
    elif mode == "right": co("Load", 0); co("Transf. right", 1)
    elif mode == "straightU": co("Load", 0); co("Unload", 1)
    else: pass                                  # straightL: Load만 계속
    st = time.time(); hit = set()
    while time.time() - st < timeout:
        d = di()
        hit |= {k for k in ("left", "right", "straight") if not d[k]}
        if mode.rstrip("UL") in hit: break
        time.sleep(0.05)
    t_exit = time.time() - st
    time.sleep(4); stop_all()
    ok = hit == {mode.rstrip("UL")}
    return f"{mode}: {'통과' if ok else '실패'} · 도착 {t_load:.1f} s · 출구 감지 {t_exit:.1f} s · 가려진 출구 {sorted(hit) or '없음'}"
c.write_single_coil(run_addr, 1); time.sleep(1)
print("시작 센서", di(), flush=True)
for m in sys.argv[2:]:
    print(run_one(m), flush=True)
