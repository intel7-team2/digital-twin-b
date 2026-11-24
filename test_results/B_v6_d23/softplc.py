"""래더 명령어 목록(plc/ladder_mnemonic_v6.txt)을 PC에서 그대로 실행하는 간이 소프트 PLC + Factory I/O(Modbus) 연결 시험.
GX Simulator2 ↔ MX OPC는 쓰기 1회 약 0.2초라 입고점 0.15초 제동 같은 타이밍 시험이 안 되므로, 래더 '논리'를 씬에서 확인하는 용도.
시험 스크립트가 C 인계(투입)와 검사 엔진(Python serve) 응답을 대신함.
사용: softplc.py <씬> <시나리오: 판정 목록, 예 1,2,3> [제한 초]
  판정 1 = GOOD, 2 = RETEST(재검사에서 GOOD), 3 = NG(메인 NG → 재검사 라인 → NG OUT), H = 입고 뒤 발열 접수(격리). 뒤에 L을 붙이면 Large(6S, D1518 = 6)"""
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
    if tok.startswith("T"): return int(T.get(tok, [0.0, False])[0] * 10 + 1e-6)   # 타이머 현재값(100 ms 단위, GX와 같음)
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
import collections, os
OUT_DELAY = float(os.environ.get('OUT_DELAY', '0')); _q = collections.deque(); OUT_ONLY = set(filter(None, os.environ.get('OUT_ONLY', '').split(',')))
def io_out():
    co = {}; hr = {}
    for n, ar, a in outs_:
        if ar == "coil": co[a] = B.get(n, False)
        else: hr[a] = W.get(n, 0) & 0xFFFF
    co[run] = True                      # 같은 범위에 Run 코일이 있으면 꺼지지 않게
    if OUT_DELAY > 0:                   # 11-24: 실제 PLC 경로 지연 흉내(출력만 OUT_DELAY초 늦게 씀)
        _q.append((time.time(), co, hr))
        while len(_q) > 1 and time.time() - _q[1][0] >= OUT_DELAY: _q.popleft()
        if time.time() - _q[0][0] < OUT_DELAY: return
        _, co0, hr0 = _q[0]
        if OUT_ONLY:                    # 지정한 출력만 늦추고 나머지는 지금 값
            co = dict(co); hr = dict(hr)
            for n, ar, a in outs_:
                if n in OUT_ONLY:
                    if ar == "coil": co[a] = co0.get(a, False)
                    else: hr[a] = hr0.get(a, 0)
        else:
            co, hr = co0, hr0
    if co:
        lo, hi = min(co), max(co); c.write_multiple_coils(lo, [co.get(i, False) for i in range(lo, hi + 1)])
    if hr:
        lo, hi = min(hr), max(hr); c.write_multiple_registers(lo, [hr.get(i, 0) for i in range(lo, hi + 1)])

# ---------------- 바깥(투입 · 검사 엔진) 대신 ----------------
import os
TSCALE = float(os.environ.get("TSCALE", "1"))   # Factory I/O 툴바 Time Scale과 같은 값(2 · 3 · 4). 타이머만 그만큼 빨리 감
STOPAT = [(x.split("=")[0], int(x.split("=")[1])) for x in os.environ.get("STOPAT", "").split("|") if x]   # 예: STOPAT=D1760=10 (그 순간 멈춰 화면 확인)
FORCE = {k: v == "1" for k, v in (x.split("=") for x in os.environ.get("FORCE", "").split(",") if x)}   # 예: FORCE=X1511=1 (씬에 없는 센서 대신)
T0 = time.time()
def log(m): print(f"{time.time()-T0:6.1f}s {m}", flush=True)
pack_ids = list(range(101, 101 + len(plan)))
fed = 0; judged = {}; watch = ["D1525", "D1535", "D1558", "D1568", "D1750", "D1760", "D1517"]
prev = {}
def outside():
    global fed
    if fed < len(plan) and W.get("D1541", 0) == 0 and not B.get("M1510") and time.time() - T0 > 3:
        B["M1510"] = True; W["D1516"] = pack_ids[fed]; W["D1518"] = 6 if plan[fed].endswith("L") else 4; W["D1542"] = 1480; log(f"C 인계: PACK {pack_ids[fed]} 판정 계획 {plan[fed]}"); fed += 1
    # 메인 검사 핸드셰이크 D1710~D1714 ↔ D1700~D1703
    if W.get("D1710") == 1 and W.get("D1713", 0) == 0:
        pid = W.get("D1711"); p = plan[pack_ids.index(pid)] if pid in pack_ids else "1"
        j = {"1": 1, "H": 1, "2": 2, "3": 3}[p.rstrip("L")]; W["D1700"] = j; W["D1701"] = 5; W["D1702"] = 60; W["D1703"] = 250; W["D1713"] = 1
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
        if pid in pack_ids and plan[pack_ids.index(pid)].rstrip("L") == "H" and W.get(f"D{1810+k}", 0) > 0 and pid not in judged:
            judged[pid] = 1; W["D1697"] = k + 1; W["D1698"] = 410; B["M1672"] = True; log(f"발열 접수: 칸 {k+1} PACK {pid}")

