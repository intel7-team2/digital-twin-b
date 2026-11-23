"""체인 축 통과 배치 시험.
straight: 체인(+Z, 'Transf. right')을 계속 돌려 통과 → 'At right exit'만 가려지면 통과
divert  : 체인으로 들여 'At right entry'(Transfer 출구 가장자리)가 가려지면 체인 정지 → 1 s 정지 확인
          → 롤러(-) 'Unload' → 'At divert exit'만 가려지면 통과
반사형 센서: 평소 ON, 가리면 OFF."""
import sys, time
sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
import fio_scene as F
from pyModbusTCP.client import ModbusClient
scene = sys.argv[1]
txt = F.load(scene); table = F.modbus_address_table(txt)
addr = {t["name"]: table[t["key"]][1] for t in F.tags(txt) if t["key"] in table}
run_addr = F.modbus_points(txt)["count"]["BitOutput"] - 1
c = ModbusClient("127.0.0.1", 502)
EXIT = {"straight": "At right exit", "divert": "At divert exit"}
ROLL = {"divertU": "Unload", "divertL": "Load"}
OUT = ["Load", "Unload", "Transf. left", "Transf. right"]
def r():
    v = c.read_discrete_inputs(0, 40)
    if v is None: sys.exit("Modbus 읽기 실패: " + c.last_error_as_txt)
    return v
def blocked(v, n): return not v[addr[n]]
def co(n, x): c.write_single_coil(addr[n], x)
def exits(v): return {k for k, n in EXIT.items() if blocked(v, n)}
def run_one(mode):
    for n in OUT: co(n, 0)
    co("Emitter", 1); time.sleep(0.3); co("Emitter", 0)
    co("Transf. right", 1)                                   # 체인 올려 +Z로 들임
    st = time.time()
    while not blocked(r(), "At right entry"):
        if time.time() - st > 40: return f"{mode}: 실패 · Transfer 출구 가장자리 센서 감지 없음(40 s)"
        time.sleep(0.02)
    t_in = time.time() - st
    hit = set(); t_hit = None
    if mode.startswith("divert"):
        co("Transf. right", 0)                               # 체인 내려 정지
        t0 = time.time(); early = set()
        while time.time() - t0 < 2.0: early |= exits(r()); time.sleep(0.05)
        if early: return f"{mode}: 실패 · 정지 못 하고 {sorted(early)}로 나감"
        co(ROLL[mode], 1)                                    # 롤러 방향 시험
    st = time.time()
    while time.time() - st < 20:
        e = exits(r())
        if e and t_hit is None: t_hit = time.time() - st
        hit |= e
        if mode[:6] in hit and not e: break
        time.sleep(0.05)
    for n in OUT: co(n, 0)
    ok = hit == {mode[:6]}
    th = f"{t_hit:.1f} s" if t_hit is not None else "없음"
    stop = " · 정지 2 s 확인" if mode.startswith("divert") else ""
    return f"{mode}: {'통과' if ok else '실패'} · 가장자리 도착 {t_in:.1f} s{stop} · 출구 감지 {th} · 가려진 출구 {sorted(hit) or '없음'}"
c.write_single_coil(run_addr, 1); time.sleep(1)
v = r(); print("시작(가림=True)", {n: blocked(v, n) for n in ["At feed", "At right entry", "At right exit", "At divert exit"]}, flush=True)
for m in sys.argv[2:]: print(run_one(m), flush=True)
