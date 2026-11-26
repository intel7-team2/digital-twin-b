"""v1(D 스텝 · MC)과 v2(M 스텝 · MC 없음) 래더를 같은 무작위 상태 · 입력에서 돌려 정착한 뒤 비교(11-25).
입력을 한 구간(40스캔 · 20초) 고정해 두고 구간 끝에서 출력 · 워드 · 스텝을 비교. 사용: python diff_v1_v2.py [회수]"""
import re, io, os, sys, random, time
H = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.join(H, "..", "..", "test_results", "B_v6_d23", "softplc.py")
S = io.open(BASE, encoding="utf-8").read(); code = S[S.index("# ---------------- 명령어 목록 읽기"):S.index("# ---------------- Factory I/O 연결")]
def load(p):
    g = {"re": re, "io": io, "os": os, "time": time, "SRC": p, "FIRST": False}; exec(code, g); return g
A, N = load(os.path.join(H, "..", "ladder_mnemonic_v6.txt")), load(os.path.join(H, "ladder_mnemonic_v2.txt"))
REL = {m[0]: int(m[1]) for m in re.findall(r"\| (\w+) \| M(\d+) \|", io.open(os.path.join(H, "steps_relay_v2.md"), encoding="utf-8").read())}
WD = {"C": "D1541", "I": "D1548", "A": "D1640", "B": "D1641", "T": "D1656", "M": "D1549", "K": "D1657", "P": "D1658", "Q": "D1659", "G": "D1654", "J": "D1750", "N": "D1760", "R1_": "D1545", "R2_": "D1555", "R3_": "D1565"}
def grp(n): m = re.match(r"^(R\d_|[A-Z])(\d+)$", n); return m[1], int(m[2])
ST = {}
for n in REL: p, k = grp(n); ST.setdefault(p, []).append(k)
words, bits = {}, set()
for g in (A, N):
    for _, rs in g["progs"]:
        for _, c, o in rs:
            for t in c + o:
                ks = [int(a[1:]) for a in t[1:] if re.match(r"^K-?\d+$", a)]
                for a in t[1:]:
                    m = re.match(r"^(D\d+)", a)
                    if m: words.setdefault(m[1], set()).update(ks)
                    elif re.match(r"^[XYM][0-9A-F]+$", a): bits.add(a)
stepM = {f"M{v}" for v in REL.values()}; skipM = stepM | {f"M{n}" for n in range(1541, 1553) if n not in (1542, 1543, 1545, 1546, 1547)} | {"M1755", "M1766"}
skipD = set(WD.values()) | {f"D{n}" for n in range(1870, 1894)} | {f"D{n}" for n in list(range(1900, 1905)) + list(range(1990, 2000))}   # 카운터: v2는 하강 에지(LDF)라 시작 때 1씩 안 올라감
TBL = [1, 2, 3, 4, 5, 6, 10, 11, 12, 13, 14, 15, 19, 20, 21, 22, 23, 24, 28, 29, 30, 31, 32, 33]
CNT = int(sys.argv[1]) if len(sys.argv) > 1 else 300; random.seed(int(time.time() * 1000) % 99991); bad, ex = {}, {}
class TT: time = staticmethod(lambda: 0.2)
for g in (A, N): g["time"] = TT
for it in range(CNT):
    W0 = {k: random.choice(sorted(v | {0, 1})) for k, v in words.items()}
    for i in range(24): W0[f"D{1660+i}"] = random.choice([0, 0, 101 + i]); W0[f"D{1810+i}"] = random.choice([0, 5]); W0[f"D{1840+i}"] = random.choice([0, 0, 0, 410]); W0[f"D{1610+i}"] = 0; W0[f"D{1870+i}"] = TBL[i]
    W0["D1697"] = 0; W0["D1642"] = random.randint(1, 24); W0["D1643"] = random.randint(1, 24); W0["D1544"] = random.choice([4, 6]); W0["D1518"] = random.choice([4, 6])
    cur = {p: random.choice(v) for p, v in ST.items()}
    for p in ("R1_", "R2_", "R3_"): cur[p] = 0      # 실행기는 요청이 있을 때만 돎
    if cur["C"] == 5: W0["D1519"] = 1
    B0 = {b: random.random() < .5 for b in bits if b[0] != "Y"}; B0["M1950"] = True; B0["X1500"] = B0["X1502"] = True; B0["X1501"] = False; B0["M1672"] = False
    B0["M1960"] = B0["M1961"] = B0["M1920"] = False   # 누름 버튼
    for k in stepM: B0[k] = False
    for k in (1545, 1546, 1547, 1555, 1556, 1557, 1565, 1566, 1567): B0[f"M{k}"] = False
    Z0 = {f"Z{i}": 0 for i in range(10)}; Z0["Z2"] = W0["D1642"] - 1; Z0["Z3"] = W0["D1643"] - 1
    seq = [{b: random.random() < .5 for b in bits if b[0] == "X" and b not in ("X1500", "X1501", "X1502", "X1503")} for _ in range(3)]
    stop = random.random() < .3; cid = [random.randint(0, 50) for _ in range(3)]; rdv = [random.choice([0, 101, 6200]) for _ in range(3)]
    res = []
    for g in (A, N):
        g["W"].clear(); g["W"].update(W0); g["B"].clear(); g["B"].update(B0); g["T"].clear(); g["edge"].clear(); g["Z"].update(Z0); g["FIRST"] = False
        for p, k in cur.items():
            if g is A: g["W"][WD[p]] = k
            else: g["B"][f"M{REL[p + str(k)]}"] = True
        snap = []
        for s in range(3):
            g["B"].update(seq[s]); g["B"]["X1502"] = not (stop and s == 1); g["B"]["X1501"] = stop and s == 2
            for d in ("D1513", "D1523", "D1533"): g["W"][d] = cid[s]
            for d in ("D1515", "D1525", "D1535"): g["W"][d] = rdv[s]
            for _ in range(120): g["scan"](0.5)
            r = {k: bool(g["B"].get(k)) for k in bits if k[0] in "YM" and k not in skipM}
            r.update({k: g["W"].get(k, 0) for k in words if k not in skipD})
            for p in ST:
                if g is A: r["step " + p] = g["W"].get(WD[p], 0)
                else: h = [k for k in ST[p] if g["B"].get(f"M{REL[p + str(k)]}")]; r["step " + p] = h[0] if len(h) == 1 else tuple(h)
            snap.append(r)
        res.append(snap)
    for s, (x, y) in enumerate(zip(*res)):
        df = {k: (x[k], y[k]) for k in x if x[k] != y[k]}
        if df:
            for k in df: bad[k] = bad.get(k, 0) + 1
            ex.setdefault(tuple(sorted(df))[:4], (s, stop, df, {p: cur[p] for p in ST}))
            break
print(f"{CNT}회 · 다름 {sum(1 for _ in ex)}종", sorted(bad.items(), key=lambda kv: -kv[1])[:40])
for k, v in list(ex.items())[:10]: print(k, v)
