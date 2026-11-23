"""V6 롤러 라인 구간 시험. 사용: sec.py <씬> <구간> [인자]
구간: s1 입고 | s2 크레인(칸) | s3 출고→CT1(main|iso) | s4 메인→CT2(good|retest) | s5 GOOD | s6 재검사(good|ng)
모든 X 센서는 반사형(가리면 OFF) → on() = 가림. 구간이 끝난 상태(팩 위치)를 다음 구간이 이어받음(씬을 다시 열지 않음)."""
import sys, time, re
sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
import fio_scene as F
from pyModbusTCP.client import ModbusClient
scene, sec = sys.argv[1], sys.argv[2]; arg = sys.argv[3] if len(sys.argv) > 3 else ""
txt = F.load(scene); table = F.modbus_address_table(txt)
A = {t["name"]: table[t["key"]] for t in F.tags(txt) if t["key"] in table}
run = table[re.search(r'RunOutputKey="([0-9a-f-]{36})"', txt).group(1)][1]
c = ModbusClient("127.0.0.1", 502); T0 = time.time()
class Stop(Exception): pass
import os
SOFT = os.environ.get("SOFT", "0") == "1"   # 11-23: 감속 방식은 8칸 중 2칸만 통과 → 기본은 원래 방식(4 V · −2 V 0.15 s); SLOW = int(os.environ.get("SLOW", "150"))
SLOWT = float(os.environ.get("SLOWT", "2.0")); BRK = (int(os.environ.get("BRK", "50")), float(os.environ.get("BRKT", "0.1")))
def rd(n):
    area, a, _ = A[n]
    v = {"di": c.read_discrete_inputs, "ir": c.read_input_registers, "coil": c.read_coils, "hr": c.read_holding_registers}[area](a, 1)
    if v is None: raise Stop("Modbus 읽기 실패")
    return v[0]
def on(n): return not rd(n)
def co(n, x): c.write_single_coil(A[n][1], bool(x))
def hr(n, v): c.write_single_register(A[n][1], int(v) & 0xFFFF)
def log(m): print(f"{time.time()-T0:6.1f}s {m}", flush=True)
def until(fn, to, what):
    st = time.time()
    while time.time() - st < to:
        if fn(): log(what); return time.time() - st
        time.sleep(0.01)
    raise Stop(f"{what} — {to} s 안에 안 됨")
def rfid(base, cmd, idx=0):
    co(f"M{base+1}", 0); hr(f"D{base+1}", idx); hr(f"D{base}", cmd); cid = rd(f"D{base+3}"); time.sleep(0.2)
    co(f"M{base+1}", 1)
    until(lambda: rd(f"D{base+3}") != cid, 3, f"RFID D{base} 명령 {cmd} 응답")
    co(f"M{base+1}", 0); time.sleep(0.2)
    return rd(f"D{base+4}"), rd(f"D{base+5}")
def crane(k, p):
    t, mx, mz = ("D1601", "X1600", "X1601") if k == "A" else ("D1602", "X1608", "X1609")
    hr(t, p); st = time.time()
    while time.time() - st < 3 and not (rd(mx) or rd(mz)): time.sleep(0.02)
    until(lambda: not rd(mx) and not rd(mz), 45, f"크레인 {k} → {p}"); time.sleep(0.5)
def fork(k, side):
    L, R, l, m, r = ("Y1600", "Y1601", "X1602", "X1603", "X1604") if k == "A" else ("Y1608", "Y1609", "X160A", "X160B", "X160C")
    co(L, side == "left"); co(R, side == "right")
    until(lambda: rd({"left": l, "middle": m, "right": r}[side]), 8, f"크레인 {k} 포크 {side}")
