"""입고 진입 롤러(Y1504, 켜짐/꺼짐)를 속도 지정(아날로그, D1506)으로 바꿈(11-24).
실제 PLC(중계) 시험에서 로딩 컨베이어 앞쪽만 1.5 V로 느려지고 진입 롤러가 뒤에서 전속으로 밀어 팔레트가 돌아가 박스가 빠짐.
팔레트 길이 ≈ 로딩 컨베이어 길이라 감속 중에도 뒤쪽은 늘 진입 롤러 위 → 두 컨베이어를 같은 속도로 움직여야 함.
사용: python patch_entry_analog.py <원본 씬> <출력 씬>"""
import sys, re, uuid
sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
import fio_scene as F
src, out = sys.argv[1], sys.argv[2]
t = F.load(src)
objs = [o for o in re.findall(r"<Object .*?</Object>", t, re.S) if 'Name="Y1504"' in o]
assert len(objs) == 1, f"Y1504 물체 {len(objs)}개"
o = objs[0]
n = re.sub(r'<ComponentIO Index="(\d+)" CurrentOperatingMode="\d+" />', r'<ComponentIO Index="\1" CurrentOperatingMode="2" />', o)
n = re.sub(r'<OperatingMode Description="\$C_RollerConveyor_OM_SingleBinary_NAME">.*?</OperatingMode>',
           '<OperatingMode Description="$C_RollerConveyor_OM_Analogue_NAME">\n      <GroupIO Description="Default">\n'
           f'        <AnalogueOutput Name="D1506" Address="0" Key="{uuid.uuid4()}" OpenCircuit="False" ShortCircuit="False" UseForcedValue="False" ForcedValue="0" />\n'
           '      </GroupIO>\n    </OperatingMode>', n, flags=re.S)
assert "D1506" in n and "Y1504" not in n
t = t.replace(o, n, 1)
t, added = F.map_modbus(t, only=["D1506"])
print("Modbus 배정:", added)
F.save(out, t)
