"""V7(11-25): 1층 검사 라인 바로 위에 2층 분류 라인을 겹친 ㄷ자 배치. 참고 A_3D_full2.
1층: 입고 · 크레인(V6_plc_19_base 그대로) → TT1 → TTM → 메인 검사 → TT2(GOOD 직진 / 그 외 재검사 고리 → TT3) → TT5 → E1 엘리베이터. 1층 리무버 없음(발열 격리 = 보관 레일).
2층: E1(들어온 쪽으로 되돌려 나감) → 픽앤플레이스(박스만 박스 벨트로) → 빈 팔레트는 직진 배출. NG 박스는 픽앤플레이스가 NG 벨트(박스 벨트 옆)에 바로 놓고, GOOD은 박스 벨트 → 팔레타이저(2개 = 한 팔레트).
사용: py -3.12 build_v7_2f.py <V6_plc_19_base> <출력>   (참고 씬 부품 견본: 2F_templates.json)"""
import sys, re, io, os, json, uuid
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H)
from fio_lib import place, scene, F, _idx, rot_xml
src, out = sys.argv[1:3]; t = F.load(src)
TPL = json.load(io.open(os.path.join(H, "2F_templates.json"), encoding="utf-8"))
code = io.open(os.path.join(H, "build_v6_plc.py"), encoding="utf-8").read()
exec(code[:code.index("# ---- 크레인 구간")].replace("out = sys.argv[1]; ", "").replace(code[code.index("sys.path.insert"):code.index("\n", code.index("sys.path.insert"))], ""))
PANEL = ("ElectricSwitchboard", "EmergencyStopButton", "StartPushButton", "StopPushButton", "ResetPushButton")
for o in F.OBJ_RE.findall(t):
    x, z = (int(v) for v in re.search(r'<Position X="([^"]+)" Y="[^"]+" Z="([^"]+)"', o).groups()); pn = re.search(r'PrefabName="([^"]+)"', o).group(1)
    if pn in PANEL: O.append(o.replace(f'Z="{z}"', f'Z="{z-8}"', 1))
    elif x > 230: O.append(o)
_idx[0] = max(int(v) for v in re.findall(r'ComponentIO Index="(\d+)"', t)) + 1
def put(key, x, y, z, yaw, names=None):
    o = TPL[key]
    o = re.sub(r'Key="[0-9a-f-]{36}"', lambda m: f'Key="{uuid.uuid4()}"', o); o = re.sub(r'GroupKey="[0-9a-f-]{36}"', f'GroupKey="{F.ZERO}"', o)
    o = re.sub(r'<Position [^>]*/>', f'<Position X="{x}" Y="{y}" Z="{z}" />', o, 1)
    if yaw:
        r, fw, rt_ = rot_xml(yaw); o = re.sub(r'<Rotation [^>]*/>', r, o, 1); o = re.sub(r'<Forward [^>]*/>', fw, o, 1); o = re.sub(r'<Right [^>]*/>', rt_, o, 1)
    _idx[0] += 1; o = re.sub(r'ComponentIO Index="\d+"', f'ComponentIO Index="{_idx[0]}"', o).replace('UseForcedValue="True"', 'UseForcedValue="False"')
    for a, b in (names or {}).items(): o = re.sub(rf'(?<=\s)Name="{re.escape(a)}"', f'Name="{b}"', o)
    O.append(o)
def rollY(L, x, y, z, yaw, name): O.append(place(f"RollerConveyor{L}M", x, y, z, yaw, names={"Entry conveyor": name, "Conveyor": name, "Box conveyor": name}))
def belt(L, x, y, z, yaw, name): O.append(re.sub(r'(<BinaryOutput Name=")[^"]*', rf'\g<1>{name}', place(f"BeltConveyor{L}M", x, y, z, yaw)))
def diff(x, y, z, yaw, name, rng="0.6"):
    O.append(place("DiffusePhotoelectricSensor", x, y, z, yaw, extra=lambda o: re.sub(r'<Sensor Range="[^"]*"', f'<Sensor Range="{rng}"', re.sub(r'<Rotation [^>]*/>', rot_xml(yaw)[0], re.sub(r"<FineRotation>[^<]*<", "<FineRotation>0<", re.sub(r'(<BinaryInput Name=")[^"]*', rf'\g<1>{name}', o)), count=1)).replace("<FinePosition>0<", "<FinePosition>-0.0625<")))
