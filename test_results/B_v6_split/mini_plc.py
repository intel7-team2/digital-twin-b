"""명령어 목록 일부(COMMON A · RFID · INFEED)를 PC에서 돌려 보는 간이 해석기 + 가짜 RFID 리더.
GX Simulator2 확인 전 논리 점검용. 사용: mini_plc.py <mnemonic> [시나리오]"""
import re, sys
src = sys.argv[1]; scen = sys.argv[2] if len(sys.argv) > 2 else "new"
progs, cur = {}, None
for l in open(src, encoding="utf-8"):
    m = re.match(r";\s*@PROGRAM\s+(\w+)", l)
    if m: cur = m.group(1); progs[cur] = []; continue
    m = re.match(r"^([A-Z]\d\d)\s+(.*)$", l.rstrip())
    if m and cur: progs[cur].append((m.group(1), m.group(2).split(";")[0]))
RUN = ["COMMON", "RFID", "INFEED"]
D, M, X, T = {}, {}, {}, {}   # T: name -> [count, on]
edge = {}
def val(tok):
    if tok.startswith("K"): return int(tok[1:])
    return D.get(tok, 0)
def bit(tok):
    k = tok[0]
    if k == "X": return X.get(tok, False)
    if k == "T": return T.get(tok, [0, False])[1]
    if tok == "SM400": return True
    if tok in ("SM412", "SM402"): return False
    return M.get(tok, False)
CMP = {"=": lambda a, b: a == b, "<>": lambda a, b: a != b, ">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b, ">": lambda a, b: a > b, "<": lambda a, b: a < b}
SCAN = 0.01
def run_rung(name, body, mc):
    left, right = (body.split("=>", 1) + [""])[:2] if "=>" in body else ("", body)
    st = []   # stack of block values
    acc = None
    for ins in [c.strip() for c in left.split("|") if c.strip()]:
        p = ins.split(); op = p[0]
        m = re.match(r"^(LD|AND|OR)(=|<>|>=|<=|>|<)$", op)
        if m:
            v = CMP[m.group(2)](val(p[1]), val(p[2])); kind = m.group(1)
        elif op in ("ORB", "ANB"):
            b = acc; a = st.pop()
            acc = (a or b) if op == "ORB" else (a and b); continue
        else:
            kind = {"LD": "LD", "LDI": "LD", "LDP": "LD", "LDF": "LD", "AND": "AND", "ANI": "AND", "OR": "OR", "ORI": "OR", "ORP": "OR"}[op]
            v = bit(p[1])
            if op in ("LDI", "ANI", "ORI"): v = not v
            if op in ("LDP", "LDF", "ORP"):
                key = (name, ins); prev = edge.get(key, v if False else bit(p[1]) if False else edge.get(key, False))
                raw = bit(p[1]); prev = edge.get(key, False); edge[key] = raw
                v = (raw and not prev) if op in ("LDP", "ORP") else (prev and not raw)
        if kind == "LD":
            if acc is not None: st.append(acc)
            acc = v
        elif kind == "AND": acc = acc and v
        else: acc = acc or v
    cond = True if acc is None else acc
    cond = cond and mc
    for ins in [c.strip() for c in right.split("|") if c.strip()]:
        p = ins.split(); op = p[0]
        if op == "OUT":
            if p[1].startswith("T"):
                t = T.setdefault(p[1], [0, False])
                if cond: t[0] += SCAN * 10; t[1] = t[0] >= int(p[2][1:])
                else: t[0], t[1] = 0, False
            else: M[p[1]] = cond
        elif not cond: continue
        elif op == "SET": M[p[1]] = True
        elif op == "RST": M[p[1]] = False
        elif op == "MOV": D[p[2]] = val(p[1])
        elif op == "INC": D[p[1]] = D.get(p[1], 0) + 1
        elif op == "DEC": D[p[1]] = D.get(p[1], 0) - 1
        elif op == "PLS": pass
        elif op == "MC": return "MC"
        elif op == "MCR": return "MCR"
    return None
tag = {0: 55} if scen == "dup" else {}
reader = {"busy": 0, "prev": False}
def fake_reader():
    exe = M.get("M1511", False)
    if exe and not reader["prev"]: reader["busy"] = 3
    reader["prev"] = exe
    if reader["busy"]:
        reader["busy"] -= 1
        if reader["busy"] == 0:
            cmd, idx = D.get("D1510", 0), D.get("D1511", 0)
            if cmd == 3: tag[idx] = D.get("D1512", 0)
            if cmd == 2: D["D1515"] = tag.get(idx, 0)
            if cmd == 1: D["D1515"] = 777
            D["D1514"] = 0; D["D1513"] = D.get("D1513", 0) + 1
            log.append(f"리더 명령 {cmd} idx {idx} 실행" + (f" (쓰기 {D.get('D1512')})" if cmd == 3 else ""))
log = []
# 초기 조건: 운전 중 · 투입 요청 · 셀 수 4 · PACK ID 101 · 전압 1480
M.update({"M1950": True, "M1510": True}); D.update({"D1518": 4, "D1516": 101, "D1542": 1480}); X["X1500"] = True
steps = []
for scan in range(4000):
    if D.get("D1541") == 5 and scan > 5: X["X1510"] = True          # 팩 도착
    for pn in RUN:
        mc = True
        for name, body in progs[pn]:
            if name.startswith("S") or name.startswith("H"): continue
            r = run_rung(name, body, mc)
            if r == "MC": mc = M.get("M1950", False)
            if r == "MCR": mc = True
    fake_reader()
    s = D.get("D1541", 0)
    if not steps or steps[-1][1] != s: steps.append((scan, s))
    if s == 31: X["X1510"] = False
    if (s == 0 and scan > 50) or (s == 15 and scen == "dup" and scan > 300): break
print("스텝 변화:", " → ".join(f"{s}" for _, s in steps))
print("\n".join(log))
print("태그:", tag, "| 알람 M1951/M1952:", M.get("M1951"), M.get("M1952"), "| 인계 D1543 D1544:", D.get("D1543"), D.get("D1544"), "| 스캔", scan)
