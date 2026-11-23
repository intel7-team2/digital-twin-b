"""크레인 연속 사이클(단계별 확인으로 정한 순서). 사용: crane_cycle.py <씬> <칸> [<칸> ...]
1 투입: Emitter 펄스 → 입고 ON + 로딩 4 V → At Load 가림 즉시 입고 OFF · 로딩 −2 V 0.15 s → 0
2 집기: 55에서 포크 왼쪽 → 리프트 ON → 포크 가운데
3 넣기: 목표 칸 → 포크 오른쪽 → 리프트 OFF → 가운데
4 꺼내기: 포크 오른쪽 → 리프트 ON → 가운데
5 내려놓기: 55 → 포크 오른쪽 → 리프트 OFF → 가운데
6 배출: 언로딩 컨베이어 ON → At Exit 가림 → 풀림
판정: 각 단계의 리밋 · 이동 신호, 집은 뒤 At Load 풀림, 배출 At Exit 가림→풀림."""
import sys, time, re
sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
import fio_scene as F
from pyModbusTCP.client import ModbusClient
scene, cells = sys.argv[1], [int(x) for x in sys.argv[2:]]
txt = F.load(scene); table = F.modbus_address_table(txt)
addr = {t["name"]: table[t["key"]][1] for t in F.tags(txt) if t["key"] in table}
run_key = re.search(r'RunOutputKey="([0-9a-f-]{36})"', txt).group(1)
run_addr = next(a for k, (area, a, kind) in table.items() if k == run_key)
c = ModbusClient("127.0.0.1", 502)
class Fail(Exception): pass
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
def goto(p):
    c.write_single_register(addr["Target Position"], p)
    st = time.time()
    while time.time() - st < 3 and not (di("Moving X") or di("Moving Z")): time.sleep(0.02)
    until(lambda: not di("Moving X") and not di("Moving Z"), 45, f"이동 {p}"); time.sleep(0.5)
def fork(side):
    co("Forks Left", side == "left"); co("Forks Right", side == "right")
    until(lambda: di({"left": "At Left", "right": "At Right", "middle": "At Middle"}[side]), 8, f"포크 {side}")
def lift(on): co("Lift", on); time.sleep(1.5)
for n in ("Forks Left", "Forks Right", "Lift", "Unload Conveyor", "Entry Conveyor", "Emitter"): co(n, 0)
speed(0); c.write_single_coil(run_addr, 1); time.sleep(1.5); goto(55)
ok = 0
for i, cell in enumerate(cells, 1):
    t0 = time.time(); step = "투입"
    try:
        co("Emitter", 1); time.sleep(0.3); co("Emitter", 0)
        co("Entry Conveyor", 1); speed(4)
        t_in = until(lambda: not di("At Load"), 30, "At Load 감지 없음")
        co("Entry Conveyor", 0); speed(-2); time.sleep(0.15); speed(0); time.sleep(0.8)
        step = "집기"; fork("left"); lift(True); fork("middle")
        if not di("At Load"): raise Fail("집은 뒤에도 At Load 가림(못 집음)")
        step = "넣기"; goto(cell); fork("right"); lift(False); fork("middle")
        step = "꺼내기"; time.sleep(0.5); fork("right"); lift(True); fork("middle")
        step = "내려놓기"; goto(55); fork("right"); lift(False); fork("middle")
        step = "배출"; co("Unload Conveyor", 1)
        until(lambda: not di("At Exit"), 20, "At Exit 감지 없음")
        until(lambda: di("At Exit"), 20, "At Exit 안 풀림")
        co("Unload Conveyor", 0)
        ok += 1
        print(f"{i}. 칸 {cell}: 통과 · 도착 {t_in:.1f} s · 사이클 {time.time()-t0:.1f} s", flush=True)
    except Fail as e:
        print(f"{i}. 칸 {cell}: 실패 · {step} 단계 · {e}", flush=True)
        for n in ("Forks Left", "Forks Right", "Lift", "Unload Conveyor", "Entry Conveyor"): co(n, 0)
        speed(0); break
print(f"결과: {ok}/{len(cells)}")
