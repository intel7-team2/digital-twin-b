"""실제 PLC(GX Simulator2) + MX OPC + Factory I/O(OPC 씬) 6팩 시험용 — 바깥(C 인계 · 검사 엔진 · 발열 접수)을 OPC로 대신함(11-24).
softplc.py의 outside()와 같은 동작. 래더는 GX Simulator2가 돌리고, 이 스크립트는 바깥 신호만 읽고 씀.
사용: py -3.12 opc_outside.py <계획 예: 1,2L,3,H,1L,2> <제한 초> [--device CSIM] [--bridge <Modbus 씬>] [--serve]
  --serve: 검사 · 격리 기록 응답을 하지 않음(measurement_engine.py serve가 함). 계획의 판정 숫자는 무시, L(6S) · H(발열)만 씀
준비: GX Works2 시뮬레이션 RUN · MX OPC 프로젝트 MXOPC_B_v6_d24b.mdb(태그 359).
  --bridge 없이: Factory I/O에 V6_plc_17_opc(OPC Client 씬)를 열고 실행.
  --bridge 씬:  Factory I/O에 Modbus 씬(V6_plc_17)을 열고, 이 스크립트가 Factory I/O(Modbus) ↔ PLC(MX OPC)를 중계.
     11-24: Factory I/O OPC Client가 센서(입력) 쓰기에서 MX OPC '지정되지 않은 오류'를 받아(출력은 정상) 이 방식으로 시험."""
import sys, os, time, ctypes
sys.path.insert(0, r"D:\seojung\digital-twin-b")
import plc_link as P

plan = [x for x in sys.argv[1].split(",") if x and x != "-"]; LIMIT = float(sys.argv[2])   # 11-27: 계획 "-" = 팩 없이 중계만(HMI 버튼 · 수동 시험용, 카운터도 지우지 않음)
DEV = sys.argv[sys.argv.index("--device") + 1] if "--device" in sys.argv else "CSIM"
SERVE = "--serve" in sys.argv                               # 11-26: 검사 · 격리 기록 응답은 measurement_engine.py serve가 함(여기서는 기록만). C 인계 · 발열 접수는 그대로 대행
HOLDRUN = "--hold" in sys.argv                             # 11-27: 팩이 다 나와도 제한 시간까지 중계 유지(시연 · HMI 수거)


class Link(P.OpcDirectLink):
    def read_many(self, devs):
        """여러 번지를 SyncIO.Read 한 번으로(캐시). 품질이 Good이 아니면 None"""
        with self._lock:
            hs = (ctypes.c_ulong * len(devs))(*[self._item(d)[0] for d in devs])
            st, err = ctypes.POINTER(P._ITEMSTATE)(), ctypes.POINTER(ctypes.c_long)()
            hr = self._call(self._sio, 3, ctypes.c_ulong, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong),
                            ctypes.POINTER(ctypes.POINTER(P._ITEMSTATE)), ctypes.POINTER(ctypes.POINTER(ctypes.c_long)))(
                self._sio, P.OPC_DS_CACHE, len(devs), hs, ctypes.byref(st), ctypes.byref(err))
            if hr not in (0, 1) or not st:
                raise P.LinkError(f"일괄 읽기 실패 0x{hr & 0xFFFFFFFF:08X}")
            out = {}
            for i, d in enumerate(devs):
                try:
                    out[d] = self._value(st[i].val) if (err[i] == 0 and st[i].q == P.QUALITY_GOOD) else None
                finally:
                    ctypes.windll.oleaut32.VariantClear(ctypes.byref(st[i].val))
            self._ole32.CoTaskMemFree(st); self._ole32.CoTaskMemFree(err)
            return out

    def write_many(self, pairs):
        """여러 번지를 SyncIO.Write 한 번으로. 실패한 번지 목록을 돌려줌"""
        if not pairs: return []
        with self._lock:
            hs = (ctypes.c_ulong * len(pairs))(); vs = (P._VARIANT * len(pairs))()
            for i, (d, value) in enumerate(pairs):
                h, vt = self._item(d); hs[i] = h; vt = vt if vt in P._VT_FMT else 2; vs[i].vt = vt
                fmt = P._VT_FMT[vt]
                v = (-1 if value else 0) if vt == 11 else (int(value) & {"<H": 0xFFFF, "<I": 0xFFFFFFFF, "<B": 0xFF}[fmt] if fmt in ("<H", "<I", "<B") else int(value))
                P.struct.pack_into(fmt, vs[i].v, 0, v)
            err = ctypes.POINTER(ctypes.c_long)()
            hr = self._call(self._sio, 4, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(P._VARIANT),
                            ctypes.POINTER(ctypes.POINTER(ctypes.c_long)))(self._sio, len(pairs), hs, vs, ctypes.byref(err))
            bad = [pairs[i][0] for i in range(len(pairs)) if err and err[i]] if err else [d for d, _ in pairs]
            if err: self._ole32.CoTaskMemFree(err)
            return bad


