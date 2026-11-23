"""A36 관통형 시험 씬 v2(F2t): F2q_crane_cycle_S에 크레인 B를 A와 **같은 방향**으로 X=256에 복제.
- B 칸 번호 = A 칸 번호(같은 레일 끝 기준). B의 랙 쪽 포크 = Left(+X), A의 랙 쪽 = Right(-X)
- 랙 뒤 안전 펜스(X=247) · 출구 컨베이어(253,184) · Remover(250,184) · At Exit 센서 · 거울(255) → 라인 밖으로(B 대기 위치와 겹침)
- 카메라 'Current' = 랙 위에서 내려다봄
사용: build_two_cranes2.py <출력>"""
import re, sys, uuid
sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
import fio_scene as F
out = sys.argv[1]
t = F.load(r"D:/seojung/digital-twin-b/factoryio_test/F2q_crane_cycle_S.factoryio")
def move(o, x, y, z): return re.sub(r'<Position X="[^"]*" Y="[^"]*" Z="[^"]*" />', f'<Position X="{x}" Y="{y}" Z="{z}" />', o, 1)
moved = 0
for m in list(F.OBJ_RE.finditer(t)):
    o = m.group(0)
    pn = re.search(r'PrefabName="([^"]+)"', o).group(1)
    pos = re.search(r'<Position X="([^"]+)" Y="([^"]+)" Z="([^"]+)"', o).groups()
    if pn == "SafeguardL" and pos[0] == "247":
        t = t.replace(o, move(o, 200, pos[1], pos[2]), 1); moved += 1
    elif (pn, pos) in {("RollerConveyor2M", ("253", "2", "184")), ("Remover", ("250", "6", "184")),
                       ("RetroreflectivePhotoelectricSensor", ("255", "5", "188")), ("RetroreflectiveMirror", ("255", "5", "180"))}:
        t = t.replace(o, move(o, 200 - moved, pos[1], 40), 1); moved += 1
a = next(m.group(0) for m in F.OBJ_RE.finditer(t) if 'PrefabName="StackerCrane"' in m.group(0))
b = re.sub(r'Key="[0-9a-f-]{36}"', lambda m: f'Key="{uuid.uuid4()}"', a)
b = b.replace('<Position X="276" Y="33" Z="146" />', '<Position X="256" Y="33" Z="146" />')
b = b.replace('ComponentIO Index="1"', 'ComponentIO Index="95"')
mx = {"Input": 0, "Output": 0}
for tg in F.tags(t): mx[tg["io"]] = max(mx[tg["io"]], tg["address"])
def ren(m):
    el, name = m.group(1), m.group(2); io_ = "Input" if el.endswith("Input") else "Output"
    mx[io_] += 1
    return f'<{el} Name="{name} B" Address="{mx[io_]}"'
b = re.sub(r'<(BinaryInput|BinaryOutput|IntOutput) Name="([^"]*)" Address="-?\d+"', ren, b)
t = t.replace(a, a + "\n  " + b, 1)
t = re.sub(r'(<CameraPosition Name="Current" Type="OrbitCamera">\s*<Data>\s*)<CameraPosition [^>]*/>\s*<PivotPosition [^>]*/>',
           r'\1<CameraPosition X="33.2" Y="13" Z="19.6" />\n        <PivotPosition X="33.2" Y="0" Z="19.0" />', t)
t, added = F.map_modbus(t)
t = F.touch_header(t, "Project B A36 v2: two cranes same orientation on both sides of one rack")
F.save(out, t)
print("옮긴 부품", moved, "· 연결 추가", len(added))
