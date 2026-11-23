"""크레인 입고점 정지 장치 시험 씬 (F2m).
원본: factoryio_test/F2g_crane_SqPallet_S.factoryio (Automated Warehouse 복사본, SquarePallet + BoxS)
- Load Conveyor: 단순 ON/OFF → 아날로그(−10~+10 V, 속도 · 방향). 'Load speed' 이름, Modbus Holding Register
- Entry Conveyor: 강제 ON 해제 → 코일
- 위치 센서(반사형, 빔은 Z 188 → 180으로 컨베이어를 가로지름) 높이를 팔레트 높이로(인자 Y, 기본 4)
  · At Load (X=281)      팔레트 머리 = 정위치 기준
  · At Load over (X=278) 지나침
  · At Load tail (X=290) 꼬리(덜 들어옴)
- Modbus ScaleFactor 100 (레지스터 1000 = 10.00 V)
사용: build_crane_stop.py <출력> [빔 Y]"""
import re, sys, uuid
sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
import fio_scene as F
out = sys.argv[1]; BY = sys.argv[2] if len(sys.argv) > 2 else "4"
t = F.load(r"D:/seojung/digital-twin-b/factoryio_test/F2g_crane_SqPallet_S.factoryio")
objs = [m.group(0) for m in F.OBJ_RE.finditer(t)]
def with_name(n): return next(o for o in objs if f'Name="{n}"' in o)
# 1) 로딩 컨베이어 → 아날로그
lc = with_name("Load Conveyor")
lc2 = lc.replace('CurrentOperatingMode="0"', 'CurrentOperatingMode="2"')
lc2 = lc2.replace("$C_RollerConveyor_OM_SingleBinary_NAME", "$C_RollerConveyor_OM_Analogue_NAME")
lc2 = re.sub(r'<BinaryOutput Name="Load Conveyor" Address="(\d+)" Key="([0-9a-f-]{36})"([^>]*)ForcedValue="[^"]*" />',
             lambda m: f'<AnalogueOutput Name="Load speed" Address="{m.group(1)}" Key="{uuid.uuid4()}"{m.group(3)}ForcedValue="0" />', lc2)
old_key = re.search(r'Name="Load Conveyor" Address="\d+" Key="([0-9a-f-]{36})"', lc).group(1)
t = t.replace(lc, lc2, 1)
t = t.replace(f'PointIOKey="{old_key}"', f'PointIOKey="{F.ZERO}"')       # 옛 코일 연결 비움
# 2) 입고 컨베이어 강제 해제
t, _ = F.set_force(t, "Entry Conveyor", "release")
# 3) 센서 높이 · 추가
def set_y(o, y): return re.sub(r'<Position X="([^"]*)" Y="[^"]*" Z="([^"]*)" />', rf'<Position X="\1" Y="{y}" Z="\2" />', o, 1)
al = with_name("At Load")
mir = next(o for o in objs if 'PrefabName="RetroreflectiveMirror"' in o and 'X="281"' in o)
t = t.replace(al, set_y(al, BY), 1); t = t.replace(mir, set_y(mir, BY), 1)
maxin = max(tg["address"] for tg in F.tags(t) if tg["io"] == "Input")
def clone(o, x, name=None):
    global maxin
    o = re.sub(r'Key="[0-9a-f-]{36}"', lambda m: f'Key="{uuid.uuid4()}"', o)
    o = re.sub(r'GroupKey="[0-9a-f-]{36}"', f'GroupKey="{F.ZERO}"', o)
    o = re.sub(r'<Position X="[^"]*" Y="[^"]*" Z="([^"]*)" />', rf'<Position X="{x}" Y="{BY}" Z="\1" />', o, 1)
    o = re.sub(r'ComponentIO Index="(\d+)"', lambda m: f'ComponentIO Index="{int(m.group(1)) + 30}"', o)
    if name:
        maxin += 1
        o = re.sub(r'<BinaryInput Name="At Load" Address="-?\d+"', f'<BinaryInput Name="{name}" Address="{maxin}"', o)
    return o
new = [clone(al, 278, "At Load over"), clone(mir, 278), clone(al, 290, "At Load tail"), clone(mir, 290)]
last = list(F.OBJ_RE.finditer(t))[-1]
ind = re.search(r'\n[ \t]*$', t[:last.start()]).group(0)
t = t[:last.end()] + "".join(ind + o for o in new) + t[last.end():]
# 4) Modbus 연결 · 배율
t, added = F.map_modbus(t)
mb = F.modbus_points(t); bs, be = mb["match"].span(); blk = t[bs:be]
blk = re.sub(r'ScaleFactor="[^"]*"', 'ScaleFactor="100"', blk)
t = t[:bs] + blk + t[be:]
t = F.touch_header(t, f"Project B crane infeed stop: analog load conveyor + pallet-height sensors (Y={BY})")
F.save(out, t)
print("연결 추가:", [(a[0], a[1], a[2]) for a in added])
