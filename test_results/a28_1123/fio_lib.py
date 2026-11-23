"""Factory I/O 부품 견본 모음 + 씬 생성 도우미.
견본: 기본 씬(Scenes/*.factoryio) + 우리 시험 씬(T0_templates: 곡선 벨트 · RFID, F2t: 크레인 2대 · 아날로그 로딩).
place(prefab, x, y, z, yaw, names={기존 태그 이름: 새 이름}, src=견본 선택 문자열) → Object XML (새 Key)
yaw: 진행 방향(Forward) 기준 'S'(+Z) 'N'(−Z) 'E'(+X) 'W'(−X)"""
import re, os, io, glob, uuid, sys
sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
import fio_scene as F
SC = r"C:/Program Files (x86)/Real Games/Factory IO/Scenes"
EXTRA = [r"C:/Users/user/Documents/Factory IO/My Scenes/T0_templates.factoryio",
         r"D:/seojung/digital-twin-b/factoryio_test/F2t_two_cranes_same.factoryio"]
LIB = {}
for f in sorted(glob.glob(SC + "/*.factoryio")) + EXTRA:
    s = io.open(f, encoding="utf-8-sig").read()
    for o in F.OBJ_RE.findall(s):
        pn = re.search(r'PrefabName="([^"]+)"', o).group(1)
        LIB.setdefault(pn, []).append((os.path.basename(f), o))
Q = {"S": ("0", "1", "1", "1", "0"), "N": ("1", "0", "-1", "-1", "0"),
     "E": ("0.7071068", "0.7071068", "1", "0", "-1"), "W": ("-0.7071068", "0.7071068", "-1", "0", "1")}
def rot_xml(yaw):
    qy, qw, *_ = Q[yaw]
    fwd = {"S": (0, 1), "N": (0, -1), "E": (1, 0), "W": (-1, 0)}[yaw]
    right = {"S": (1, 0), "N": (-1, 0), "E": (0, -1), "W": (0, 1)}[yaw]
    return (f'<Rotation X="0" Y="{qy}" Z="0" W="{qw}" />', f'<Forward X="{fwd[0]}" Y="0" Z="{fwd[1]}" />',
            f'<Right X="{right[0]}" Y="0" Z="{right[1]}" />')
_idx = [100]
def place(prefab, x, y, z, yaw="S", names=None, src=None, extra=None):
    cands = LIB[prefab]
    if src: cands = [c for c in cands if src in c[0] or src in c[1]] or cands
    o = cands[0][1]
    o = re.sub(r'Key="[0-9a-f-]{36}"', lambda m: f'Key="{uuid.uuid4()}"', o)
    o = re.sub(r'GroupKey="[0-9a-f-]{36}"', f'GroupKey="{F.ZERO}"', o)
    o = re.sub(r'<Position [^>]*/>', f'<Position X="{x}" Y="{y}" Z="{z}" />', o, 1)
    r, fw, rt = rot_xml(yaw)
    o = re.sub(r'<Rotation [^>]*/>', r, o, 1); o = re.sub(r'<Forward [^>]*/>', fw, o, 1); o = re.sub(r'<Right [^>]*/>', rt, o, 1)
    _idx[0] += 1
    o = re.sub(r'ComponentIO Index="\d+"', f'ComponentIO Index="{_idx[0]}"', o)
    o = re.sub(r'UseForcedValue="True"', 'UseForcedValue="False"', o)
    if names:
        tags = re.findall(r'Name="([^"]*)"', o)
        for old, new in names.items():
            o = re.sub(rf'(?<=\s)Name="{re.escape(old)}"', f'Name="{new}"', o)
    if extra: o = extra(o)
    return o
def tag_names(prefab, src=None):
    c = LIB[prefab]
    if src: c = [x for x in c if src in x[0] or src in x[1]] or c
    return re.findall(r'<(?:Binary|Int|Analogue)(?:Input|Output) Name="([^"]*)"', c[0][1])
def scene(objs, out, desc, camera=None, base=r"C:/Users/user/Documents/Factory IO/My Scenes/T0_templates.factoryio"):
    """빈 씬(T0의 머리 · 드라이버)에 objs를 넣고 Modbus Server 연결 · Run 코일 · 배율 100으로 저장."""
    t = io.open(base, encoding="utf-8-sig").read()
    first = t.find("<Object "); last = t.rfind("</Object>") + len("</Object>")
    body = "\n  ".join(objs)
    t = t[:first] + body + t[last:] if first >= 0 else t.replace("</FactoryIO>", "  " + body + "\n</FactoryIO>")
    cnt = {}
    def renum(m):
        k = m.group(1); cnt[k] = cnt.get(k, -1) + 1
        return f'<{k} Name="{m.group(2)}" Address="{cnt[k]}"'
    t = re.sub(r'<((?:Binary|Int|Analogue)(?:Input|Output)) Name="([^"]*)" Address="-?\d+"', renum, t)
    t = F.set_driver(t, F.DRIVER["modbus-server"])
    t, added = F.map_modbus(t)
    run = re.search(r'RunOutputKey="([0-9a-f-]{36})"', t).group(1)
    mb = F.modbus_points(t); nout = mb["count"]["BitOutput"]; bs, be = mb["match"].span(); blk = t[bs:be]
    blk = re.sub(r'BitOutputCount="\d+"', f'BitOutputCount="{nout + 1}"', blk, 1)
    last = re.search(rf'([ \t]*)<BitOutput{nout - 1} PointIOKey="[^"]*" />', blk)
    blk = blk[:last.end()] + "\n" + f'{last.group(1)}<BitOutput{nout} PointIOKey="{run}" />' + blk[last.end():]
    blk = re.sub(r'ScaleFactor="[^"]*"', 'ScaleFactor="100"', blk)
    t = t[:bs] + blk + t[be:]
    if camera:
        (cx, cy, cz), (px, py, pz) = camera
        t = re.sub(r'(<CameraPosition Name="Current" Type="OrbitCamera">\s*<Data>\s*)<CameraPosition [^>]*/>\s*<PivotPosition [^>]*/>',
                   rf'\1<CameraPosition X="{cx}" Y="{cy}" Z="{cz}" />\n        <PivotPosition X="{px}" Y="{py}" Z="{pz}" />', t)
    t = F.touch_header(t, desc)
    F.save(out, t)
    return added
if __name__ == "__main__":
    for k in sorted(LIB): print(k, len(LIB[k]), LIB[k][0][0], tag_names(k)[:4])
