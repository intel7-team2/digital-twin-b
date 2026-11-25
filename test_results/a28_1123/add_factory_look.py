"""완성 씬(V6_plc_18) 둘레에 펜스 · 통로 · 제어반 · 설비를 덧붙여 공장처럼 꾸밈(11-25, 기능 변경 없음).
기존 물체 · 드라이버 매핑 문자열은 그대로 두고 마지막 </Object> 뒤에만 추가. 새 태그는 Modbus에 매핑하지 않음(래더 · 주소 영향 없음).
사용: python add_factory_look.py <원본> <출력>"""
import sys, re
from fio_lib import place, F, _idx
src, out = sys.argv[1:3]
t = F.load(src); O = []
_idx[0] = max(int(x) for x in re.findall(r'ComponentIO Index="(\d+)"', t)) + 1
A = lambda p, x, y, z, yaw="S", **k: O.append(place(p, x, y, z, yaw, **k))
# ---- 1. 크레인 · 랙 구역 펜스(높은 펜스 17칸). 컨베이어 통로 z 177~193, 작업자 출입구 = 남쪽 x=299 ----
for z in (100, 117, 134, 151, 168, 202):
    A("SafeguardL", 308, 10, z, "N"); A("SafeguardL", 239, 10, z, "S")
for x in (299, 282, 265, 248): A("SafeguardL", x, 10, 91, "E")
for x in (282, 265, 248): A("SafeguardL", x, 10, 211, "W")
A("LightCurtainEmitter", 293, 9, 211, "N"); A("LightCurtainReceiver", 303, 9, 211, "N")
# ---- 2. 메인 검사 · 재검사 구역 펜스 ----
for x in (206, 189):
    A("SafeguardL", x, 10, 171, "W"); A("SafeguardL", x, 10, 147, "E")
for x in (156, 173): A("SafeguardL", x, 10, 122, "E")
A("SafeguardL", 182, 10, 131, "N")
# ---- 3. 발열 격리 구역(위험 구역) ----
A("SafeguardL", 231, 10, 200, "N"); A("SafeguardL", 213, 10, 200, "S"); A("SafeguardL", 222, 10, 209, "W")
# ---- 4. 전체 둘레 낮은 펜스 (출입구 2곳: 남쪽 x=186(통로 계단 앞), 동쪽 z=143) ----
for k in range(16):
    x = 84 + 17 * k
    A("Safeguard", x, 6, 83, "E")
    if x != 186: A("Safeguard", x, 6, 220, "W")
for k in range(8):
    z = 92 + 17 * k
    if z != 143: A("Safeguard", 348, 6, z, "N")
    A("Safeguard", 75, 6, z, "S")
# ---- 5. 관찰 통로(GOOD 라인 남쪽, 높이 11칸) ----
for x in (125, 147, 169):
    A("PlatformL", x, 11, 206, "S")
    A("HandrailXL", x, 16, 198, "W"); A("HandrailXL", x, 16, 213, "W")
for x in (114, 136, 158, 179):
    for z in (199, 213): A("PlatformPillar", x, 5, z, "S")
for z in (202, 210): A("HandrailM", 114, 15, z, "S")
A("PlatformM", 184, 11, 202, "S"); A("PlatformPillar", 187, 5, 199, "S")
A("Stairs", 185, 10, 207, "N")
for x in (181, 188): A("StairsHandrail", x, 11, 214, "N")
A("CornerHandrail", 184, 16, 201, "W")
# ---- 6. 구역별 제어반 + 표시기 + 경광등 기둥 ----
for x, z in ((196, 176), (160, 117), (206, 203), (314, 205)):
    A("Column", x, 8, z, "S"); A("ElectricSwitchboard", x + 1, 12, z, "S"); A("DigitalDisplay", x + 3, 12, z, "S")
for x, z in ((235, 212), (311, 214), (184, 175), (185, 121)):
    A("Column", x, 8, z, "S"); A("WarningLight", x, 17, z, "S")
# ---- 7. 둘레 설비 · 예비 랙 ----
for z in (110, 137, 164): A("Rack", 400, 25, z, "S")
for z in (110, 150): A("MachiningCenter", 42, 9, z, "S")
A("Tank", 400, 18, 215, "S"); A("Tank", 372, 18, 215, "S")
# 추가 태그 번호: 종류별로 기존 최댓값 뒤부터
body = "\n  ".join(O); mx = {}
for k, a in re.findall(r'<((?:Binary|Int|Analogue)(?:Input|Output)) Name="[^"]*" Address="(-?\d+)"', t): mx[k] = max(mx.get(k, -1), int(a))
def ren(m):
    k = m.group(1); mx[k] = mx.get(k, -1) + 1; return f'<{k} Name="deco {m.group(2)} {mx[k]}" Address="{mx[k]}"'
body = re.sub(r'<((?:Binary|Int|Analogue)(?:Input|Output)) Name="([^"]*)" Address="-?\d+"', ren, body)
e = t.rfind("</Object>") + 9
new = t[:e] + "\n  " + body + t[e:]
assert F.modbus_address_table(new) == F.modbus_address_table(t)
assert all(o in new for o in F.OBJ_RE.findall(t))
F.save(out, new); print("추가 부품", len(O))