OVR = {}; ESTOP = []                                        # --estop "X1500@D1640=11|X1502@D1750=12": softplc.py ESTOP과 같음(6초 누름 → 뗌 → 시작 버튼)
if "--estop" in sys.argv: ESTOP = [(x.split("@")[0],) + tuple(x.split("@")[1].split("=")) for x in sys.argv[sys.argv.index("--estop") + 1].split("|")]
_es = {"t": None, "n": 0}
L = Link(device=DEV, source=P.OPC_DS_CACHE)
T0 = time.time()
def log(m): print(f"{time.time()-T0:6.1f}s {m}", flush=True)
BR = None
if "--bridge" in sys.argv:                                  # Factory I/O(Modbus) ↔ PLC(OPC) 중계 준비
    import re
    sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use"); sys.path.insert(0, r"D:\seojung\digital-twin-b\test_results\a28_1123")
    import fio_scene as F
    from pyModbusTCP.client import ModbusClient
    txt = F.load(sys.argv[sys.argv.index("--bridge") + 1]); tb = F.modbus_address_table(txt)
    BR = {"in": [], "out": [], "sent": {}}
    for tg in F.tags(txt):
        if tg["key"] in tb and re.match(r"^([XY][0-9A-F]{4}|[DM]\d{4})$", tg["name"]):
            ar, a, _ = tb[tg["key"]]; (BR["in"] if ar in ("di", "ir") else BR["out"]).append((tg["name"], ar, a))
    # 11-27 검토: 시작 전에 씬 주소 겹침 검사(11-27 리무버 태그 Address가 크레인 B 포크와 겹쳐 포크가 멈춘 일)
    _dup = [k for k in set((ar, a) for _, ar, a in BR["in"] + BR["out"]) if sum(1 for _, ar, a in BR["in"] + BR["out"] if (ar, a) == k) > 1]
    _tagaddr = {}
    for _m in re.finditer(r'<(\w+(?:Input|Output)) Name="([^"]*)" Address="(-?\d+)"', txt): _tagaddr.setdefault((_m.group(1), _m.group(3)), []).append(_m.group(2))
    _dup2 = {k: v for k, v in _tagaddr.items() if len(v) > 1 and k[1] != "-1"}
    _dupn = sorted({n for n, _, _ in BR["in"]} & {n for n, _, _ in BR["out"]}) + sorted(n for n in {n for n, _, _ in BR["in"]} if sum(1 for m, _, _ in BR["in"] if m == n) > 1)
    if _dup or _dup2 or _dupn:
        sys.exit(f"씬 검사 실패 — Modbus 주소 겹침 {_dup} · 태그 Address 겹침 {_dup2} · 이름 겹침 {_dupn}")
    MB = ModbusClient("127.0.0.1", 502)
    MB.write_single_coil(tb[re.search(r'RunOutputKey="([0-9a-f-]{36})"', txt).group(1)][1], 1)
    BR["run"] = tb[re.search(r'RunOutputKey="([0-9a-f-]{36})"', txt).group(1)][1]
    BR["outnames"] = sorted({n for n, _, _ in BR["out"]})
    BR["di_n"] = max([a for _, ar, a in BR["in"] if ar == "di"] + [0]) + 1; BR["ir_n"] = max([a for _, ar, a in BR["in"] if ar == "ir"] + [0]) + 1
    def bridge():
        d = MB.read_discrete_inputs(0, BR["di_n"]); r = MB.read_input_registers(0, BR["ir_n"])
        ch = []
        for n, ar, a in BR["in"]:
            v = bool(d[a]) if ar == "di" else ((r[a] + 32768) % 65536) - 32768
            if BR["sent"].get(n) != v: ch.append((n, v))
        bad = L.write_many(ch)
        for n, v in ch:
            if n not in bad: BR["sent"][n] = v
        if bad: log(f"  중계 쓰기 실패 {len(bad)}개: {bad[:8]}")
        O = L.read_many(BR["outnames"]); co = {BR["run"]: True}; hr = {}
        for n, ar, a in BR["out"]:
            if ar == "coil": co[a] = bool(O.get(n))
            else: hr[a] = (O.get(n) or 0) & 0xFFFF
        lo, hi = min(co), max(co); MB.write_multiple_coils(lo, [co.get(i, False) for i in range(lo, hi + 1)])
        if hr: lo, hi = min(hr), max(hr); MB.write_multiple_registers(lo, [hr.get(i, 0) for i in range(lo, hi + 1)])
    bridge(); log(f"중계 시작: 입력 {len(BR['in'])} · 출력 {len(BR['out'])}")
    # 11-24: MX OPC 쓰기(SyncIO Write)는 한 번에 약 0.6초 걸려, 한 루프에서 하면 그동안 출력 갱신 · 바깥 처리도 멈춤
    # → 입력 쓰기 · 출력 읽기를 각자 스레드(각자 OPC 연결 · Modbus 연결)로 나눠 PLC → Factory I/O 쪽 지연을 0.02초 수준으로
    import threading
    BR["stop"] = False
    def _in_loop():
        Lw = Link(device=DEV, source=P.OPC_DS_CACHE); Mw = ModbusClient("127.0.0.1", 502)
        while not BR["stop"]:
            d = Mw.read_discrete_inputs(0, BR["di_n"]); r = Mw.read_input_registers(0, BR["ir_n"])
            if not d or r is None: time.sleep(0.02); continue
            ch = []; now_ = time.time()
            for n, ar, a in BR["in"]:
                v = bool(d[a]) if ar == "di" else ((r[a] + 32768) % 65536) - 32768
                if ar == "di":                                      # 11-26 짧은 신호 보존: 쓰는 동안 붙잡아 둔 변화를 먼저, 바뀐 값은 최소 HOLD초 유지
                    with ILK: v = BR["pend"].get(n, v)
                    if BR["sent"].get(n) is not None and BR["sent"][n] != v and now_ - BR["sent_t"].get(n, 0) < HOLD: continue
                v = OVR.get(n, v)                                   # 11-25 비상정지 · 정지 시험: 버튼 입력을 대신 넣음
                if BR["sent"].get(n) != v: ch.append((n, v))
            if not ch: time.sleep(0.01); continue
            bad = Lw.write_many(ch)
            for n, v in ch:
                if n not in bad:
                    BR["sent"][n] = v; BR["sent_t"][n] = time.time()
                    with ILK:
                        if BR["pend"].get(n) == v: BR["pend"].pop(n, None)
            if bad: log(f"  중계 쓰기 실패 {len(bad)}개: {bad[:8]}")
    def _out_loop():
        Lr = Link(device=DEV, source=P.OPC_DS_CACHE); Mr = ModbusClient("127.0.0.1", 502); last_co = {}; last_hr = {}
        while not BR["stop"]:
            O = Lr.read_many(BR["outnames"]); co = {BR["run"]: True}; hr = {}
            for n, ar, a in BR["out"]:
                if ar == "coil": co[a] = bool(O.get(n))
                else: hr[a] = (O.get(n) or 0) & 0xFFFF
            # 11-24: 바뀐 출력만 씀(같은 값을 초당 50번 다시 쓰면 Factory I/O 롤러가 떨려 팔레트가 메인 라인에서 돌아가는지 확인)
            with ILK:                                                # 인터록이 끊은 롤은 켜지 않음(11-25)
                BR["want"] = co
                cw = [(a, v and a not in BR["cut"]) for a, v in co.items() if last_co.get(a) != (v and a not in BR["cut"])]
                for a, v in cw:
                    if Mr.write_single_coil(a, v): last_co[a] = v          # 11-27 검토: 실패하면 기억하지 않음(다음 바퀴에 다시 씀)
            with ILK:
                hw = [(a, 0 if a in BR["zero"] else v) for a, v in hr.items() if last_hr.get(a) != (0 if a in BR["zero"] else v)]
                for a, v in hw:
                    if Mr.write_single_register(a, v): last_hr[a] = v
            time.sleep(0.02)
    # 11-25 턴테이블 현장 즉시정지: 진행 쪽 끝 센서가 켜지면 롤을 바로 끊음(fio_interlock.py). OPC를 거치지 않음
    import fio_interlock
    ILK = threading.Lock(); BR["cut"] = set(); BR["zero"] = set(); BR["want"] = {}; BR["pend"] = {}; BR["sent_t"] = {}
    HOLD = 2.0                                                       # 11-26: 입력 한 상태를 PLC에 최소 2초 보임(중계 한 바퀴 최대 약 1.4초)
    _xa = {n: a for n, ar, a in BR["in"] if ar == "di"}; _ya = {n: a for n, ar, a in BR["out"] if ar == "coil"}; _wa = {n: a for n, ar, a in BR["out"] if ar != "coil"}
    def _ilk_loop():
        Mi = ModbusClient("127.0.0.1", 502)
        while not BR["stop"]:
            d = Mi.read_discrete_inputs(0, BR["di_n"])
            if not d: time.sleep(0.02); continue
            with ILK:                                                # 11-26: 보낸 값과 달라진 첫 변화를 붙잡아 둠(입력 루프가 쓰는 0.6초 사이의 짧은 신호)
                for n, a in _xa.items():
                    if n not in BR["pend"] and BR["sent"].get(n) is not None and bool(d[a]) != BR["sent"][n]: BR["pend"][n] = bool(d[a])
            now = {_ya[y] for y in fio_interlock.cuts(lambda n: n in _xa and d[_xa[n]], lambda n: n in _ya and bool(BR["want"].get(_ya[n]))) if y in _ya}
            zr = {_wa[w] for w in fio_interlock.zero_words(lambda n: n not in _xa or d[_xa[n]]) if w in _wa}
            new, newz = now - BR["cut"], zr - BR["zero"]
            if now != BR["cut"] or zr != BR["zero"]:
                with ILK:
                    BR["cut"], BR["zero"] = now, zr
                    for a in newz: Mi.write_single_register(a, 0)
                    for a in new:
                        if BR["want"].get(a): Mi.write_single_coil(a, False)
            time.sleep(0.01)
    def _guard(f):                                                   # 11-27 검토: 중계 스레드가 예외로 조용히 죽지 않게 — 기록하고 1초 뒤 다시(새 연결)
        while not BR["stop"]:
            try: f()
            except BaseException as e:
                if BR["stop"]: break
                log(f"  ** 중계 스레드 {f.__name__} 오류 → 1초 뒤 다시: {type(e).__name__} {e}"); time.sleep(1)
    for f in (_in_loop, _out_loop, _ilk_loop): threading.Thread(target=_guard, args=(f,), daemon=True).start()
    log("중계 스레드 시작(입력 쓰기 · 출력 읽기 따로)")
