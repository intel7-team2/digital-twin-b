"""크레인 A · B 한 동작씩. 사용: two.py <씬> <명령> [인자]
  run                      Run ON · 출력 OFF · A 55
  a_in N                   A: 투입(아날로그 + 제동) → 집기 → 칸 N 넣기 (5/5 통과 순서)
  a_out N                  A: 칸 N 꺼내기 → 55 → 언로딩에 놓기 → 배출(At Exit 가림 → 풀림)
  goto  A|B N              크레인 이동(시작 → 정지 확인)
  fork  A|B left|right|middle
  lift  A|B on|off         (1.5 s)
  state                    두 크레인 상태"""
import sys, time, re
sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
import fio_scene as F
from pyModbusTCP.client import ModbusClient
scene, cmd, args = sys.argv[1], sys.argv[2], sys.argv[3:]
txt = F.load(scene); table = F.modbus_address_table(txt)
addr = {t["name"]: table[t["key"]][1] for t in F.tags(txt) if t["key"] in table}
run_key = re.search(r'RunOutputKey="([0-9a-f-]{36})"', txt).group(1)
run_addr = table[run_key][1]
c = ModbusClient("127.0.0.1", 502)
class Fail(Exception): pass
def sfx(k): return "" if k == "A" else " B"
def di(n):
    v = c.read_discrete_inputs(addr[n], 1)
    if v is None: raise Fail("Modbus 읽기 실패")
    return v[0]
def co(n, x): c.write_single_coil(addr[n], x)
def speed(v): c.write_single_register(addr["Load speed"], int(round(v * 100)) & 0xFFFF)
def until(fn, to, what):
    st = time.time()
    while time.time() - st < to:
        if fn(): return time.time() - st
        time.sleep(0.01)
    raise Fail(what)
def goto(k, p):
    s = sfx(k); c.write_single_register(addr["Target Position" + s], p); st = time.time()
    while time.time() - st < 3 and not (di("Moving X" + s) or di("Moving Z" + s)): time.sleep(0.02)
    until(lambda: not di("Moving X" + s) and not di("Moving Z" + s), 45, f"{k} 이동 {p}"); time.sleep(0.5)
def fork(k, side):
    s = sfx(k); co("Forks Left" + s, side == "left"); co("Forks Right" + s, side == "right")
    return until(lambda: di({"left": "At Left", "right": "At Right", "middle": "At Middle"}[side] + s), 8, f"{k} 포크 {side}")
def lift(k, on): co("Lift" + sfx(k), on); time.sleep(1.5)
def state(k):
    s = sfx(k)
    lim = [n for n in ("At Left", "At Middle", "At Right") if di(n + s)] or ["?"]
    mov = [n for n in ("Moving X", "Moving Z") if di(n + s)] or ["정지"]
    return f"{k}: 포크 {lim[0]} · {'/'.join(mov)}"
try:
    if cmd == "run":
        for n in ("Forks Left", "Forks Right", "Lift", "Forks Left B", "Forks Right B", "Lift B", "Unload Conveyor", "Entry Conveyor", "Emitter"): co(n, 0)
        speed(0); c.write_single_coil(run_addr, 1); time.sleep(1.5); goto("A", 55)
    elif cmd == "a_in":
        n = int(args[0])
        co("Emitter", 1); time.sleep(0.3); co("Emitter", 0)
        co("Entry Conveyor", 1); speed(4)
        t_in = until(lambda: not di("At Load"), 30, "At Load 감지 없음")
        co("Entry Conveyor", 0); speed(-2); time.sleep(0.15); speed(0); time.sleep(0.8)
        fork("A", "left"); lift("A", True); fork("A", "middle")
        if not di("At Load"): raise Fail("A가 못 집음")
        goto("A", n); fork("A", "right"); lift("A", False); fork("A", "middle")
        print(f"A 입고 · 칸 {n}에 넣음 (도착 {t_in:.1f} s)")
    elif cmd == "a_out":
        n = int(args[0])
        goto("A", n); fork("A", "right"); lift("A", True); fork("A", "middle")
        goto("A", 55); fork("A", "right"); lift("A", False); fork("A", "middle")
        co("Unload Conveyor", 1)
        until(lambda: not di("At Exit"), 20, "At Exit 감지 없음"); until(lambda: di("At Exit"), 20, "At Exit 안 풀림")
        co("Unload Conveyor", 0); print(f"A 칸 {n} 꺼내 배출 · 출구 감지 정상")
    elif cmd == "goto": goto(args[0], int(args[1])); print(f"{args[0]} 칸 {args[1]} 도착")
    elif cmd == "fork": print(f"{args[0]} 포크 {args[1]} {fork(args[0], args[1]):.1f} s")
    elif cmd == "lift": lift(args[0], args[1] == "on"); print(f"{args[0]} 리프트 {args[1]}")
    print(state("A"), "|", state("B"))
except Fail as e:
    print("실패:", e); print(state("A"), "|", state("B"))
