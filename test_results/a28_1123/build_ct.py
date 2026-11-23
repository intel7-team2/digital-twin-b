"""A28 시험 씬: 팔레트 + Chain Transfer 좌/우/직진. 기본 씬 'Sorting by Height (Basic)' 복사본에 직진 컨베이어 · 센서 · Remover 추가."""
import re, sys, uuid, os
sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
import fio_scene as F
src = os.path.join(F.SCENES_DIR, "Sorting by Height (Basic).factoryio")
base, out = sys.argv[1], sys.argv[2]
t = F.load(src)
objs = {m.group(0) for m in F.OBJ_RE.finditer(t)}
def get(tag):
    return next(o for o in objs if f'Name="{tag}"' in o)
def clone(o, pos, rot, fwd, right, names, idx_add=10):
    o = re.sub(r'Key="[0-9a-f-]{36}"', lambda m: f'Key="{uuid.uuid4()}"', o)
    o = re.sub(r'GroupKey="[0-9a-f-]{36}"', f'GroupKey="{F.ZERO}"', o)
    o = re.sub(r'<Position [^>]*/>', '<Position X="%s" Y="%s" Z="%s" />' % pos, o, 1)
    o = re.sub(r'<Rotation [^>]*/>', '<Rotation X="0" Y="%s" Z="0" W="%s" />' % rot, o, 1)
    o = re.sub(r'<Forward [^>]*/>', '<Forward X="%s" Y="0" Z="%s" />' % fwd, o, 1)
    o = re.sub(r'<Right [^>]*/>', '<Right X="%s" Y="0" Z="%s" />' % right, o, 1)
    o = re.sub(r'ComponentIO Index="(\d+)"', lambda m: f'ComponentIO Index="{int(m.group(1)) + idx_add}"', o)
    for old, new in names.items():
        o = o.replace(f'Name="{old}"', f'Name="{new}"')
    return o
maxaddr = {"Input": 0, "Output": 0}
for tg in F.tags(t):
    maxaddr[tg["io"]] = max(maxaddr[tg["io"]], tg["address"])
def readdr(o):
    def rep(m):
        io = "Input" if m.group(1).endswith("Input") else "Output"
        maxaddr[io] += 1
        return f'<{m.group(1)} Name="{m.group(2)}" Address="{maxaddr[io]}"'
    return re.sub(r'<(BinaryInput|BinaryOutput)\s+Name="([^"]*)"\s+Address="-?\d+"', rep, o)
R = ("-0.7071068", "0.7071068"); FW = ("-1", "0"); RT = ("0", "1")
new = [
    clone(get("Conveyor entry"), (235, 2, 140), R, FW, RT, {"Conveyor entry": "Conveyor straight"}),
    clone(get("At left exit"), (229, 5, 136), R, FW, RT, {"At left exit": "At straight exit"}),
    clone(get("Remover left"), (224, 6, 140), ("0", "1"), ("0", "1"), ("1", "0"), {"Remover left": "Remover straight"}),
]
mir = next(o for o in objs if 'PrefabName="RetroreflectiveMirror"' in o and 'Z="114"' in o)
new.append(clone(mir, (229, 5, 144), R, FW, RT, {}))
new = [readdr(o) for o in new]
last = list(F.OBJ_RE.finditer(t))[-1]
ind = re.search(r'\n[ \t]*$', t[:last.start()]).group(0)
t = t[:last.end()] + "".join(ind + o for o in new) + t[last.end():]
bases = [] if base == "none" else [base]
t, n = F.set_emitter(t, ["BoxL"], bases)
t = re.sub(r'MinTimeToEmit="[^"]*" MaxTimeToEmit="[^"]*"', 'MinTimeToEmit="14" MaxTimeToEmit="14"', t)
for nm in ["Conveyor entry", "Conveyor left", "Conveyor right", "Conveyor straight"]:
    t, k = F.set_force(t, nm, "on")
if len(sys.argv) > 3 and sys.argv[3] == "noloaded":   # 끝단 Loaded 센서 브래킷이 직진을 막음 → 제거
    o = next(m.group(0) for m in F.OBJ_RE.finditer(t) if 'Name="Loaded"' in m.group(0))
    o2 = re.sub(r'<Position [^>]*/>', '<Position X="240" Y="1" Z="100" />', o, 1)   # 지우면 씬이 안 열림 → 라인 밖 바닥으로 옮김
    t = t.replace(o, o2, 1)
t, _ = F.set_force(t, "Emitter", "release")   # 시험 코드가 한 개씩 내보냄
t, added = F.map_modbus(t)
# Run 신호를 코일에 연결
run = re.search(r'RunOutputKey="([0-9a-f-]{36})"', t).group(1)
mb = F.modbus_points(t)
nout = mb["count"]["BitOutput"]
bs, be = mb["match"].span()
blk = t[bs:be]
blk = re.sub(r'BitOutputCount="\d+"', f'BitOutputCount="{nout + 1}"', blk, 1)
lastout = re.search(rf'([ 	]*)<BitOutput{nout - 1} PointIOKey="[^"]*" />', blk)
blk = blk[:lastout.end()] + "\n" + f'{lastout.group(1)}<BitOutput{nout} PointIOKey="{run}" />' + blk[lastout.end():]
t = t[:bs] + blk + t[be:]
t = F.touch_header(t, f"Project B A28: {base} + Chain Transfer left/right/straight")
F.save(out, t)
print("added", added, "run coil", nout)
