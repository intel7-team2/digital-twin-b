"""씬의 부품을 종류 + 격자 위치로 찾아 옮김(11-25, CT 끝막이 정지 위치에 다음 롤러를 맞춤).
사용: python move_part.py <원본> <출력> "<Prefab>@x,z>nx,nz" ..."""
import sys, re
sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
import fio_scene as F
src, out = sys.argv[1:3]; t = F.load(src)
for spec in sys.argv[3:]:
    name, rest = spec.split("@"); a, b = rest.split(">"); x, z = a.split(","); nx, nz = b.split(",")
    hit = [o for o in F.OBJ_RE.findall(t) if f'PrefabName="{name}"' in o and re.search(rf'<Position X="{x}" Y="[^"]+" Z="{z}"', o)]
    assert len(hit) == 1, f"{spec}: {len(hit)}개"
    n = re.sub(rf'(<Position X="){x}(" Y="[^"]+" Z="){z}"', rf'\g<1>{nx}\g<2>{nz}"', hit[0], count=1)
    t = t.replace(hit[0], n, 1); print(spec)
F.save(out, t)
