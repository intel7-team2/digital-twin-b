"""두 명령어 목록이 같은 동작인지 무작위 상태 · 입력으로 비교(11-25 래더 압축 확인).
상태(D 스텝 값 · 타이머 · 비트 · 입력)를 무작위로 잡고 둘을 같은 값에서 N스캔 돌려 모든 디바이스를 비교.
사용: python ladder_diff.py <예전 목록> <새 목록> [회수=20000] [스캔=4]"""
import re, sys, io, random, time
H = io.open(__file__.replace("ladder_diff.py", "softplc.py"), encoding="utf-8").read()
code = H[H.index("# ---------------- 명령어 목록 읽기"):H.index("# ---------------- Factory I/O 연결")]
def load(path):
    g = {"re": re, "io": io, "time": time, "SRC": path, "FIRST": False}
    exec(code, g); return g
A, N = load(sys.argv[1]), load(sys.argv[2])
CNT = int(sys.argv[3]) if len(sys.argv) > 3 else 20000; SC = int(sys.argv[4]) if len(sys.argv) > 4 else 4
words, bits, tims = {}, set(), set()
for g in (A, N):
    for _, rungs in g["progs"]:
        for _, c, o in rungs:
            for t in c + o:
                for a in t[1:]:
                    if re.match(r"^D\d+(Z\d)?$", a): words.setdefault(re.match(r"D\d+", a)[0], set())
                    elif re.match(r"^[XYM][0-9A-F]+$", a): bits.add(a)
                    elif re.match(r"^T\d+$", a): tims.add(a)
                ds = [a for a in t[1:] if re.match(r"^D\d+", a)]; ks = [int(a[1:]) for a in t[1:] if re.match(r"^K-?\d+$", a)]
                for d in ds: words[re.match(r"D\d+", d)[0]] |= set(ks)
for b in (1660, 1810, 1840, 1610, 1870):
    for i in range(24): words.setdefault(f"D{b+i}", set())
words = {k: sorted(v | {0, 1}) for k, v in words.items()}
bits -= {f"M{n}" for n in range(1541, 1553)} & set()
tset = {}
for _, rungs in A["progs"]:
    for _, c, o in rungs:
        for t in o:
            if t[0] in ("OUT", "OUTH") and t[1][0] == "T": tset[t[1]] = int(t[2][1:]) * (0.01 if t[0] == "OUTH" else 0.1)
random.seed(int(time.time()) if "--seed" not in sys.argv else 1); bad = {}; ex = {}
FZ = [0.0]
class TT:
    time = staticmethod(lambda: FZ[0])
for g in (A, N): g["time"] = TT
for it in range(CNT):
    W0 = {k: random.choice(v) if random.random() < .9 else random.randint(0, 400) for k, v in words.items()}
    B0 = {b: random.random() < .5 for b in bits}; B0["M1950"] = random.random() < .95
    W0["D1548"] = random.choice([0, 10, 15, 20, 30, 40])                      # 없는 스텝 번호는 뺌
    if W0["D1541"] == 5: W0["D1519"] = 1; B0["X1510"] = True                   # 스텝 5는 X1510 ON에서만 시작하고 첫 스캔에 D1519 = 1
    T0 = {t: [x := random.choice([0.0, tset[t] * random.random(), tset[t]]), x >= tset[t] - 1e-6] for t in tset}
    Z0 = {f"Z{i}": random.randint(0, 23) for i in range(10)}
    seq = [{b: random.random() < .5 for b in bits if b[0] == "X"} if random.random() < .5 else {} for _ in range(SC)]
    dts = [random.choice([.05, .1, 1.0, 3.0]) for _ in range(SC)]
    if seq[0].get("X1510") is False and W0["D1541"] in (0, 5): seq[0]["X1510"] = True
    fz = [random.random() * 5 for _ in range(SC)]; first = random.random() < .1
    res = []
    for g in (A, N):
        g["W"].clear(); g["W"].update(W0); g["B"].clear(); g["B"].update(B0); g["T"].clear(); g["T"].update({k: list(v) for k, v in T0.items()})
        g["Z"].update(Z0); g["edge"].clear(); g["FIRST"] = first; snap = []
        for s in range(SC):
            FZ[0] = fz[s]; g["B"].update(seq[s]); g["scan"](dts[s]); g["FIRST"] = False
            snap.append((dict(g["W"]), dict(g["B"]), {k: (round(v[0], 4), v[1]) for k, v in g["T"].items()}))
        res.append(snap)
    for s, (x, y) in enumerate(zip(*res)):
        df = [k for p, q in zip(x, y) for k in set(p) | set(q) if p.get(k) != q.get(k)]
        if df:
            for k in df: bad[k] = bad.get(k, 0) + 1
            ex.setdefault(tuple(sorted(df))[:6], (it, s, {k: (x[0].get(k, x[1].get(k)), y[0].get(k, y[1].get(k))) for k in df}, {k: W0.get(k) for k in df}))
            break
print(f"비교 {CNT}회 × {SC}스캔 · 다른 디바이스 {len(bad)}개", sorted(bad.items(), key=lambda kv: -kv[1])[:30])
for k, v in list(ex.items())[:8]: print(k, v)
