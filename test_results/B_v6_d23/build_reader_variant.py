"""RFID ② · ③ 본 리더 배치만 바꾼 씬(11-24). 후보를 옆에 같이 달면 같은 태그가 여러 리더 범위에 들어가 본 리더가 응답하지 않으므로
씬마다 본 리더 위치 하나만 바꿔 따로 시험한다.
사용: python build_reader_variant.py <이름> <dz(−면 라인에 가까움)> <Y> <감지 m>  → factoryio_test/V6_plc_16_<이름>.factoryio"""
import sys, re
sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
import fio_scene as F
name, dz, y, rng = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
SRC = r"D:/seojung/digital-twin-b/factoryio_test/V6_plc_16.factoryio"
OUT = rf"D:/seojung/digital-twin-b/factoryio_test/V6_plc_16_{name}.factoryio"
t = F.load(SRC)
for main in (1520, 1530):
    rd = [o for o in re.findall(r"<Object .*?</Object>", t, re.S) if 'PrefabName="RFIDReader"' in o and f'Name="D{main}"' in o][0]
    x, yy, z = (int(v) for v in re.search(r'<Position X="(-?\d+)" Y="(-?\d+)" Z="(-?\d+)"', rd).groups())
    o = re.sub(r'<Position [^>]*/>', f'<Position X="{x}" Y="{y}" Z="{z + dz}" />', rd, 1)
    o = re.sub(r'<Sensor Range="[^"]*"', f'<Sensor Range="{rng}"', o)
    t = t.replace(rd, o); print(f"D{main}: X{x} Y{yy}→{y} Z{z}→{z + dz} 범위 {rng}")
F.save(OUT, t)
