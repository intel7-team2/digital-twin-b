"""래더 명령어 목록(plc/ladder_mnemonic_v6.txt)을 PC에서 그대로 실행하는 간이 소프트 PLC + Factory I/O(Modbus) 연결 시험.
GX Simulator2 ↔ MX OPC는 쓰기 1회 약 0.2초라 입고점 0.15초 제동 같은 타이밍 시험이 안 되므로, 래더 '논리'를 씬에서 확인하는 용도.
시험 스크립트가 C 인계(투입)와 검사 엔진(Python serve) 응답을 대신함.
사용: softplc.py <씬> <시나리오: 판정 목록, 예 1,2,3> [제한 초]
  판정 1 = GOOD, 2 = RETEST(재검사에서 GOOD), 3 = NG(메인 NG → 재검사 라인 → NG OUT), H = 입고 뒤 발열 접수(격리)"""
import sys, re, time, io
sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
sys.path.insert(0, r"D:\seojung\digital-twin-b\test_results\a28_1123")   # pyModbusTCP 대체 모듈
import fio_scene as F
from pyModbusTCP.client import ModbusClient

SRC = r"D:\seojung\digital-twin-b\plc\ladder_mnemonic_v6.txt"
scene, plan = sys.argv[1], sys.argv[2].split(",")
LIMIT = float(sys.argv[3]) if len(sys.argv) > 3 else 600

# ---------------- 명령어 목록 읽기 ----------------
progs = []
for raw in io.open(SRC, encoding="utf-8"):
    m = re.match(r";\s*@PROGRAM\s+(\w+)", raw)
    if m: progs.append((m.group(1), [])); continue
    m = re.match(r"^([A-Z]\d\d)\s+(.*)$", raw.rstrip())
    if m and progs:
        body = m.group(2).split(";")[0]
        left, right = (body.split("=>", 1) if "=>" in body else ("", body))
        conds = [c.split() for c in left.split("|") if c.strip()]
        outs = [c.split() for c in right.split("|") if c.strip()]
        progs[-1][1].append((m.group(1), conds, outs))

# ---------------- 메모리 ----------------
B = {}            # 비트 X Y M SM
W = {}            # 워드 D Z
T = {}            # 타이머 이름 → [누적 s, 접점]
edge = {}
Z = {f"Z{i}": 0 for i in range(10)}
def addr(tok):
    m = re.match(r"^([DXYMTZ]|SM)([0-9A-F]+)(Z\d)?$", tok)
    kind, num, zi = m.groups()
    if kind in ("X", "Y"):
        n = int(num, 16) + (Z[zi] if zi else 0); return f"{kind}{n:X}"
    n = int(num) + (Z[zi] if zi else 0); return f"{kind}{n}"
def val(tok):
    if tok.startswith("K"): return int(tok[1:])
    if tok.startswith("Z"): return Z[tok]
    return W.get(addr(tok), 0)
def setw(tok, v):
    v = ((int(v) + 32768) % 65536) - 32768
    if tok.startswith("Z"): Z[tok] = v
    else: W[addr(tok)] = v
def bit(tok):
    if tok == "SM400": return True
    if tok == "SM402": return FIRST
    if tok == "SM412": return (time.time() % 1.0) < 0.5
    if tok.startswith("T"): return T.get(tok, [0, False])[1]
    return B.get(addr(tok), False)
CMP = {"=": lambda a, b: a == b, "<>": lambda a, b: a != b, ">=": lambda a, b: a >= b,
       "<=": lambda a, b: a <= b, ">": lambda a, b: a > b, "<": lambda a, b: a < b}

def cond_of(key, conds):
    st, acc = [], None
    for k, c in enumerate(conds):
        op = c[0]
        if op in ("ORB", "ANB"):
            a = st.pop(); acc = (a or acc) if op == "ORB" else (a and acc); continue
        m = re.match(r"^(LD|AND|OR)(=|<>|>=|<=|>|<)$", op)
        if m:
            kind, v = m.group(1), CMP[m.group(2)](val(c[1]), val(c[2]))
        else:
            kind = {"LD": "LD", "LDI": "LD", "LDP": "LD", "LDF": "LD", "AND": "AND", "ANI": "AND",
                    "OR": "OR", "ORI": "OR", "ORP": "OR", "ORF": "OR"}[op]
            raw = bit(c[1]); v = raw
            if op in ("LDI", "ANI", "ORI"): v = not raw
            if op in ("LDP", "LDF", "ORP", "ORF"):
                prev = edge.get((key, k), raw); edge[(key, k)] = raw
                v = (raw and not prev) if op in ("LDP", "ORP") else (prev and not raw)
        if kind == "LD":
            if acc is not None: st.append(acc)
            acc = v
        elif kind == "AND": acc = acc and v
        else: acc = acc or v
    return True if acc is None else acc

