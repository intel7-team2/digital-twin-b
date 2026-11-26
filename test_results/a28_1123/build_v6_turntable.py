"""V6_plc_19_base의 입고 · 크레인 구간은 그대로 두고, CT1부터 뒤를 턴테이블 5대 + 곡선 레일로 다시 짬(11-25).
턴테이블(16×16칸, 방향 W): 0° = X축, 롤(+) = −X로 / 90° = Z축, 롤(+) = −Z로. 0 → 90은 왼쪽(−X → −Z)으로 돎. 앞 센서(Fr) = 롤(+) 쪽 끝, 뒤 센서(Bk) = 들어오는 쪽.
  TT1  1차 분리: 0°로 받음 → 90° → 롤(+) 메인(−Z) / 롤(−) 격리(+Z)
  TTM  메인 코너: 90°로 받음(−Z로 들어옴) → 0° → 롤(+) −X. 박스 태그가 계속 진행 방향 오른쪽(+Z)이라 리더 ②는 자리 그대로
  TT2  분기: 0°로 받음 → 90° → 롤(−) GOOD(+Z) / 롤(+) 재검사(−Z)
  TT3  2차 분리: 0°로 받음 → 90° → 롤(−) GOOD(+Z) / 롤(+) NG(−Z)
  TT5  합류: 0° 롤(+)로 메인 GOOD 통과. 재검사 GOOD은 90° 롤(−)로 받음 → 0° → 롤(+)
사용: py -3.12 build_v6_turntable.py <V6_plc_19_base> <출력>"""
import sys, re, io, os
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H)
from fio_lib import place, scene, F, _idx
src, out = sys.argv[1:3]; t = F.load(src)
code = io.open(os.path.join(H, "build_v6_plc.py"), encoding="utf-8").read()
exec(code[:code.index("# ---- 크레인 구간")].replace("out = sys.argv[1]; ", "").replace(code[code.index("sys.path.insert"):code.index("\n", code.index("sys.path.insert"))], ""))
PANEL = ("ElectricSwitchboard", "EmergencyStopButton", "StartPushButton", "StopPushButton", "ResetPushButton")
for o in F.OBJ_RE.findall(t):
    x, z = (int(v) for v in re.search(r'<Position X="([^"]+)" Y="[^"]+" Z="([^"]+)"', o).groups()); pn = re.search(r'PrefabName="([^"]+)"', o).group(1)
    if pn in PANEL: O.append(o.replace(f'Z="{z}"', f'Z="{z-8}"', 1))
    elif x > 230: O.append(o)
_idx[0] = max(int(v) for v in re.findall(r'ComponentIO Index="(\d+)"', t)) + 1
def tt(x, z, n, name):
    d = ("Load", "Unload", "Turn", "At load position", "At unload position", "At front", "At back")
    O.append(place("Turntable", x, 2, z, "W", names={k: (v or f"{name} {k}") for k, v in zip(d, n)}))
# 컨베이어는 나가는 쪽 끝이 0.7칸 짧아 보여, 턴테이블을 들어오는 컨베이어 쪽으로 1칸씩 당겨 붙임(11-25)
#            롤(+)    롤(−)    회전     0°       90°      앞(Fr)   뒤(Bk)
tt(219, 184, ("Y1662", "Y1663", "Y1664", "X1664", "X1668", "X1662", "X1663"), "TT1"); retro(228, 184, "X", "X1660")
roller(2, 219, 200, "S", "Y1690"); retro(219, 197, "Z", "X1902"); remover(219, 205)
roller(2, 219, 168, "N", "Y1700"); retro(219, 162, "Z", "X1666")
tt(219, 153, ("Y1665", None, "Y1666", "X1667", "X1669", "X1665", None), "TTM")
roller(4, 195, 153, "W", "Y1700")
rstop(183, 153, "W", "Y1701", 3); retro(187, 153, "X", "X1700"); rfid(186, 157, "N", 1520)
roller(2, 171, 153, "W", "Y1702"); retro(165, 153, "X", "X1720")
tt(156, 153, ("Y1722", "Y1723", "Y1724", "X1725", "X1726", "X1723", "X1724"), "TT2")
# GOOD
roller(2, 156, 169, "S", "Y1703"); curve(152, 184, "W", "Y1703", ccw=True); roller(2, 137, 188, "W", "Y1703"); retro(131, 188, "X", "X1903")
tt(122, 188, ("Y1904", "Y1906", "Y1905", "X1907", "X1908", "X1904", "X1905"), "TT5")
roller(4, 98, 188, "W", "Y1900"); retro(94, 188, "X", "X1900"); remover(85, 188)
# 재검사
roller(2, 156, 137, "N", "Y1800"); retro(156, 133, "Z", "X1800"); curve(152, 122, "S", "Y1800"); roller(2, 137, 118, "W", "Y1800")
rstop(133, 118, "W", "Y1730", 3); retro(137, 118, "X", "X1730"); rfid(136, 122, "N", 1530); retro(131, 118, "X", "X1731")
tt(122, 118, ("Y1733", "Y1734", "Y1735", "X1735", "X1737", "X1733", "X1734"), "TT3")
# 재검사 GOOD → TT5 (54칸 = 2 m + 4 m · 2 m, 끝을 1칸 물려 붙이고 4 m · 2 m는 8칸 겹침)
roller(2, 122, 134, "S", "Y1731"); roller(4, 122, 157, "S", "Y1736"); roller(2, 122, 173, "S", "Y1736")
O.append(place("DiffusePhotoelectricSensor", 127, 5, 153, "N", extra=lambda o: re.sub(r'(<BinaryInput Name=")[^"]*', r'\g<1>X1736', o).replace("<FinePosition>0<", "<FinePosition>-0.0625<")))
# NG
curve(118, 103, "S", "Y1732"); roller(2, 103, 99, "W", "Y1901"); retro(106, 99, "X", "X1901"); remover(98, 99)
m = re.search(r'OrbitCamera">\s*<Data>\s*<CameraPosition X="([^"]+)" Y="([^"]+)" Z="([^"]+)" />\s*<PivotPosition X="([^"]+)" Y="([^"]+)" Z="([^"]+)"', t).groups()
added = scene(O, out, "Project B v6 line (roller + curve + turntable)", camera=(m[:3], m[3:]))
print("부품", len(O), "· 연결", len(added))
