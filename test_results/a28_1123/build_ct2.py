"""Chain Transfer '체인 축 통과' 배치 (A28 · 1차 분리 / M1720 형태: 직진 + 한쪽 분기).
원본 'Sorting by Height (Basic)': CT(255,140), 롤러(+) 방향 = -X 쪽(고정 스토퍼), 체인 = ±Z.
- 공급: Z=120 컨베이어를 +Z(센터 쪽)로 뒤집고 Emitter를 그 끝(Z=108)으로
- 직진 출구: Z=160 컨베이어(+Z) · 센서 'At right exit'
- 분기 출구: X=275 컨베이어를 +X(바깥)로 뒤집음 · 센서 'At divert exit'(X=283에 새로)
- 중앙 정지: 'At right entry' 빔(Z=144, Transfer 출구 가장자리)
- 'Loaded' 센서 · 'Remover left'는 라인 밖으로"""
import re, sys, os, uuid
sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
import fio_scene as F
out = sys.argv[1]
t = F.load(os.path.join(F.SCENES_DIR, "Sorting by Height (Basic).factoryio"))
def obj_with(name):
    return next(m.group(0) for m in F.OBJ_RE.finditer(t) if f'Name="{name}"' in m.group(0))
def edit(o, pos=None, rot=None, rename=None):
    o2 = o
    if pos: o2 = re.sub(r'<Position [^>]*/>', '<Position X="%s" Y="%s" Z="%s" />' % pos, o2, 1)
    if rot: o2 = re.sub(r'<Rotation [^>]*/>', '<Rotation X="0" Y="%s" Z="0" W="%s" />' % rot, o2, 1)
    if rename:
        for a, b in rename.items(): o2 = o2.replace(f'Name="{a}"', f'Name="{b}"')
    return o2
def sub(name, **kw):
    global t
    o = obj_with(name); t = t.replace(o, edit(o, **kw), 1)
sub("Conveyor left", rot=("0", "1"), rename={"Conveyor left": "Feed conveyor"})       # +Z 로 공급
sub("Conveyor entry", rot=("0.7071068", "0.7071068"), rename={"Conveyor entry": "Divert conveyor"})  # +X 바깥으로
emi = next(m.group(0) for m in F.OBJ_RE.finditer(t) if 'PrefabName="Emitter"' in m.group(0))
t = t.replace(emi, edit(emi, pos=("255", "6", "108")), 1)
sub("Remover left", pos=("287", "6", "140"), rename={"Remover left": "Remover divert"})
sub("Loaded", pos=("240", "1", "100"))
sub("At left exit", rename={"At left exit": "At feed"})
# 분기 출구 센서: 'At left exit' 센서/거울 쌍을 복제해 X=283, 빔은 Z 136→144
sens = obj_with("At feed")
mir = next(m.group(0) for m in F.OBJ_RE.finditer(t) if 'PrefabName="RetroreflectiveMirror"' in m.group(0) and 'Z="114"' in m.group(0))
def clone(o, pos, rot, names):
    o = re.sub(r'Key="[0-9a-f-]{36}"', lambda m: f'Key="{uuid.uuid4()}"', o)
    o = re.sub(r'GroupKey="[0-9a-f-]{36}"', f'GroupKey="{F.ZERO}"', o)
    o = edit(o, pos=pos, rot=rot, rename=names)
    return re.sub(r'ComponentIO Index="(\d+)"', lambda m: f'ComponentIO Index="{int(m.group(1)) + 20}"', o)
maxin = max(tg["address"] for tg in F.tags(t) if tg["io"] == "Input")
ns = clone(sens, ("283", "5", "136"), ("-0.7071068", "0.7071068"), {"At feed": "At divert exit"})
ns = re.sub(r'(<BinaryInput Name="At divert exit" Address=")-?\d+', lambda m: m.group(1) + str(maxin + 1), ns)
nm = clone(mir, ("283", "5", "144"), ("-0.7071068", "0.7071068"), {})
last = list(F.OBJ_RE.finditer(t))[-1]
ind = re.search(r'\n[ \t]*$', t[:last.start()]).group(0)
t = t[:last.end()] + ind + ns + ind + nm + t[last.end():]
t, _ = F.set_emitter(t, ["BoxL"], ["SquarePallet"])
for n in ["Feed conveyor", "Divert conveyor", "Conveyor right"]:
    t, _ = F.set_force(t, n, "on")
t, _ = F.set_force(t, "Emitter", "release")
t, added = F.map_modbus(t)
run = re.search(r'RunOutputKey="([0-9a-f-]{36})"', t).group(1)
mb = F.modbus_points(t); nout = mb["count"]["BitOutput"]
bs, be = mb["match"].span(); blk = t[bs:be]
blk = re.sub(r'BitOutputCount="\d+"', f'BitOutputCount="{nout + 1}"', blk, 1)
lo = re.search(rf'([ \t]*)<BitOutput{nout - 1} PointIOKey="[^"]*" />', blk)
blk = blk[:lo.end()] + "\n" + f'{lo.group(1)}<BitOutput{nout} PointIOKey="{run}" />' + blk[lo.end():]
t = t[:bs] + blk + t[be:]
t = F.touch_header(t, "Project B A28: Chain Transfer pass-through on chains, divert by rollers(-)")
F.save(out, t)
print("added", [a[0] for a in added])
