"""실제 PLC 경로 시험 · 시연 전 점검(11-27). 읽기만 함 — 설정 · 파일 · 값을 바꾸지 않음.

11-24 ~ 11-27에 실제로 터진 문제를 시작 전에 잡으려고 만듦:
  MX OPC 실행 프로젝트가 예상과 다름 · 씬 태그 Address / Modbus 주소 겹침(크레인 B 포크 정지) · 래더 · 중계 · HMI가 쓰는 번지가
  MX OPC에 없음 · serve 중복 / 없음 · HMI 중계 서버 없음 · WinGP 체험판 3시간 · GX Simulator2 정지 · Factory I/O 응답 없음

사용: py -3.12 real_preflight.py [--scene V7_plc_2.factoryio] [--mdb MXOPC_B_v7f.mdb] [--serve 1] [--hmi]
  끝 코드: 0 = 통과, 1 = 막는 문제 있음(NG). 주의(WARN)는 통과로 셈
"""
import argparse, csv, io, os, re, socket, struct, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "computer_use"))
import fio_scene as F
import mxopc_db as M

ap = argparse.ArgumentParser()
ap.add_argument("--scene", default="V7_plc_2.factoryio")
ap.add_argument("--mdb", default="MXOPC_B_v7f.mdb", help="MX OPC가 실행 중이어야 하는 프로젝트 파일 이름")
ap.add_argument("--serve", type=int, default=1, help="떠 있어야 하는 measurement_engine serve 수(0이면 검사 안 함)")
ap.add_argument("--hmi", action="store_true", help="HMI(WinGP · 중계 서버)도 검사")
ap.add_argument("--no-opc", action="store_true", help="MX OPC 값 읽기 검사를 건너뜀")
args = ap.parse_args()

res = []
def put(level, name, detail=""):
    res.append(level); print(f"[{level:4}] {name}" + (f" — {detail}" if detail else ""), flush=True)

def procs(pattern):
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          "Get-CimInstance Win32_Process | % { \"$($_.ProcessId)`t$($_.Name)`t$($_.CreationDate)`t$($_.CommandLine)\" }"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    rows = [l.split("\t", 3) for l in out.splitlines() if l.count("\t") >= 3]
    return [r for r in rows if re.search(pattern, r[3] or r[1], re.I)]

# 1. MX OPC 실행 프로젝트
mdb_now = M.runtime_mdb() or ""
if os.path.basename(mdb_now).lower() == args.mdb.lower():
    put("OK", "MX OPC 실행 프로젝트", mdb_now)
else:
    put("NG", "MX OPC 실행 프로젝트가 다름", f"지금 {mdb_now or '없음'} · 필요 {args.mdb} (D:\\seojung\\MXOPC_{args.mdb.split('_')[-1].split('.')[0]}.bat를 관리자로 실행)")

# 2. MX OPC에 필요한 태그
names = set()
if os.path.exists(mdb_now):
    out = M.run_vbs('Set rs = cn.Execute("SELECT Name FROM MX_DataTagsRoot WHERE ParentID=1")\r\nDo While Not rs.EOF\r\n  WScript.Echo rs("Name")\r\n  rs.MoveNext\r\nLoop\r\n', mdb_now)
    names = set(out.split())
scene_path = os.path.join(ROOT, "factoryio_test", args.scene)
txt = F.load(scene_path)
tb = F.modbus_address_table(txt)
bridge = [t["name"] for t in F.tags(txt) if t["key"] in tb and re.match(r"^([XY][0-9A-F]{4}|[DM]\d{4})$", t["name"])]
need = {"씬 중계 번지": set(bridge)}
need["serve · 중계 핸드셰이크"] = {f"D{n}" for n in list(range(1700, 1704)) + [1710, 1711, 1713, 1714] + list(range(1730, 1734)) + [1740, 1741, 1743, 1744]
                             + list(range(1650, 1654)) + [1516, 1517, 1518, 1524, 1534, 1558, 1568, 1900, 1901, 1902]} | {"M1510", "M1950", "M1952", "M1953", "M1954"}
need["초기화(opc_reset)"] = {l.strip() for l in open(os.path.join(HERE, "opc_reset_names.txt"), encoding="utf-8") if l.strip() and not l.startswith("#")} | {"M1961", "M1964"}
hmi = set()
for r in csv.DictReader(io.open(os.path.join(ROOT, "hmi", "hmi_parts_v2.csv"), encoding="utf-8-sig")):
    hmi.update(m for m in re.findall(r"\b([XYMD]\d{4}|[XY]1[0-9A-F]{3})\b", r["번지"]) if not m.startswith("LS"))
need["HMI 화면 번지"] = hmi
for k, v in need.items():
    miss = sorted(v - names)
    if not names:
        put("NG", f"MX OPC 태그 — {k}", "실행 프로젝트 파일을 못 읽음")
    elif miss:
        put("NG" if k != "HMI 화면 번지" else "WARN", f"MX OPC에 없는 번지 — {k} {len(miss)}개", ", ".join(miss[:20]) + (" …" if len(miss) > 20 else ""))
    else:
        put("OK", f"MX OPC 태그 — {k} {len(v)}개 모두 있음")

