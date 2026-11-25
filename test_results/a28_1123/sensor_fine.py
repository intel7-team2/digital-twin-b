"""정전용량 센서의 FinePosition(CT 쪽 +, m)을 바꿈(11-25, CT 정지 위치 반 칸 맞춤). 사용: python sensor_fine.py <원본> <출력> X1662=-0.06 ..."""
import sys,re
sys.path.insert(0,r'D:/seojung/digital-twin-b/computer_use')
import fio_scene as F
src,out=sys.argv[1:3]; t=F.load(src)
for a in sys.argv[3:]:
    n,v=a.split('=')
    o=[o for o in F.OBJ_RE.findall(t) if f'Name="{n}"' in o and 'Capacitive' in o][0]
    t=t.replace(o,o.replace('<FinePosition>0<',f'<FinePosition>{v}<'))
F.save(out,t)
