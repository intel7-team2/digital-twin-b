"""실제 PLC 시험 중 화면 · 신호 기록(11-24). 한 프로세스에서 같이 돌리면 서로 막혀(화면 1장에서 멈춤) 둘로 나눠 띄움.
  py -3.12 opc_shots.py img <폴더> <제한 초> [간격 초=1]   Factory IO 창(PrintWindow, 가려져도 됨)을 간격마다 저장
  py -3.12 opc_shots.py sig <폴더> <제한 초>               0.1초마다 OPC로 크레인 · 출고 신호를 읽어 바뀔 때만 signals.csv"""
import sys, os, time, ctypes, re, io, csv, textwrap
MODE, OUT, LIMIT = sys.argv[1], sys.argv[2], float(sys.argv[3]); EVERY = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
os.makedirs(OUT, exist_ok=True)
HERE = os.path.dirname(os.path.abspath(__file__))
T0 = time.time()
if MODE == "img":
    from ctypes import wintypes
    ctypes.windll.user32.SetProcessDPIAware()
    src = io.open(os.path.join(HERE, "softplc.py"), encoding="utf-8").read()
    m = re.search(r"    from PIL import Image\n    def grab_fio\(box\):.*?return im\n", src, re.S).group(0)
    ns = {}; exec("import ctypes\nfrom PIL import ImageGrab\n" + textwrap.dedent(m), ns)
    n = 0
    while time.time() - T0 < LIMIT:
        t = time.time()
        try:
            h = ctypes.windll.user32.FindWindowW(None, "Factory IO"); r = wintypes.RECT(); ctypes.windll.user32.GetWindowRect(h, ctypes.byref(r))
            im = ns["grab_fio"]((r.left, r.top, r.right, r.bottom)); im = im.resize((2400, int(im.height * 2400 / im.width)))
            im.save(os.path.join(OUT, f"{n:04d}_{t-T0:06.1f}s.jpg"), quality=70); n += 1
        except Exception as e:
            print("화면 저장 오류:", e, flush=True)
        time.sleep(max(0.05, EVERY - (time.time() - t)))
    print(f"화면 {n}장", flush=True)
else:
    keep = (LIMIT, T0)
    sys.argv = [sys.argv[0], "1", "1"]
    exec(open(os.path.join(HERE, "opc_outside.py"), encoding="utf-8").read().split("L = Link(")[0])
    LIMIT, T0 = keep                                   # 공용 코드가 LIMIT · T0을 덮어씀(11-24: 시작하자마자 끝났던 원인)
    L = Link(device="CSIM", source=P.OPC_DS_CACHE)
    SIG = ["D1641", "D1602", "X1608", "X1609", "X160A", "X160B", "X160C", "Y1608", "Y1609", "Y160A", "Y1610", "X1610", "M1670", "D1655",
           "D1640", "D1601", "X1600", "X1601", "X1602", "X1603", "X1604", "Y1600", "Y1601", "Y1602", "D1656", "D1750", "D1541"]
    f = open(os.path.join(OUT, "signals.csv"), "w", encoding="utf-8-sig", newline=""); w = csv.writer(f); w.writerow(["초"] + SIG)
    prev = None; n = 0
    while time.time() - T0 < LIMIT:
        V = L.read_many(SIG); row = [V[k] for k in SIG]
        if row != prev: w.writerow([f"{time.time()-T0:.2f}"] + row); f.flush(); prev = row; n += 1
        time.sleep(0.1)
    f.close(); print(f"신호 {n}줄", flush=True)
