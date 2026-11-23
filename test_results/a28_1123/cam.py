"""씬의 'Current' 카메라를 지정 격자 위치 위(높이 h m, 남쪽으로 d m 비스듬히)로 옮겨 새 파일로 저장. 사용: cam.py <씬> <출력> <X격자> <Z격자> [h] [d]"""
import re, sys
sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
import fio_scene as F
src, out, gx, gz = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
h = float(sys.argv[5]) if len(sys.argv) > 5 else 4.0; d = float(sys.argv[6]) if len(sys.argv) > 6 else 2.5
px, pz = gx * 0.125, gz * 0.125
t = F.load(src)
t = re.sub(r'(<CameraPosition Name="Current" Type="OrbitCamera">\s*<Data>\s*)<CameraPosition [^>]*/>\s*<PivotPosition [^>]*/>',
           rf'\1<CameraPosition X="{px}" Y="{h}" Z="{pz + d}" />\n        <PivotPosition X="{px}" Y="0.3" Z="{pz}" />', t)
F.save(out, t)
