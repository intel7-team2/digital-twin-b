"""Pop-up Wheel '멈춤 → 확인 → 보냄' 방식.
1) 바퀴 회전(+)만 켜서 팩을 Sorter로 들임 → 'At scale exit'(Sorter 바로 앞, 확산형: 감지 시 ON)를 지나면 0.6 s 뒤 바퀴 정지
2) 1 s 동안 어느 출구도 안 가려지면 '정지 확인'
3) 방향 명령(좌/우 = 회전 + 방향, 직진 = 회전) → 목표 출구만 가려지면 통과"""
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
CMD = {"left": ["Send forward", "Send left"], "right": ["Send forward", "Send right"], "forward": ["Send forward"]}
ALL = ["Send forward", "Send left", "Send right"]
def raw():
    r = c.read_discrete_inputs(0, 32)
    if r is None: sys.exit("Modbus 읽기 실패: " + c.last_error_as_txt)
    return r
def exits(r): return {k for k, n in EXIT.items() if not r[addr[n]]}
def co(name, v): c.write_single_coil(addr[name], v)
def run_one(mode, settle=float(__import__("os").environ.get("SETTLE", "0"))):
    for k in ALL: co(k, 0)
    co("Load scale", 1); co("Front conveyor", 0)
    co("Emitter", 1); time.sleep(0.3); co("Emitter", 0)
    st = time.time(); seen = False
    while True:                                   # Sorter 앞 센서를 지날 때까지
        r = raw()
        if r[addr["At scale exit"]]: seen = True
        if seen and not r[addr["At scale exit"]]: break
        if time.time() - st > 30: return f"{mode}: 실패 · Sorter 앞 센서 감지 안 됨"
        # 들여보낼 때 바퀴는 돌리지 않음(관성으로 지나침) → 저울 컨베이어만으로 밀어 넣음
        time.sleep(0.02)
    time.sleep(settle); co("Send forward", 0); co("Load scale", 0)   # 바퀴 · 뒤 컨베이어 모두 정지
    print("  정지", flush=True); time.sleep(float(__import__("os").environ.get("HOLD", "0")))
    t0 = time.time(); early = set()
    while time.time() - t0 < 4.0:          # 직진 출구까지 2.5 s → 4 s 동안 안 나가야 정지
        early |= exits(raw()); time.sleep(0.05)
    if early: return f"{mode}: 실패 · 정지 못 하고 {sorted(early)} 출구로 나감"
    if mode != "forward":                         # 방향 먼저 꺾고(정지 상태) → 1 s 뒤 회전
        co("Send " + mode, 1); time.sleep(1.0)
        moved = exits(raw())
        if moved: return f"{mode}: 실패 · 방향만 바꿨는데 {sorted(moved)} 출구로 나감"
    if mode == "forward": co("Front conveyor", 1)
    co("Send forward", 1)
    st = time.time(); hit = set(); t_hit = None
    while time.time() - st < 15:
        e = exits(raw())
        if e and t_hit is None: t_hit = time.time() - st
        hit |= e
        if mode in hit and not e: break
        time.sleep(0.05)
    for k in ALL: co(k, 0)
    ok = hit == {mode}
    return f"{mode}: {'통과' if ok else '실패'} · 정지 4 s 확인 · 명령 후 출구 {t_hit:.1f} s · 가려진 출구 {sorted(hit) or '없음'}" if t_hit else f"{mode}: 실패 · 명령 후 15 s 동안 출구 감지 없음"
c.write_single_coil(run_addr, 1); time.sleep(1)
for m in sys.argv[2:]:
    print(run_one(m), flush=True)