def run_outs(key, cnd, outs, mc, dt):
    """mc=False: MC 안에서 끔(OUT·타이머 OFF, 나머지 실행 안 함)"""
    for j, o in enumerate(outs):
        op = o[0]
        if op in ("OUT", "OUTH"):
            if o[1].startswith("T"):
                t = T.setdefault(o[1], [0.0, False])
                unit = 0.01 if op == "OUTH" else 0.1
                if cnd and mc: t[0] += dt; t[1] = t[0] >= int(o[2][1:]) * unit - 1e-6
                else: t[0], t[1] = 0.0, False
            else:
                B[addr(o[1])] = bool(cnd and mc)
            continue
        if op in ("PLS",):
            k = (key, "pls", j); prev = edge.get(k, False); edge[k] = bool(cnd and mc)
            B[addr(o[1])] = bool(cnd and mc and not prev); continue
        if op in ("INCP",):
            k = (key, "incp", j); prev = edge.get(k, False); now = bool(cnd and mc); edge[k] = now
            if now and not prev: setw(o[1], val(o[1]) + 1)
            continue
        if not (cnd and mc): continue
        if op == "SET": B[addr(o[1])] = True
        elif op == "RST": B[addr(o[1])] = False
        elif op == "MOV": setw(o[2], val(o[1]))
        elif op == "INC": setw(o[1], val(o[1]) + 1)
        elif op == "DEC": setw(o[1], val(o[1]) - 1)
        elif op == "+": setw(o[3], val(o[1]) + val(o[2]))
        elif op == "-": setw(o[3], val(o[1]) - val(o[2]))
        elif op == "*":
            r = val(o[1]) * val(o[2]); d = addr(o[3]); n = int(d[1:])
            W[d] = r & 0xFFFF; W[f"D{n+1}"] = (r >> 16) & 0xFFFF
        elif op == "D/":
            def l32(tok):
                d = addr(tok); n = int(d[1:]); lo = W.get(d, 0) & 0xFFFF; hi = W.get(f"D{n+1}", 0) & 0xFFFF
                v = lo | (hi << 16); return v - (1 << 32) if v >= 1 << 31 else v
            a, b = l32(o[1]), l32(o[2]); d = addr(o[3]); n = int(d[1:])
            q = int(a / b) if b else 0; r = a - q * b if b else 0
            W[d] = q & 0xFFFF; W[f"D{n+1}"] = (q >> 16) & 0xFFFF; W[f"D{n+2}"] = r & 0xFFFF; W[f"D{n+3}"] = (r >> 16) & 0xFFFF
        elif op == "FMOV":
            d = addr(o[2]); n = int(d[1:])
            for i in range(val(o[3])): W[f"D{n+i}"] = val(o[1])
        else:
            raise ValueError(f"{key}: 모르는 명령 {op}")

def scan(dt):
    for pname, rungs in progs:
        mc = True; i = 0
        while i < len(rungs):
            name, conds, outs = rungs[i]
            if outs and outs[0][0] == "FOR":
                n = val(outs[0][1]); j = next(k for k in range(i, len(rungs)) if rungs[k][2] and rungs[k][2][0][0] == "NEXT")
                for _ in range(n):
                    for k in range(i + 1, j):
                        nm, cs, os_ = rungs[k]
                        run_outs((pname, nm), cond_of((pname, nm), cs), os_, mc, dt)
                i = j + 1; continue
            if outs and outs[0][0] == "MC":
                c = cond_of((pname, name), conds); B[addr(outs[0][2])] = c; mc = c; i += 1; continue
            if outs and outs[0][0] == "MCR":
                mc = True; i += 1; continue
            run_outs((pname, name), cond_of((pname, name), conds), outs, mc, dt); i += 1

# ---------------- Factory I/O 연결 ----------------
txt = F.load(scene); table = F.modbus_address_table(txt)
ins, outs_ = [], []
for t in F.tags(txt):
    if t["key"] not in table: continue
    area, a, _ = table[t["key"]]
    if not re.match(r"^([XY][0-9A-F]{4}|[DM]\d{4})$", t["name"]): continue
    (ins if area in ("di", "ir") else outs_).append((t["name"], area, a))
c = ModbusClient("127.0.0.1", 502)
run = table[re.search(r'RunOutputKey="([0-9a-f-]{36})"', txt).group(1)][1]
c.write_single_coil(run, 1); time.sleep(1)
di_n = max([a for _, ar, a in ins if ar == "di"] + [0]) + 1
ir_n = max([a for _, ar, a in ins if ar == "ir"] + [0]) + 1
def io_in():
    d = c.read_discrete_inputs(0, di_n); r = c.read_input_registers(0, ir_n) if ir_n else []
    for n, ar, a in ins:
        if ar == "di": B[n] = bool(d[a])
        else: W[n] = ((r[a] + 32768) % 65536) - 32768
    for k, v in FORCE.items(): B[k] = v