_LL = [time.time()]; STALL = float(os.environ.get("STALL", "150"))   # 11-27 검토: 이 시간 동안 기록할 변화가 없으면 정체 의심을 남김
def log(m): _LL[0] = time.time(); print(f"{time.time()-T0:6.1f}s {m}", flush=True)
WATCH = ["M1950", "M1500", "D1640", "D1641", "D1656", "D1541", "D1750", "D1760", "D1525", "D1535", "D1558", "D1568", "D1900", "D1901", "D1902"] + [f"M{1951+i}" for i in range(8)]
WATCH += [w for w in os.environ.get("WATCHX", "").split(",") if w]   # 11-27: WATCHX="D1740,X1730" — 변화를 더 기록할 번지(MX OPC에 등록된 것만)
HS = ["M1510", "D1710", "D1711", "D1713", "D1740", "D1741", "D1743", "D1650", "D1651", "D1652", "D1653", "D1700", "D1730"]
RACK = [f"D{1660+k}" for k in range(24)] + [f"D{1810+k}" for k in range(24)]
ALL = WATCH + HS + RACK + [w for _, w, _ in ESTOP if w not in WATCH + HS + RACK]
PRESS = [(x.split("@")[0],) + tuple(x.split("@")[1].replace(":", "=").split("=")) for x in os.environ.get("PRESS", "").split("|") if x]   # 11-27: PRESS="M1963@D1902=1:5" — 그 워드가 값이 되고 5초 뒤 비트를 1로 한 번 씀(HMI 비트 셋 스위치 흉내, 래더가 끔)
_pr = {"n": 0, "t": None}
ALL += [w for _, w, _, _ in PRESS if w not in ALL]
KU = os.environ.get("KEEPUNTIL", "")                          # 11-27: KEEPUNTIL=Y1929 — 팩이 다 나와도 그 비트가 켜질 때까지 계속(배치 끝 1개 팔레트 배출 확인)
if KU: ALL.append(KU)
pack_ids = list(range(101, 101 + len(plan))); fed = 0; judged = set(); prev = {}