# 3. 씬 겹침(11-27 리무버 Address 3 = 크레인 B 포크 Y1608)
pts = []
for t in F.tags(txt):
    if t["key"] in tb: pts.append((tb[t["key"]][0], tb[t["key"]][1], t["name"]))
dup_mb = sorted({(a, n) for a, n, _ in pts if sum(1 for b, m, _ in pts if (b, m) == (a, n)) > 1})
tagaddr = {}
for m in re.finditer(r'<(\w+(?:Input|Output)) Name="([^"]*)" Address="(-?\d+)"', txt):
    tagaddr.setdefault((m.group(1), m.group(3)), []).append(m.group(2))
dup_tag = {f"{k[0]} {k[1]}": v for k, v in tagaddr.items() if len(v) > 1 and k[1] != "-1"}
run = re.search(r'RunOutputKey="([0-9a-f-]{36})"', txt)
if dup_mb or dup_tag: put("NG", "씬 주소 겹침", f"Modbus {dup_mb} · 태그 Address {dup_tag}")
else: put("OK", f"씬 {args.scene}", f"태그 겹침 없음 · 중계 번지 {len(bridge)}개 · Run 코일 {'있음' if run and run.group(1) in tb else '없음!'}")

# 4. Factory I/O · GX Simulator2
try:
    s = socket.create_connection(("127.0.0.1", 502), 1); s.settimeout(1); s.sendall(struct.pack(">HHHBBHH", 1, 0, 6, 1, 2, 0, 1)); ok = len(s.recv(20)) >= 9; s.close()
    put("OK" if ok else "NG", "Factory I/O Modbus 502 응답")
except OSError:
    put("WARN", "Factory I/O Modbus 502 응답 없음", "씬을 아직 안 열었으면 정상(run_real.sh가 엶)")
put("OK" if procs(r"QnUDSimRun2") else "NG", "GX Simulator2 실행(QnUDSimRun2)")
if not args.no_opc and names:
    try:
        sys.argv = [sys.argv[0], "1", "1"]
        src = open(os.path.join(HERE, "opc_outside.py"), encoding="utf-8").read()
        g = {"__file__": os.path.join(HERE, "opc_outside.py")}; exec(src.split("OVR = {}")[0], g)
        L = g["Link"](device="CSIM", source=g["P"].OPC_DS_CACHE)
        a = None
        for _ in range(10):
            a = L.read_many(["SM400", "D1540", "M1950", "X1500", "X1502"]) if "SM400" in names else L.read_many(["D1540", "M1950", "X1500", "X1502"])
            if a.get("D1540") is not None: break
            time.sleep(1)
        if a.get("D1540") is None: put("NG", "MX OPC 값 읽기", f"품질 불량 {a} (GX RUN · MX OPC 프로젝트 확인)")
        else: put("OK", "MX OPC 값 읽기", f"{a}")
        if a.get("X1500") == 0 or a.get("X1502") == 0:
            put("WARN", "비상정지 X1500 · 정지 X1502(NC)가 0", "Factory I/O가 실행 중이 아니면 정상. 실행 중인데 0이면 운전이 안 걸림")
    except BaseException as e:
        put("NG", "MX OPC 연결", str(e))

# 5. 프로세스
sv = [r for r in procs(r"measurement_engine\.py\s+serve") if r[1].lower() == "python.exe"]
if args.serve:
    if len(sv) == args.serve: put("OK", f"serve {len(sv)}개", sv[0][3].split("--db")[-1].strip() if sv else "")
    else: put("NG", f"serve {len(sv)}개(필요 {args.serve})", "2개 이상이면 같은 요청에 둘 다 답함, 0개면 검사기에서 멈춤")
br = [r for r in procs(r"opc_outside\.py") if r[1].lower() == "python.exe"]
if br: put("WARN", f"중계(opc_outside) {len(br)}개 이미 실행 중", "이전 회차가 남았으면 끄고 시작")
if args.hmi:
    rl = [r for r in procs(r"hmi_mc_relay\.py") if r[1].lower() == "python.exe"]
    put("OK" if len(rl) == 1 else "NG", f"HMI 중계 서버 {len(rl)}개", "" if len(rl) == 1 else "1개만 띄울 것(같은 포트를 둘 다 열면 예전 중계가 남음)")
    st = subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-Process PCRuntime -ErrorAction SilentlyContinue | Select-Object -First 1).StartTime.ToString('yyyyMMddHHmmss')"],
                        capture_output=True, text=True).stdout.strip()
    if not re.match(r"\d{14}$", st): put("NG", "WinGP 실행 안 됨")
    else:
        if True:
            age = (time.time() - time.mktime(time.strptime(st, "%Y%m%d%H%M%S"))) / 3600
            put("WARN" if age > 2.5 else "OK", f"WinGP 실행 {age:.1f}시간째", "체험판 3시간 — 2.5시간이 넘었으면 시연 전에 다시 실행" if age > 2.5 else "")

ng = res.count("NG")
print(f"\n점검 결과: NG {ng} · WARN {res.count('WARN')} · OK {res.count('OK')}", flush=True)
sys.exit(1 if ng else 0)