def io_out():
    co = {}; hr = {}
    for n, ar, a in outs_:
        if ar == "coil": co[a] = B.get(n, False)
        else: hr[a] = W.get(n, 0) & 0xFFFF
    co[run] = True                      # 같은 범위에 Run 코일이 있으면 꺼지지 않게
    if co:
        lo, hi = min(co), max(co); c.write_multiple_coils(lo, [co.get(i, False) for i in range(lo, hi + 1)])
    if hr:
        lo, hi = min(hr), max(hr); c.write_multiple_registers(lo, [hr.get(i, 0) for i in range(lo, hi + 1)])

# ---------------- 바깥(투입 · 검사 엔진) 대신 ----------------
import os
FORCE = {k: v == "1" for k, v in (x.split("=") for x in os.environ.get("FORCE", "").split(",") if x)}   # 예: FORCE=X1511=1 (씬에 없는 센서 대신)
T0 = time.time()
def log(m): print(f"{time.time()-T0:6.1f}s {m}", flush=True)
pack_ids = list(range(101, 101 + len(plan)))
fed = 0; judged = {}; watch = ["D1524", "D1534", "D1549", "D1550", "D1551", "D1541", "D1548", "D1640", "D1641", "D1656", "D1657", "D1658", "D1659", "D1750", "D1760"]
prev = {}
def outside():
    global fed
    if fed < len(plan) and W.get("D1541", 0) == 0 and not B.get("M1510") and time.time() - T0 > 3:
        B["M1510"] = True; W["D1516"] = pack_ids[fed]; W["D1518"] = 4; W["D1542"] = 1480; log(f"C 인계: PACK {pack_ids[fed]} 판정 계획 {plan[fed]}"); fed += 1
    # 메인 검사 핸드셰이크 D1710~D1714 ↔ D1700~D1703
    if W.get("D1710") == 1 and W.get("D1713", 0) == 0:
        pid = W.get("D1711"); p = plan[pack_ids.index(pid)] if pid in pack_ids else "1"
        j = {"1": 1, "H": 1, "2": 2, "3": 3}[p]; W["D1700"] = j; W["D1701"] = 5; W["D1702"] = 60; W["D1703"] = 250; W["D1713"] = 1
        log(f"메인 검사 PACK {pid} → 판정 {j}")
    if W.get("D1710") == 0 and W.get("D1713") == 1: W["D1713"] = 0
    if W.get("D1740") == 1 and W.get("D1743", 0) == 0:
        W["D1730"] = 1; W["D1731"] = 5; W["D1732"] = 60; W["D1733"] = 250; W["D1743"] = 1; log(f"재검사 PACK {W.get('D1741')} → GOOD")
    if W.get("D1740") == 0 and W.get("D1743") == 1: W["D1743"] = 0
    if W.get("D1650") == 1 and W.get("D1653", 0) == 0: W["D1653"] = 1; log(f"격리 기록 PACK {W.get('D1651')} 온도 {W.get('D1652')}")
    if W.get("D1650") == 0 and W.get("D1653") == 1: W["D1653"] = 0
    # 발열 접수(H): 계획이 H인 팩이 랙에 들어가면 그 칸을 발열로
    for k in range(24):
        pid = W.get(f"D{1660+k}", 0)
        if pid in pack_ids and plan[pack_ids.index(pid)] == "H" and W.get(f"D{1810+k}", 0) > 0 and pid not in judged:
            judged[pid] = 1; W["D1697"] = k + 1; W["D1698"] = 410; B["M1672"] = True; log(f"발열 접수: 칸 {k+1} PACK {pid}")

# ---------------- 실행 ----------------
FIRST = True; last = time.time()
B["X1501"] = False
try:
    io_in(); scan(0.0); FIRST = False
    io_in(); B["X1501"] = True; scan(0.01); io_out(); log("시작 버튼(X1501)")
    end_need = len(plan)
    while time.time() - T0 < LIMIT:
        now = time.time(); dt = now - last; last = now
        io_in(); outside(); scan(dt); io_out()
        for w in watch:
            v = W.get(w, 0)
            if prev.get(w) != v: prev[w] = v; log(f"  {w} = {v}")
        for a in ("M1951", "M1952", "M1953", "M1954", "M1955", "M1956", "M1957"):
            if B.get(a) and not prev.get(a): log(f"  알람 {a}")
            prev[a] = B.get(a)
        done = W.get("D1900", 0) + W.get("D1901", 0) + W.get("D1902", 0)
        if prev.get("cnt") != done: prev["cnt"] = done; log(f"카운터 GOOD {W.get('D1900',0)} · NG {W.get('D1901',0)} · 격리 {W.get('D1902',0)}")
        if done >= end_need: log("모든 팩 배출"); break
        time.sleep(0.005)
    print(f"결과: GOOD {W.get('D1900',0)} · NG {W.get('D1901',0)} · 격리 {W.get('D1902',0)} / 계획 {plan}", flush=True)
finally:
    for n, ar, a in outs_:
        if ar == "coil": B[n] = False
    io_out()