# 시작: X1501은 Factory I/O 씬 버튼이라 OPC로 써도 Factory I/O가 덮음 → 운전 비트 M1950을 직접 SET(래더 A02와 같은 결과)
for a in (("M1510", "D1900", "D1901", "D1902", "D1713", "D1743", "D1653") if plan else ()): L.write(a, 0)   # 이전 회차 값 지움(카운터는 처음 X 상태로 1씩 올라 있음)
L.write("M1950", 1); log("운전 시작(M1950 SET)")
time.sleep(2)
_st = L.read_many(["M1950", "X1500", "X1502"])                  # 11-27 검토: 정지 버튼(NC) X1502 · 비상정지 X1500이 0이면 래더가 M1950을 바로 지움 → 알리고 끝냄
if not _st.get("M1950"):
    log(f"** 운전 시작 실패: M1950={_st.get('M1950')} · 비상정지 X1500={_st.get('X1500')} · 정지 X1502={_st.get('X1502')} (Factory I/O 실행 · 버튼 상태 확인)")
    if BR: BR["stop"] = True
    sys.exit(2)
pend = {"C": False, "main": False, "re": False, "iso": False}   # OPC 캐시 지연으로 같은 요청에 두 번 답하지 않게
t_start = time.time()
while time.time() - T0 < LIMIT:
    t = time.time()
    V = L.read_many(ALL)
    for w in WATCH:
        if V.get(w) != prev.get(w):
            if w.startswith("M") and w != "M1950":
                if V.get(w): log(f"  알람 {w}")
            else:
                log(f"  {w} = {V.get(w)}")
            prev[w] = V.get(w)
    if ESTOP or _es["t"]:                                   # 비상정지 · 정지 시험
        if _es["t"] is None and _es["n"] < len(ESTOP):
            b, w, v = ESTOP[_es["n"]]
            if V.get(w) is not None and int(V[w]) == int(v): _es.update(t=t, b=b); OVR[b] = False; log(f"** {b} 누름 ({w}={v})")
        elif _es["t"]:
            d = t - _es["t"]
            if d >= 6: OVR.pop(_es["b"], None)
            if 8 <= d < 11: OVR["X1501"] = True
            if d >= 11: OVR.pop("X1501", None); _es["t"] = None; _es["n"] += 1; log(f"** 다시 시작 M1950={V.get('M1950')}")
    if _pr["n"] < len(PRESS):                               # HMI 버튼 흉내
        b, w, v, d = PRESS[_pr["n"]]
        if _pr["t"] is None and V.get(w) is not None and int(V[w]) == int(v): _pr["t"] = t
        if _pr["t"] is not None and t - _pr["t"] >= float(d): L.write(b, 1); log(f"** HMI {b} 누름 ({w}={v} 뒤 {d}s)"); _pr.update(n=_pr["n"] + 1, t=None)
    # C 인계
    if pend["C"] and V["M1510"]: pend["C"] = "seen"
    if pend["C"] == "seen" and not V["M1510"]: pend["C"] = False          # 래더가 M1510을 받아 내린 뒤에만 다음 인계
    if fed < len(plan) and not pend["C"] and ("--v2" in sys.argv or V["D1541"] == 0) and not V["M1510"] and time.time() - T0 > 3:
        pend["C"] = True; L.write_many([("D1516", pack_ids[fed]), ("D1518", 6 if plan[fed].endswith("L") else 4), ("D1542", 1480), ("M1510", 1)])   # 11-25: 한 번에 씀(한 건씩 쓰면 건당 0.6 s라 그동안 PLC 출력 갱신이 밀려 크레인 B가 내려놓기 전에 포크를 당김)
        log(f"C 인계: PACK {pack_ids[fed]} 판정 계획 {plan[fed]}"); fed += 1
    if SERVE:                                                 # serve가 응답 → 완료가 올라온 순간만 기록
        for st, req, res, done in (("메인 검사", "D1710", "D1700", "D1713"), ("재검사", "D1740", "D1730", "D1743"), ("격리 기록", "D1650", "D1651", "D1653")):
            if V[done] == 1 and not pend.get(st): pend[st] = True; log(f"{st} 응답(serve): {res} = {V[res]}" + (f" · PACK {V['D1711'] if st == '메인 검사' else V['D1741']}" if st != "격리 기록" else ""))
            if V[done] == 0: pend[st] = False
    else:
        # 메인 검사 핸드셰이크
        if V["D1710"] == 0: pend["main"] = False
        if V["D1710"] == 1 and (V["D1713"] or 0) == 0 and not pend["main"]:
            pend["main"] = True; pid = V["D1711"]; p = plan[pack_ids.index(pid)] if pid in pack_ids else "1"
            j = {"1": 1, "H": 1, "2": 2, "3": 3}[p.rstrip("L")]
            L.write_many([("D1700", j), ("D1701", 5), ("D1702", 60), ("D1703", 250), ("D1713", 1)])
            log(f"메인 검사 PACK {pid} → 판정 {j}")
        if V["D1710"] == 0 and V["D1713"] == 1: L.write("D1713", 0)
        # 재검사 핸드셰이크(GOOD)
        if V["D1740"] == 0: pend["re"] = False
        if V["D1740"] == 1 and (V["D1743"] or 0) == 0 and not pend["re"]:
            pend["re"] = True
            L.write_many([("D1730", 1), ("D1731", 5), ("D1732", 60), ("D1733", 250), ("D1743", 1)])
            log(f"재검사 PACK {V['D1741']} → GOOD")
        if V["D1740"] == 0 and V["D1743"] == 1: L.write("D1743", 0)
        # 격리 기록
        if V["D1650"] == 0: pend["iso"] = False
        if V["D1650"] == 1 and (V["D1653"] or 0) == 0 and not pend["iso"]: pend["iso"] = True; L.write("D1653", 1); log(f"격리 기록 PACK {V['D1651']} 온도 {V['D1652']}")
        if V["D1650"] == 0 and V["D1653"] == 1: L.write("D1653", 0)
    # 발열 접수(H) — 11-27 A2: --serve면 serve가 보관 온도를 정하고 접수함(run_real.sh가 계획의 H를 serve --hot-packs로 넘김)
    for k in (range(24) if not SERVE else ()):
        pid = V[f"D{1660+k}"]
        if pid in pack_ids and plan[pack_ids.index(pid)].rstrip("L") == "H" and (V[f"D{1810+k}"] or 0) > 0 and pid not in judged:
            judged.add(pid); L.write_many([("D1697", k + 1), ("D1698", 410), ("M1672", 1)]); log(f"발열 접수: 칸 {k+1} PACK {pid}")
    done = sum(V[d] or 0 for d in ("D1900", "D1901", "D1902"))
    if plan and done >= len(plan): prev["all_done"] = True          # 11-27: 회차 끝 뒤 다음 운전 시작에 serve가 카운터를 0으로 해도(A9) '다 나옴'은 유지
    if prev.get("all_done"): done = max(done, len(plan))
    if plan and done >= len(plan):
        if KU and not V.get(KU):
            if not prev.get("ku"): prev["ku"] = 1; log(f"모든 팩 배출 — {KU} 켜질 때까지 계속")
        elif HOLDRUN:
            if not prev.get("hold"): prev["hold"] = 1; log("모든 팩 배출 — --hold: 제한 시간까지 중계 유지(HMI 수거 · 시연용)")
        else: log((f"{KU} 켜짐 · " if KU else "") + "모든 팩 배출"); break
    if plan and done < len(plan) and time.time() - _LL[0] > STALL:   # 팩이 다 나온 뒤(배치 끝 대기 · --hold)는 경고하지 않음
        _sb = {k: V.get(k) for k in ("M1950", "M1500", "D1541", "D1640", "D1641", "D1750", "D1760", "D1900", "D1901", "D1902") if k in V}
        log(f"** 정체 의심: {STALL:.0f}초 동안 기록할 변화 없음 · {_sb} (Factory I/O 화면 · 스텝 확인)")
    prev["주기"] = max(prev.get("주기", 0), time.time() - t)
    time.sleep(0.05)
if BR:
    BR["stop"] = True; time.sleep(0.3)
    # 11-27 검토: 끝날 때 출력을 켠 채로 두지 않음 — 코일 · 아날로그 출력을 0으로. Run 코일은 켜 둠
    # (Run을 끄면 Factory I/O가 편집 모드로 돌아가 씬이 처음 상태로 초기화됨 → 남은 팔레트 · 격리 팩이 사라지고 회차 끝(A9)을 못 봄, 11-27 v9c)
    try:
        _ca = [a for _, ar, a in BR["out"] if ar == "coil"] + [BR["run"]]
        MB.write_multiple_coils(0, [i == BR["run"] for i in range(max(_ca) + 1)])
        _ra = [a for _, ar, a in BR["out"] if ar != "coil"]
        if _ra: MB.write_multiple_registers(0, [0] * (max(_ra) + 1))
    except Exception: pass
print(f"결과: GOOD {V['D1900']} · NG {V['D1901']} · 격리 {V['D1902']} / 계획 {plan} · 가장 긴 주기 {prev['주기']:.2f}s", flush=True)