# ---------------- 후보 리더 동시 판독 (11-24, 씬 V6_plc_16_RP 전용) ----------------
# 씬에 D2000~(②) · D2100~(③) 후보 리더가 있으면, 본 검사 스텝이 0 → 10(팔레트 정지)이 된 뒤 1.2초에
# 후보 모두에 명령 1(시리얼 읽기)을 내고 1.5초 뒤 결과를 한 줄로 남김. 래더는 이 번지를 쓰지 않음.
PROBE = {st: sorted({int(n[1:]) // 10 * 10 for n, ar, a in outs_ if re.match(rf"^D{p}\d\d$", n)})
         for st, p in (("②", "20"), ("③", "21"))}
PROBE = {k: v for k, v in PROBE.items() if v and os.environ.get("PROBE", "0") == "1"}   # 동시 명령은 리더를 멈추게 함(11-24) → 기본 끔
_pr = {st: {"prev": 0, "t10": None, "fired": None, "cid": {}} for st in PROBE}
def probe():
    for st, bases in PROBE.items():
        s = _pr[st]; step = W.get("D1750" if st == "②" else "D1760", 0); now = time.time()
        if s["prev"] == 0 and step == 10: s["t10"] = now
        s["prev"] = step
        if s["t10"] and s["fired"] is None and now - s["t10"] >= 1.2:
            for b in bases:
                W[f"D{b}"] = 1; s["cid"][b] = W.get(f"D{b+3}", 0); B[f"M{b+1}"] = True
            s["fired"] = now
        if s["fired"] and now - s["fired"] >= 1.5:
            res = []
            for b in bases:
                B[f"M{b+1}"] = False
                res.append(f"{b}:{W.get(f'D{b+5}', 0) if W.get(f'D{b+3}', 0) != s['cid'][b] else '-'}")
            log(f"후보 {st} " + " ".join(res)); s["t10"] = None; s["fired"] = None

# ---------------- 자동 화면 저장 (11-23) ----------------
# SHOTS=<폴더>를 주면 SHOT_EVERY초(기본 2)마다 화면을 JPEG로 저장하고 index.csv에 시각 · 주요 스텝 · 알람을 남김.
# 스캔을 늦추지 않도록 별도 스레드에서 찍음. Factory I/O 창을 최대화해 맨 앞에 두고 돌릴 것(가려진 창은 안 찍힘).
# 끝난 뒤 index.csv에서 문제가 난 시각을 찾아 그 전후 몇 장만 열어 보면 됨.
SHOTS = os.environ.get("SHOTS", ""); SHOT_EVERY = float(os.environ.get("SHOT_EVERY", "2")); SHOT_W = int(os.environ.get("SHOT_W", "1600"))
SHOT_KEYS = ["D1541", "D1548", "D1640", "D1641", "D1656", "D1549", "D1750", "D1657", "D1551", "D1760", "D1658", "D1659", "D1900", "D1901", "D1902"]
def _shooter():
    import threading, csv as _csv
    from PIL import ImageGrab
    os.makedirs(SHOTS, exist_ok=True)
    idx = open(os.path.join(SHOTS, "index.csv"), "w", encoding="utf-8-sig", newline="")
    wr = _csv.writer(idx); wr.writerow(["초", "파일"] + SHOT_KEYS + ["알람"]); stop = threading.Event()
    import ctypes
    from ctypes import wintypes
    try: ctypes.windll.user32.SetProcessDPIAware()          # 175% 배율에서도 실제 픽셀 좌표로
    except Exception: pass
    def fio_rect():
        """Factory I/O 창 영역만 찍음(다른 창 · 개인 화면이 들어가지 않게). 못 찾으면 None → 그 회차는 건너뜀"""
        h = ctypes.windll.user32.FindWindowW(None, "Factory IO")
        if not h or ctypes.windll.user32.IsIconic(h): return None
        r = wintypes.RECT(); ctypes.windll.user32.GetWindowRect(h, ctypes.byref(r))
        return (r.left, r.top, r.right, r.bottom) if r.right - r.left > 100 else None
    from PIL import Image
    def grab_fio(box):
        """Factory IO 창 내용만 PrintWindow(PW_RENDERFULLCONTENT)로 찍음 — 다른 창이 위에 있어도 가려진 부분까지(11-24).
        실패하면(검은 화면 등) 화면 영역 캡처로 대신함"""
        h = ctypes.windll.user32.FindWindowW(None, "Factory IO"); w, ht = box[2] - box[0], box[3] - box[1]
        u, g = ctypes.windll.user32, ctypes.windll.gdi32
        hdc = u.GetWindowDC(h); mdc = g.CreateCompatibleDC(hdc); bmp = g.CreateCompatibleBitmap(hdc, w, ht); g.SelectObject(mdc, bmp)
        ok = u.PrintWindow(h, mdc, 2)
        class BIH(ctypes.Structure):
            _fields_ = [("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_int32), ("biHeight", ctypes.c_int32), ("biPlanes", ctypes.c_uint16),
                        ("biBitCount", ctypes.c_uint16), ("biCompression", ctypes.c_uint32), ("biSizeImage", ctypes.c_uint32),
                        ("biXPelsPerMeter", ctypes.c_int32), ("biYPelsPerMeter", ctypes.c_int32), ("biClrUsed", ctypes.c_uint32), ("biClrImportant", ctypes.c_uint32)]
        bi = BIH(ctypes.sizeof(BIH), w, -ht, 1, 32, 0, 0, 0, 0, 0, 0); buf = ctypes.create_string_buffer(w * ht * 4)
        g.GetDIBits(mdc, bmp, 0, ht, buf, ctypes.byref(bi), 0)
        g.DeleteObject(bmp); g.DeleteDC(mdc); u.ReleaseDC(h, hdc)
        im = Image.frombuffer("RGB", (w, ht), buf, "raw", "BGRX", 0, 1)
        if not ok or im.convert("L").getextrema()[1] < 10: return ImageGrab.grab(bbox=box, all_screens=True)
        return im
    h0 = ctypes.windll.user32.FindWindowW(None, "Factory IO")
    if h0:                                                   # 시작할 때 Factory IO 창을 최대화하고 앞으로(가려지면 안 찍힘)
        ctypes.windll.user32.ShowWindow(h0, 3); ctypes.windll.user32.SetForegroundWindow(h0); time.sleep(0.5)
    def run():
        n = 0
        while not stop.is_set():
            t = time.time() - T0
            try:
                box = fio_rect()
                if box is None:
                    print("화면 저장: Factory IO 창을 못 찾음(최소화?) — 건너뜀", flush=True); stop.wait(SHOT_EVERY); continue
                im = grab_fio(box)
                if im.width > SHOT_W: im = im.resize((SHOT_W, int(im.height * SHOT_W / im.width)))
                fn = f"{n:04d}_{t:06.1f}s.jpg"; im.save(os.path.join(SHOTS, fn), quality=70)
                al = " ".join(a for a in ("M1951", "M1952", "M1953", "M1954", "M1955", "M1956", "M1957") if B.get(a))
                wr.writerow([f"{t:.1f}", fn] + [W.get(k, 0) for k in SHOT_KEYS] + [al]); idx.flush(); n += 1
            except Exception as e:
                print("화면 저장 오류:", e, flush=True)
            stop.wait(SHOT_EVERY)
        idx.close()
    th = threading.Thread(target=run, daemon=True); th.start()
    return stop
shot_stop = _shooter() if SHOTS else None
if SHOTS: log(f"자동 화면 저장: {SHOTS} ({SHOT_EVERY}초마다)")

# ---------------- 실행 ----------------
FIRST = True; last = time.time()
B["X1501"] = False
try:
    io_in(); scan(0.0); FIRST = False
    io_in(); B["X1501"] = True; scan(0.01); io_out(); log("시작 버튼(X1501)")
    end_need = len(plan)
    while time.time() - T0 < LIMIT:
        now = time.time(); dt = (now - last) * TSCALE; last = now   # Factory I/O 배속(Time Scale)과 맞춤
        io_in(); outside(); probe(); scan(dt); io_out()
        for w in watch:
            v = W.get(w, 0)
            if prev.get(w) != v: prev[w] = v; log(f"  {w} = {v}")
        for a in ("M1951", "M1952", "M1953", "M1954", "M1955", "M1956", "M1957"):
            if B.get(a) and not prev.get(a): log(f"  알람 {a}")
            prev[a] = B.get(a)
        done = W.get("D1900", 0) + W.get("D1901", 0) + W.get("D1902", 0)
        if prev.get("cnt") != done: prev["cnt"] = done; log(f"카운터 GOOD {W.get('D1900',0)} · NG {W.get('D1901',0)} · 격리 {W.get('D1902',0)}")
        if done >= end_need: log("모든 팩 배출"); break
        hit = [s_ for s_ in STOPAT if (B.get(s_[0]) if s_[0][0] in "MXY" else W.get(s_[0], 0)) == s_[1]]
        if hit: log(f"멈춤 조건 {hit}"); break
        time.sleep(0.005)
    print(f"결과: GOOD {W.get('D1900',0)} · NG {W.get('D1901',0)} · 격리 {W.get('D1902',0)} / 계획 {plan}", flush=True)
finally:
    if shot_stop: shot_stop.set(); time.sleep(0.5)
    for n, ar, a in outs_:
        if ar == "coil": B[n] = False
    io_out()