def lift(k, x): co("Y1602" if k == "A" else "Y160A", x); time.sleep(1.5)
try:
    c.write_single_coil(run, 1); time.sleep(1)
    if sec == "s1":
        bad = [t["name"] for t in F.tags(txt) if t["key"] in table and table[t["key"]][0] == "di" and re.match(r"X1[5-9]", t["name"])
               and t["name"] not in ("X1500", "X1501", "X1502", "X1503") and not re.match(r"X16[0-9A-C]{2}$", t["name"]) and on(t["name"])]
        bad += [t["name"] for t in F.tags(txt) if "loaded" in t["name"] and rd(t["name"])]
        if bad: raise Stop(f"빈 라인인데 감지 중인 센서: {bad}")
        log("빈 라인 센서 점검 통과")
        for n in ("Y1502", "Y1504", "Y1500"): co(n, 0)
        hr("Y1505 speed", 0); crane("A", 55); crane("B", 55)
        co("Y1501", 1); co("Y1501-2", 1); co("Y1502", 1)
        co("Y1500", 1); time.sleep(0.3); co("Y1500", 0)
        until(lambda: on("X1510"), 30, "RFID① 정위치 X1510")
        if arg == "stop": time.sleep(1.5); raise Stop("RFID① 정지까지만(관찰용)")
        time.sleep(1.5); log(f"정지 유지 X1510 = {'가림' if on('X1510') else '풀림'}")
        st, data = rfid(1510, 0); log(f"RFID① 태그 확인 상태 D1514 = {st} (0 정상 · 1 태그 없음 · 2 여러 개)")
        if st == 0:
            hr("D1512", 1234); st, _ = rfid(1510, 3, 0); st2, val = rfid(1510, 2, 0); log(f"RFID① 쓰기 1234 → 읽기 {val} (상태 {st2})")
            hr("D1512", 22200); rfid(1510, 3, 1); _, v2 = rfid(1510, 2, 1); hr("D1512", 40000); rfid(1510, 3, 2); _, v3 = rfid(1510, 2, 2)
            log(f"RFID① 22200 → {v2} · 40000 → {v3}(16비트 부호 없음이면 40000)")
        hr("D1512", 101); stw, _ = rfid(1510, 3, 0); time.sleep(0.3); str_, v = rfid(1510, 2, 0)
        log(f"RFID① PACK ID 101 쓰기 상태 {stw} → 다시 읽기 {v} (상태 {str_})")
        co("Y1502", 0); co("Y1504", 1); hr("Y1505 speed", 400)
        if SOFT:   # 11-23 수정: 4 V로 들어오다 팩이 로딩 컨베이어에 다 올라가면(X1513 풀림) 1.5 V로 줄이고, 입고점에서 약하게 제동
            until(lambda: on("X1513 entry"), 30, "로딩 컨베이어 입구 X1513")
            time.sleep(SLOWT); hr("Y1505 speed", SLOW); log(f"감속 {SLOW/100} V")   # 팔레트 틈으로 빛이 새서 X1513 풀림은 못 씀 → 시간
        until(lambda: on("X1512"), 30, "크레인 A 입고점 X1512")
        co("Y1501", 0); co("Y1501-2", 0); co("Y1504", 0)
        if SOFT: hr("Y1505 speed", -BRK[0]); time.sleep(BRK[1]); hr("Y1505 speed", 0)
        else: hr("Y1505 speed", -200); time.sleep(0.15); hr("Y1505 speed", 0)
        time.sleep(1); log(f"입고점 정지 X1512 = {'가림' if on('X1512') else '풀림'}")
    elif sec == "s2":
        cell = int(arg or 14)
        fork("A", "left"); lift("A", 1); fork("A", "middle")
        if on("X1512"): raise Stop("A가 집은 뒤에도 X1512 가림(못 집음)")
        crane("A", cell); fork("A", "right"); lift("A", 0); fork("A", "middle"); crane("A", 1)
        crane("B", cell); fork("B", "left"); lift("B", 1); fork("B", "middle")
        crane("B", 55); fork("B", "right"); lift("B", 0); fork("B", "middle")
        until(lambda: on("X1610"), 5, "B 출고점 X1610")
    elif sec.startswith("c"):                       # 크레인 단계별: c1 A 집기 · c2 A 넣기 · c3 B 꺼내기 · c4 B 내려놓기
        cell = int(arg or 14)
        if sec == "c1": fork("A", "left"); lift("A", 1); fork("A", "middle")
        if sec == "c2": crane("A", cell); fork("A", "right"); lift("A", 0); fork("A", "middle"); crane("A", 1)
        if sec == "c3": crane("B", cell); fork("B", "left"); lift("B", 1); fork("B", "middle")
        if sec == "c4": crane("B", 55); fork("B", "right"); lift("B", 0); fork("B", "middle")
    elif sec == "s3":
        for n in ("Y1610", "Y1611", "CT1 load", "CT1 left", "CT1 right", "Y1700-1", "Y1700-2", "Y1700", "Y1690", "Y1701"): co(n, 0)
        co("Y1701", 1); co("Y1610", 1); co("Y1611", 1); co("CT1 load", 1)
        until(lambda: on("X1660"), 20, "1차 분리 앞 X1660")
        until(lambda: rd("CT1 loaded"), 20, "CT1 도착 센서(롤러 정지)")
        co("CT1 load", 0); co("Y1611", 0); co("Y1610", 0); time.sleep(0.8)
        if arg == "iso":
            co("Y1690", 1); co("CT1 right", 1); until(lambda: on("X1902"), 20, "격리 게이트 X1902")
        else:
            co("Y1700-1", 1); co("Y1700-2", 1); co("Y1700", 1); co("CT1 left", 1)
            until(lambda: on("X1700"), 30, "메인 검사 정위치 X1700")
            co("CT1 left", 0); time.sleep(1.5); log(f"Roller Stop 정지 유지 X1700 = {'가림' if on('X1700') else '풀림'}")
    elif sec == "s4":
        st, _ = rfid(1520, 0); log(f"RFID② 태그 확인 상태 D1524 = {st}")
        st, v = rfid(1520, 2, 0); log(f"RFID② PACK ID 읽기 = {v} (상태 {st})")
        for n in ("CT2 load", "CT2 left", "CT2 right"): co(n, 0)
        co("Y1700", 1); co("Y1702", 1); co("CT2 load", 1); co("Y1701", 0)
        until(lambda: on("X1720"), 20, "CT2 앞 X1720")
        until(lambda: rd("CT2 loaded"), 20, "CT2 도착 센서(롤러 정지)")
        co("CT2 load", 0); co("Y1702", 0); co("Y1700", 0); time.sleep(0.8)
    elif sec == "s5":
        for n in ("Y1702-2", "Y1702-3", "Y1702-4", "Y1900"): co(n, 1)
        co("CT5 merge right", 1); co("CT2 left", 1)
        until(lambda: on("X1903 main"), 40, "합류 CT 앞 X1903 main")
        co("CT2 left", 0)
        until(lambda: on("X1900"), 40, "GOOD OUT 게이트 X1900")
        co("CT5 merge right", 0)
    elif sec == "s6":
        for n in ("Y1800", "Y1801", "Y1800-2", "Y1731", "Y1731-2", "Y1732", "Y1732-2", "Y1901", "Y1900"): co(n, 1)
        co("Y1730", 1); co("CT2 right", 1)
        until(lambda: on("X1800"), 20, "재검사 라인 입구 X1800")
        until(lambda: on("X1730"), 40, "재검사 정위치 X1730"); co("CT2 right", 0)
        time.sleep(1.0); st, _ = rfid(1530, 0); log(f"RFID③ 태그 확인 상태 D1534 = {st}")
        st, v = rfid(1530, 2, 0); log(f"RFID③ PACK ID 읽기 = {v} (상태 {st})")
        co("CT3 load", 1); co("Y1730", 0)
        until(lambda: on("X1731"), 20, "CT3 앞 X1731")
        until(lambda: rd("CT3 loaded"), 20, "CT3 도착 센서(롤러 정지)"); co("CT3 load", 0); co("Y1800-2", 0); time.sleep(0.8)
        if arg == "ng":
            co("CT3 right", 1); until(lambda: on("X1901"), 40, "NG OUT 게이트 X1901"); co("CT3 right", 0)
        else:
            co("CT3 left", 1); co("CT4 wait left", 1)
            until(lambda: rd("CT4 wait loaded"), 20, "대기 CT4 도착"); co("CT4 wait left", 0); co("CT3 left", 0); time.sleep(1.0)
            log(f"대기 CT4 정지 유지 = {'○' if rd('CT4 wait loaded') else '×'}")
            co("CT4 wait left", 1); co("CT5 merge load", 1)
            until(lambda: rd("CT5 merge loaded"), 30, "합류 CT5 도착"); co("CT5 merge load", 0); co("CT4 wait left", 0); time.sleep(0.8)
            co("CT5 merge right", 1); until(lambda: on("X1900"), 40, "GOOD OUT 게이트 X1900"); co("CT5 merge right", 0)
    print("결과: 통과", flush=True)
except Stop as e:
    print(f"결과: 실패 · {e}", flush=True)
