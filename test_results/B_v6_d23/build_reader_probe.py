"""RFID ② · ③ 리더 배치 비교용 씬(11-24): V6_plc_16에 후보 리더 8개씩을 더 단 V6_plc_16_RP를 만든다.
후보 이름은 D2000~(②) · D2100~(③) — 래더에 없는 번지라 시험 전용. softplc.py가 본 리더와 같은 팩에서 후보들도 읽게 해 비교한다.
사용: python build_reader_probe.py"""
import sys, re, io, uuid
sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
import fio_scene as F
SRC = r"D:/seojung/digital-twin-b/factoryio_test/V6_plc_16.factoryio"
OUT = r"D:/seojung/digital-twin-b/factoryio_test/V6_plc_16_RP.factoryio"
# (이름, dx 라인 방향, dz 라인 쪽(−면 라인에 가까움), Y, 감지 m) — 본 리더 기준
CAND = [("B 1칸 가깝게", 0, -1, 4, "1.0"),   # A(본 리더와 같은 자리) · C(0.8 m)는 Modbus 출력 칸(64) 부족으로 뺌
        ("D 범위 1.2m", 0, 0, 4, "1.2"), ("E 라인 +1", 1, 0, 4, "1.0"), ("F 라인 −1", -1, 0, 4, "1.0"),
        ("G 높이 Y3", 0, 0, 3, "1.0"), ("H 높이 Y5", 0, 0, 5, "1.0"), ("I 반대쪽(−Z)", 0, -10, 4, "1.0")]   # I: 라인 반대편에서 +Z를 봄(박스가 돌아 태그 면이 반대로 갔는지)
t = F.load(SRC)
objs = re.findall(r"<Object .*?</Object>", t, re.S)
idx = max(int(x) for x in re.findall(r'ComponentIO Index="(\d+)"', t))
add = []
for st, main, base0 in (("②", 1520, 2000), ("③", 1530, 2100)):
    rd = [o for o in objs if 'PrefabName="RFIDReader"' in o and f'Name="D{main}"' in o][0]
    x, y, z = (int(v) for v in re.search(r'<Position X="(-?\d+)" Y="(-?\d+)" Z="(-?\d+)"', rd).groups())
    for i, (nm, dx, dz, yy, rng) in enumerate(CAND):
        b = base0 + i * 10; idx += 1
        o = re.sub(r'Key="[0-9a-f-]{36}"', lambda m: f'Key="{uuid.uuid4()}"', rd)
        o = re.sub(r'<Position [^>]*/>', f'<Position X="{x - dx}" Y="{yy}" Z="{z + dz}" />', o, 1)   # 라인은 −X로 흐름 · 리더는 라인 +Z 쪽
        if dz <= -10: o = re.sub(r'<Rotation [^>]*/>', '<Rotation X="0" Y="0" Z="0" W="1" />', o, 1)
        o = re.sub(r'<Sensor Range="[^"]*"', f'<Sensor Range="{rng}"', o)
        o = re.sub(r'ComponentIO Index="\d+"', f'ComponentIO Index="{idx}"', o)
        for k in range(6):
            o = o.replace(f'Name="D{main + k}"', f'Name="D{b + k}"')
        o = o.replace(f'Name="M{main + 1}"', f'Name="M{b + 1}"')
        add.append(o); print(st, f"D{b}", nm, f"X{x - dx} Y{yy} Z{z + dz} 범위 {rng}")
t = t.replace(objs[-1], objs[-1] + "\n  " + "\n  ".join(add), 1)
t, added = F.map_modbus(t, only=["D20", "D21", "M20", "M21"])
F.save(OUT, t)
print("저장", OUT, "· Modbus 추가", len(added))
