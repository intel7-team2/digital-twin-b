"""씬의 센서 한 개를 X/Z 격자로 옮김(11-24, 실제 PLC 경로 지연 보정 시험).
사용: python move_sensor.py <원본 씬> <출력 씬> <센서 이름 예: X1662> <새 X> [새 Z]"""
import sys, re
sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
import fio_scene as F
src, out, name, nx = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
nz = sys.argv[5] if len(sys.argv) > 5 else None
t = F.load(src)
objs = [o for o in re.findall(r"<Object .*?</Object>", t, re.S) if f'Name="{name}"' in o]
assert len(objs) == 1, f"{name} 물체 {len(objs)}개"
o = objs[0]
n = re.sub(r'(<Position X=")[^"]+(")', rf'\g<1>{nx}\g<2>', o, count=1)
if nz: n = re.sub(r'(<Position X="[^"]+" Y="[^"]+" Z=")[^"]+(")', rf'\g<1>{nz}\g<2>', n, count=1)
t = t.replace(o, n, 1)
print(re.search(r'<Position[^>]+>', o).group(0), "→", re.search(r'<Position[^>]+>', n).group(0))
F.save(out, t)