def beamX(y, z, x0, x1, n):
    O.append(place("RetroreflectivePhotoelectricSensor", x0, y, z, "N", names={"Sensor": n}, extra=FPR)); O.append(place("RetroreflectiveMirror", x1, y, z, "N", extra=FP))
def beamZ(x, y, z0, z1, n):
    O.append(place("RetroreflectivePhotoelectricSensor", x, y, z0, "E", names={"Sensor": n}, extra=FPR)); O.append(place("RetroreflectiveMirror", x, y, z1, "E", extra=FP))
def removerY(x, y, z):
    _rm[0] += 1; O.append(place("Remover", x, y, z, "S", names={"Remover": f"Remover {_rm[0]}"}, extra=lambda o: o.replace('UseForcedValue="False" ForcedValue="True"', 'UseForcedValue="True" ForcedValue="True"')))
def tt(x, z, n, name):
    d = ("Load", "Unload", "Turn", "At load position", "At unload position", "At front", "At back")
    O.append(place("Turntable", x, 2, z, "W", names={k: (v or f"{name} {k}") for k, v in zip(d, n)}))
# ===== 1층 =====
tt(219, 184, ("Y1662", "Y1663", "Y1664", "X1664", "X1668", "X1662", "X1663"), "TT1"); retro(228, 184, "X", "X1660")
roller(2, 219, 200, "S", "Y1690"); retro(219, 201, "Z", "X1902")           # 격리 보관 레일(끝 스토퍼 항상 올림). 11-26: 겹친 롤러(z204) 삭제, 스토퍼 z206(롤러 가운데 +6 = 롤러 사이 · 홀수 칸 z205 · z207은 롤러와 겹쳐 떨고 팔레트가 넘어감, 격리 레일 단독 시험으로 확인) · 빔 z201(선 팔레트 가운데)
O.append(place("RollerStop", 219, 3, int(os.environ.get("ISOZ", 206)), "S", names={"Load stop": "ISO stop"}, extra=lambda o: o.replace('UseForcedValue="False" ForcedValue="False"', 'UseForcedValue="True" ForcedValue="True"', 1)))
roller(2, 219, 168, "N", "Y1700"); retro(219, 162, "Z", "X1666")
tt(219, 153, ("Y1665", None, "Y1666", "X1667", "X1669", "X1665", None), "TTM")
roller(4, 195, 153, "W", "Y1700")
rstop(183, 153, "W", "Y1701", 3); retro(187, 153, "X", "X1700"); rfid(186, 157, "N", 1520)
roller(2, 171, 153, "W", "Y1702"); retro(165, 153, "X", "X1720")
tt(156, 153, ("Y1722", None, "Y1724", "X1725", "X1726", "X1723", None), "TT2")
roller(2, 140, 153, "W", "Y1703"); roller(2, 138, 153, "W", "Y1703")   # 11-26: X1903 빔 삭제(래더 안 씀)
tt(122, 153, ("Y1904", "Y1906", "Y1905", "X1907", "X1908", "X1904", "X1905"), "TT5")
# 재검사 고리
roller(2, 156, 137, "N", "Y1800"); retro(156, 133, "Z", "X1800"); curve(152, 122, "S", "Y1800"); roller(2, 137, 118, "W", "Y1800")
rstop(133, 118, "W", "Y1730", 3); retro(137, 118, "X", "X1730"); rfid(136, 122, "N", 1530); retro(131, 118, "X", "X1731")
tt(122, 118, (None, "Y1734", "Y1735", "X1735", "X1737", "X1733", "X1734"), "TT3")
O[-1] = O[-1].replace('Name="TT3 Load"', 'Name="Y1733"')
roller(2, 122, 134, "S", "Y1736"); roller(2, 122, 137, "S", "Y1736"); diff(127, 5, 139, "N", "X1736")
# 엘리베이터
roller(2, 106, 153, "W", "Y1910"); rstop(100, 153, "W", "Y1911", 3); diff(103, 5, 158, "E", "X1910")
put("E1 Roll+", 93, 33, 152, "W", {"E1 Roll+": "Y1912", "E1 Roll-": "Y1913", "E1 Up": "Y1914", "E1 Down": "Y1915", "E1 In": "X1911"})   # 11-26: E1 Out(X1912) 연결 안 함(래더 안 씀)
for n, y, d in (("E2 Low1", 3, "X1913"), ("E2 High2", 30, "X1916")): put(n, 89, y, 146, None, {n: d})   # 11-26: 중간 높이 X1914 · X1915 삭제(래더 안 씀)
# ===== 2층 =====
rollY(2, 107, 27, 153, "E", "Y1916"); rollY(2, 122, 27, 153, "E", "Y1917"); rstop(128, 153, "E", "Y1918", 28); diff(125, 30, 158, "E", "X1917")
rollY(2, 138, 27, 153, "E", "Y1919"); rollY(2, 154, 27, 153, "E", "Y1919"); removerY(161, 31, 153)
put("G SPX", 127, 36, 150, "E", {"G SPX": "D1910", "G SPY": "D1911", "G SPZ": "D1912", "G X": "D1913", "G Y": "D1914", "G Z": "D1915", "G Grab": "Y191A", "G Detected": "X1918"})
belt(2, 124, 28, 140, "N", "Y191B"); belt(2, 124, 28, 124, "N", "Y191C"); belt(2, 124, 28, 108, "N", "Y191C")
belt(2, 131, 28, 140, "N", "Y191D"); belt(2, 131, 28, 124, "N", "Y191D"); removerY(132, 34, 120)   # 11-26: X1901 삭제 — 실제 PLC 경로에서 0.7초 신호가 빠짐, NG 수는 래더가 놓을 때 셈(U03)
# 11-26: 푸셔 행정이 모자라 NG는 픽앤플레이스가 NG 벨트(+x 쪽, Y=957 · GOOD Y=314 · 집기 Y=336, 11-26 실측)에 바로 놓음. X1901은 바깥쪽 확산 센서(거리 0.6 m라 박스 벨트는 안 봄), 리무버는 사용자가 맞춘 자리(132, 34, 120), X1901은 그 앞 z127(리무버 범위 z116~124보다 먼저 봄). 픽앤플레이스 x127 = 두 벨트 가운데(사용자 조정) — 박스 벨트 위 GOOD이 걸리거나 지워지지 않게
beamX(33, 102, 129, 119, "X1900")
put("P Turn", 129, 22, 92, "N", {"P Belt+": "Y1920", "P Push": "Y1921", "P Clamp": "Y1922", "P Open": "Y1923", "P Up": "Y1924", "P Down": "Y1925", "P Limit": "Y1926", "P Chain+": "Y1927", "P Front": "X1921", "P Moving": "X1922", "P Pusher": "X1923"})   # 11-26: P Clamped(X1924) 연결 해제 — 상자 2개 한 줄에서는 안 켜짐, 클램프 1초 후 진행
rollY(2, 132, 14, 106, "N", "Y1928"); rollY(2, 132, 14, 79, "N", "Y1929"); beamX(17, 87, 136, 128, "X1925")
put("P Emit", 132, 18, 110, "N", {"P Emit": "Y192A", "P Base": "D1916"}); removerY(132, 18, 75)
# 11-26: 2층만 시험하는 씬(TEST2F=1) — E1 2층 출구 롤러 위에 팔레트+상자 Emitter(Y19F0 · Part D1985 · Base D1986). 운전 씬에는 없음
if os.environ.get("TESTISO"): put("P Emit", 219, 6, 195, "S", {"P Emit": "Y19F0", "P Base": "D1986", "P Part": "D1985"})   # 11-26 격리 레일만 시험
if os.environ.get("TEST2F"): put("P Emit", 107, 31, 153, "E", {"P Emit": "Y19F0", "P Base": "D1986", "P Part": "D1985"})
# 2층 받침(장식)
for x in (113, 137, 161): O.append(place("PlatformL", x, 23, 153, "S"))
for x in (112, 135, 168):
    for z in (145, 161):
        for y in (5, 16): O.append(place("PlatformPillar", x, y, z, "S"))
added = scene(O, out, "Project B v7 line (1F inspect + 2F sort, elevator)", camera=((22.0, 24.0, 36.0), (21.0, 1.0, 19.0)))
print("부품", len(O), "· 연결", len(added))
