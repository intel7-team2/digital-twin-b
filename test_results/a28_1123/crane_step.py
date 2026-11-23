"""크레인 한 동작씩. 매 호출 = 동작 1개 → 끝난 뒤 센서 상태 출력.
사용: crane_step.py <씬> <동작> [값]
  run              Run 코일 ON, 모든 출력 OFF
  goto N           목표 칸 N (이동 시작 → 정지 확인)
  feed             로딩 컨베이어 ON → At Load 가려지는 즉시 OFF (밀어내지 않음)
  fork left|right|middle
  lift on|off      (1.5 s 대기)
  unload S         언로딩 컨베이어 S초 ON
  state            센서만 출력
반사형 센서: 평소 ON, 가리면 OFF → 출력은 '가림' 기준(True = 물체 있음)."""
import sys, time
sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
import fio_scene as F
from pyModbusTCP.client import ModbusClient
scene, act = sys.argv[1], sys.argv[2]
arg = sys.argv[3] if len(sys.argv) > 3 else None
txt = F.load(scene); table = F.modbus_address_table(txt)
addr = {t["name"]: table[t["key"]][1] for t in F.tags(txt) if t["key"] in table}
run_addr = F.modbus_points(txt)["count"]["BitOutput"] - 1
c = ModbusClient("127.0.0.1", 502)
def di():
    v = c.read_discrete_inputs(0, 32)
    if v is None: sys.exit("Modbus 읽기 실패: " + c.last_error_as_txt)
    return v
def co(n, x): c.write_single_coil(addr[n], x)
def state():
    v = di()
    blk = {n: (not v[addr[n]]) for n in ("At Entry", "At Load", "At Unload", "At Exit")}
    lim = [n for n in ("At Left", "At Middle", "At Right") if v[addr[n]]]
    mov = [n for n in ("Moving X", "Moving Z") if v[addr[n]]]
    return f"가림 {[k for k, x in blk.items() if x] or '없음'} · 포크 {lim or '?'} · 이동 {mov or '없음'}"
t0 = time.time()
if act == "run":
    for n in ("Forks Left", "Forks Right", "Lift", "Load Conveyor", "Unload Conveyor"): co(n, 0)
    c.write_single_coil(run_addr, 1); time.sleep(1)
elif act == "goto":
    c.write_single_register(addr["Target Position"], int(arg))
    started = False
    while time.time() - t0 < 3:
        v = di()
        if v[addr["Moving X"]] or v[addr["Moving Z"]]: started = True; break
        time.sleep(0.02)
    while time.time() - t0 < 45:
        v = di()
        if not v[addr["Moving X"]] and not v[addr["Moving Z"]]: break
        time.sleep(0.05)
    time.sleep(0.5)
    print(f"이동 시작 {'감지' if started else '못 봄'} · {time.time()-t0:.1f} s")
elif act == "feed":
    co("Load Conveyor", 1)
    while time.time() - t0 < 40:
        if not di()[addr["At Load"]]: break
        time.sleep(0.01)
    co("Load Conveyor", 0)
    print(f"At Load 감지 즉시 정지 · {time.time()-t0:.2f} s")
elif act == "feedt":                                   # 센서로 끊지 않고 N초 계속 돌림(팔레트가 끝단에 완전히 올라가게)
    co("Load Conveyor", 1); time.sleep(float(arg or 8)); co("Load Conveyor", 0)
    print(f"로딩 컨베이어 {arg or 8} s 동작")
elif act == "trace":                                   # 로딩 컨베이어 N초 동작하며 센서 변화 시각 기록
    co("Load Conveyor", 1); prev = None
    while time.time() - t0 < float(arg or 10):
        v = di(); cur = (not v[addr["At Entry"]], not v[addr["At Load"]])
        if cur != prev: print(f"  {time.time()-t0:5.2f}s At Entry={'가림' if cur[0] else '-'} At Load={'가림' if cur[1] else '-'}", flush=True); prev = cur
        time.sleep(0.01)
    co("Load Conveyor", 0)
elif act == "fork":
    co("Forks Left", arg == "left"); co("Forks Right", arg == "right")
    lim = {"left": "At Left", "right": "At Right", "middle": "At Middle"}[arg]
    while time.time() - t0 < 10:
        if di()[addr[lim]]: break
        time.sleep(0.05)
    print(f"포크 {arg} · {time.time()-t0:.1f} s")
elif act == "lift":
    co("Lift", arg == "on"); time.sleep(1.5)
elif act == "unload":
    co("Unload Conveyor", 1); time.sleep(float(arg or 5)); co("Unload Conveyor", 0)
print(state())
