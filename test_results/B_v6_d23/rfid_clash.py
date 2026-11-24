"""RFID 리더 동시 명령 충돌 시험(11-24). 팔레트가 ② · ③ 자리에 서 있는 상태에서(softplc STOPAT=D1760=10 뒤)
리더를 단독 / 동시 / 엇갈려 명령해 판독(래더와 같은 순서: 명령 1 시리얼 → 명령 2 메모리 0 읽기) 성공률을 셈.
사용: python rfid_clash.py <씬> <반복 수>"""
import sys, re, time, threading
sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
sys.path.insert(0, r"D:\seojung\digital-twin-b\test_results\a28_1123")   # pyModbusTCP 대체 모듈
import fio_scene as F
from pyModbusTCP.client import ModbusClient
scene, N = sys.argv[1], int(sys.argv[2])
txt = F.load(scene); table = F.modbus_address_table(txt)
T = {}
for tg in F.tags(txt):
    if tg["key"] in table: T.setdefault(tg["name"], []).append(table[tg["key"]])
lock = threading.Lock()
c = ModbusClient("127.0.0.1", 502, auto_open=True)
def co(k, v):
    with lock:
        for ar, a, _ in T[k]: c.write_single_coil(a, v)
def hr(k, v):
    with lock:
        for ar, a, _ in T[k]: c.write_single_register(a, v & 0xFFFF)
def ir(k):
    with lock: return c.read_input_registers(T[k][0][1], 1)[0]
def one(b, cmd, idx=0):
    """리더 b(D 번호)에 명령. Command ID가 바뀌면 (상태, 읽은 값), 2초 안에 안 바뀌면 None"""
    co(f"M{b+1}", 0); hr(f"D{b+1}", idx); hr(f"D{b}", cmd); cid = ir(f"D{b+3}"); time.sleep(0.15); co(f"M{b+1}", 1)
    st = time.time()
    while time.time() - st < 2:
        if ir(f"D{b+3}") != cid: break
        time.sleep(0.02)
    else:
        co(f"M{b+1}", 0); return None
    co(f"M{b+1}", 0); time.sleep(0.1); return ir(f"D{b+4}"), ir(f"D{b+5}")
def seq(b, res):
    """래더와 같은 두 단계: 명령 1(시리얼) → 명령 2(메모리 0 읽기)"""
    r1 = one(b, 1); r2 = one(b, 2, 0) if r1 else None
    res[b] = (r1, r2)
def trial(bases, lag=0.0):
    res = {}; th = []
    for i, b in enumerate(bases):
        t = threading.Thread(target=seq, args=(b, res)); th.append(t); t.start(); time.sleep(lag)
    for t in th: t.join()
    return res
print("기준 값:", {b: trial([b])[b] for b in (1520, 1530)}, flush=True)
cases = [("② 단독", [1520], 0), ("③ 단독", [1530], 0), ("② · ③ 동시", [1520, 1530], 0),
         ("② · ③ 0.3초 엇갈림", [1520, 1530], 0.3)]
if "D2000" in T: cases.append(("② · 같은 자리 후보 동시(같은 태그)", [1520, 2000], 0))
for name, bases, lag in cases:
    ok = {b: 0 for b in bases}; fail = []
    for i in range(N):
        r = trial(bases, lag)
        for b in bases:
            r1, r2 = r[b]
            if r1 and r2: ok[b] += 1
            else: fail.append((i, b, r1, r2))
        time.sleep(0.3)
    print(f"{name}: " + " · ".join(f"D{b} {ok[b]}/{N}" for b in bases) + (f"  실패 예 {fail[:3]}" if fail else ""), flush=True)
