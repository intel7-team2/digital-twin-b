"""크레인 입고점 Roller Stop 시험 씬 (F2n).
원본: factoryio_test/F2g_crane_SqPallet_S.factoryio (센서 원래 높이)
- Load Conveyor → 아날로그('Load speed', HR), Entry Conveyor 강제 해제(코일)
- Roller Stop(중량물 공압 스토퍼, Bool 'Load stop') 1개를 로딩 컨베이어 위 X=<인자>에
- Modbus ScaleFactor 100
사용: build_crane_rs.py <출력> <스토퍼 X>"""
import re, sys, uuid
sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
import fio_scene as F
out, SX = sys.argv[1], sys.argv[2]
t = F.load(r"D:/seojung/digital-twin-b/factoryio_test/F2g_crane_SqPallet_S.factoryio")
objs = [m.group(0) for m in F.OBJ_RE.finditer(t)]
lc = next(o for o in objs if 'Name="Load Conveyor"' in o)
lc2 = lc.replace('CurrentOperatingMode="0"', 'CurrentOperatingMode="2"').replace(
    "$C_RollerConveyor_OM_SingleBinary_NAME", "$C_RollerConveyor_OM_Analogue_NAME")
lc2 = re.sub(r'<BinaryOutput Name="Load Conveyor" Address="(\d+)" Key="[0-9a-f-]{36}"([^>]*)ForcedValue="[^"]*" />',
             lambda m: f'<AnalogueOutput Name="Load speed" Address="{m.group(1)}" Key="{uuid.uuid4()}"{m.group(2)}ForcedValue="0" />', lc2)
old_key = re.search(r'Name="Load Conveyor" Address="\d+" Key="([0-9a-f-]{36})"', lc).group(1)
t = t.replace(lc, lc2, 1).replace(f'PointIOKey="{old_key}"', f'PointIOKey="{F.ZERO}"')
t, _ = F.set_force(t, "Entry Conveyor", "release")
maxout = max(tg["address"] for tg in F.tags(t) if tg["io"] == "Output")
rot = re.search(r'<Rotation [^>]*/>', lc).group(0); fw = re.search(r'<Forward [^>]*/>', lc).group(0)
up = re.search(r'<Up [^>]*/>', lc).group(0); rt = re.search(r'<Right [^>]*/>', lc).group(0)
rs = f'''<Object Locked="False" GroupKey="{F.ZERO}">
    <Proxy PrefabName="RollerStop" Key="{uuid.uuid4()}">
      <Position X="{SX}" Y="2" Z="184" />
      {rot}
      <FineRotation>0</FineRotation>
      <FinePosition>0</FinePosition>
      {fw}
      {up}
      {rt}
    </Proxy>
    <ComponentIO Index="90" CurrentOperatingMode="0" />
    <OperatingMode Description="$C_OM_Default_NAME">
      <GroupIO Description="Default">
        <BinaryOutput Name="Load stop" Address="{maxout + 1}" Key="{uuid.uuid4()}" OpenCircuit="False" ShortCircuit="False" UseForcedValue="False" ForcedValue="False" />
      </GroupIO>
    </OperatingMode>
  </Object>'''
last = list(F.OBJ_RE.finditer(t))[-1]
ind = re.search(r'\n[ \t]*$', t[:last.start()]).group(0)
t = t[:last.end()] + ind + rs + t[last.end():]
t, added = F.map_modbus(t)
mb = F.modbus_points(t); bs, be = mb["match"].span()
t = t[:bs] + re.sub(r'ScaleFactor="[^"]*"', 'ScaleFactor="100"', t[bs:be]) + t[be:]
t = F.touch_header(t, f"Project B crane infeed: analog load conveyor + Roller Stop at X={SX}")
F.save(out, t)
print("연결 추가:", [(a[0], a[1], a[2]) for a in added])
