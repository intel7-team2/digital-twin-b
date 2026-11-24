"""실제 PLC(GX Simulator2) + MX OPC + Factory I/O(OPC 씬) 6팩 시험용 — 바깥(C 인계 · 검사 엔진 · 발열 접수)을 OPC로 대신함(11-24).
softplc.py의 outside()와 같은 동작. 래더는 GX Simulator2가 돌리고, 이 스크립트는 바깥 신호만 읽고 씀.
사용: py -3.12 opc_outside.py <계획 예: 1,2L,3,H,1L,2> <제한 초> [--device CSIM] [--bridge <Modbus 씬>]
준비: GX Works2 시뮬레이션 RUN · MX OPC 프로젝트 MXOPC_B_v6_d24b.mdb(태그 359).
  --bridge 없이: Factory I/O에 V6_plc_17_opc(OPC Client 씬)를 열고 실행.
  --bridge 씬:  Factory I/O에 Modbus 씬(V6_plc_17)을 열고, 이 스크립트가 Factory I/O(Modbus) ↔ PLC(MX OPC)를 중계.
     11-24: Factory I/O OPC Client가 센서(입력) 쓰기에서 MX OPC '지정되지 않은 오류'를 받아(출력은 정상) 이 방식으로 시험."""
import sys, os, time, ctypes
sys.path.insert(0, r"D:\seojung\digital-twin-b")
import plc_link as P

plan = sys.argv[1].split(","); LIMIT = float(sys.argv[2])
DEV = sys.argv[sys.argv.index("--device") + 1] if "--device" in sys.argv else "CSIM"


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
def log(m): print(f"{time.time()-T0:6.1f}s {m}", flush=True)
WATCH = ["M1950", "D1541", "D1750", "D1760", "D1525", "D1535", "D1558", "D1568", "D1900", "D1901", "D1902"] + [f"M{1951+i}" for i in range(7)]
HS = ["M1510", "D1710", "D1711", "D1713", "D1740", "D1741", "D1743", "D1650", "D1651", "D1652", "D1653"]
RACK = [f"D{1660+k}" for k in range(24)] + [f"D{1810+k}" for k in range(24)]
ALL = WATCH + HS + RACK
pack_ids = list(range(101, 101 + len(plan))); fed = 0; judged = set(); prev = {}

# 시작: X1501은 Factory I/O 씬 버튼이라 OPC로 써도 Factory I/O가 덮음 → 운전 비트 M1950을 직접 SET(래더 A02와 같은 결과)
for a in ("M1510", "D1900", "D1901", "D1902", "D1713", "D1743", "D1653"): L.write(a, 0)   # 이전 회차 값 지움(카운터는 처음 X 상태로 1씩 올라 있음)
L.write("M1950", 1); log("운전 시작(M1950 SET)")
pend = {"C": False, "main": False, "re": False, "iso": False}   # OPC 캐시 지연으로 같은 요청에 두 번 답하지 않게
t_start = time.time()
while time.time() - T0 < LIMIT:
    t = time.time()
    if BR: bridge()
    V = L.read_many(ALL)
    for w in WATCH:
        if V.get(w) != prev.get(w):
            if w.startswith("M") and w != "M1950":
                if V.get(w): log(f"  알람 {w}")
            else:
                log(f"  {w} = {V.get(w)}")
            prev[w] = V.get(w)
    # C 인계
    if pend["C"] and V["M1510"]: pend["C"] = "seen"
    if pend["C"] == "seen" and not V["M1510"]: pend["C"] = False          # 래더가 M1510을 받아 내린 뒤에만 다음 인계
    if fed < len(plan) and not pend["C"] and V["D1541"] == 0 and not V["M1510"] and time.time() - T0 > 3:
        pend["C"] = True; L.write("D1516", pack_ids[fed]); L.write("D1518", 6 if plan[fed].endswith("L") else 4); L.write("D1542", 1480); L.write("M1510", 1)
        log(f"C 인계: PACK {pack_ids[fed]} 판정 계획 {plan[fed]}"); fed += 1
    # 메인 검사 핸드셰이크
    if V["D1710"] == 0: pend["main"] = False
    if V["D1710"] == 1 and (V["D1713"] or 0) == 0 and not pend["main"]:
        pend["main"] = True; pid = V["D1711"]; p = plan[pack_ids.index(pid)] if pid in pack_ids else "1"
        j = {"1": 1, "H": 1, "2": 2, "3": 3}[p.rstrip("L")]
        for a, v in (("D1700", j), ("D1701", 5), ("D1702", 60), ("D1703", 250), ("D1713", 1)): L.write(a, v)
        log(f"메인 검사 PACK {pid} → 판정 {j}")
    if V["D1710"] == 0 and V["D1713"] == 1: L.write("D1713", 0)
    # 재검사 핸드셰이크(GOOD)
    if V["D1740"] == 0: pend["re"] = False
    if V["D1740"] == 1 and (V["D1743"] or 0) == 0 and not pend["re"]:
        pend["re"] = True
        for a, v in (("D1730", 1), ("D1731", 5), ("D1732", 60), ("D1733", 250), ("D1743", 1)): L.write(a, v)
        log(f"재검사 PACK {V['D1741']} → GOOD")
    if V["D1740"] == 0 and V["D1743"] == 1: L.write("D1743", 0)
    # 격리 기록
    if V["D1650"] == 0: pend["iso"] = False
    if V["D1650"] == 1 and (V["D1653"] or 0) == 0 and not pend["iso"]: pend["iso"] = True; L.write("D1653", 1); log(f"격리 기록 PACK {V['D1651']} 온도 {V['D1652']}")
    if V["D1650"] == 0 and V["D1653"] == 1: L.write("D1653", 0)
    # 발열 접수(H)
    for k in range(24):
        pid = V[f"D{1660+k}"]
        if pid in pack_ids and plan[pack_ids.index(pid)].rstrip("L") == "H" and (V[f"D{1810+k}"] or 0) > 0 and pid not in judged:
            judged.add(pid); L.write("D1697", k + 1); L.write("D1698", 410); L.write("M1672", 1); log(f"발열 접수: 칸 {k+1} PACK {pid}")
    done = sum(V[d] or 0 for d in ("D1900", "D1901", "D1902"))
    if done >= len(plan): log("모든 팩 배출"); break
    prev["주기"] = max(prev.get("주기", 0), time.time() - t)
if BR:
    try: MB.write_multiple_coils(min(a for _, ar, a in BR["out"] if ar == "coil"), [False] * 1)
    except Exception: pass
print(f"결과: GOOD {V['D1900']} · NG {V['D1901']} · 격리 {V['D1902']} / 계획 {plan} · 가장 긴 주기 {prev['주기']:.2f}s", flush=True)
