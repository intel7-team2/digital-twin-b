"""씬의 부품 Y만 바꿈(11-25, Roller Stop 높이). 사용: python set_part_y.py <원본> <출력> "<Prefab>@x,z=y" ..."""
import sys, re
sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
import fio_scene as F
src, out = sys.argv[1:3]; t = F.load(src)
for spec in sys.argv[3:]:
    name, rest = spec.split("@"); a, y = rest.split("="); x, z = a.split(",")
    hit = [o for o in F.OBJ_RE.findall(t) if f'PrefabName="{name}"' in o and re.search(rf'<Position X="{x}" Y="[^"]+" Z="{z}"', o)]
    assert len(hit) == 1, f"{spec}: {len(hit)}개"
    t = t.replace(hit[0], re.sub(rf'(<Position X="{x}" Y=")[^"]+', rf'\g<1>{y}', hit[0], count=1), 1); print(spec)
F.save(out, t)
