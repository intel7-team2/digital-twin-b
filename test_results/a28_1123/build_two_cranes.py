"""A36 관통형 시험 씬(F2r): F2q_crane_cycle_S(크레인 A, 랙 X=266, A는 X=276)에
크레인 B를 랙 반대쪽 X=256에 180° 돌려 복제. B 태그 = A 이름 + ' B'. B의 Right = +X(랙 쪽).
사용: build_two_cranes.py <출력>"""
import re, sys, uuid
sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
import fio_scene as F
out = sys.argv[1]; BX = sys.argv[2] if len(sys.argv) > 2 else "256"
t = F.load(r"D:/seojung/digital-twin-b/factoryio_test/F2q_crane_cycle_S.factoryio")
a = next(m.group(0) for m in F.OBJ_RE.finditer(t) if 'PrefabName="StackerCrane"' in m.group(0))
b = re.sub(r'Key="[0-9a-f-]{36}"', lambda m: f'Key="{uuid.uuid4()}"', a)
b = b.replace('<Position X="276" Y="33" Z="146" />', '<Position X="' + BX + '" Y="33" Z="146" />')
b = b.replace('<Rotation X="0" Y="-1" Z="0" W="0" />', '<Rotation X="0" Y="0" Z="0" W="1" />')
b = b.replace('<Forward X="0" Y="0" Z="-1" />', '<Forward X="0" Y="0" Z="1" />')
b = b.replace('<Right X="-1" Y="0" Z="0" />', '<Right X="1" Y="0" Z="0" />')
b = b.replace('ComponentIO Index="1"', 'ComponentIO Index="95"')
mx = {"Input": 0, "Output": 0}
for tg in F.tags(t): mx[tg["io"]] = max(mx[tg["io"]], tg["address"])
def ren(m):
    el, name = m.group(1), m.group(2)
    io_ = "Input" if el.endswith("Input") else "Output"
    mx[io_] += 1
    return f'<{el} Name="{name} B" Address="{mx[io_]}"'
b = re.sub(r'<(BinaryInput|BinaryOutput|IntOutput) Name="([^"]*)" Address="-?\d+"', ren, b)
t = t.replace(a, a + "\n  " + b, 1)
t, added = F.map_modbus(t)
t = F.touch_header(t, "Project B A36: two stacker cranes on both sides of one rack")
F.save(out, t)
print("연결 추가:", [(x[0], x[1], x[2]) for x in added])
