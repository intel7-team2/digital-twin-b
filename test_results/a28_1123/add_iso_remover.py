"""11-27 발열 격리 레일 비우기(사용자 ①): V7_plc_1에 격리 레일 끝 리무버(코일 Y1695)를 더해 V7_plc_2로 저장.
작업자가 격리 팩을 들어내는 것을 흉내 — 래더 DRIVE V02~V04가 HMI '격리 팩 수거 완료'(M1963)를 받아 레일에 팔레트가 있을 때만 켬.
자리는 11-26 시험 씬(TESTREL, Y19F1)에서 확인한 (219, 6, 202) 그대로. 다른 부품 · Modbus 칸 · Run 코일은 그대로 두고 새 코일만 빈 칸에 연결.
사용: py -3.12 add_iso_remover.py <V7_plc_1> <V7_plc_2>"""
import sys, re, io, os
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H)
from fio_lib import place, F, _idx
src, out = sys.argv[1:3]
t = io.open(src, encoding="utf-8-sig").read()
assert 'Name="Y1695"' not in t, "이미 Y1695가 있음"
_idx[0] = max(int(v) for v in re.findall(r'ComponentIO Index="(\d+)"', t))
o = place("Remover", 219, 6, 202, "S", names={"Remover": "Y1695"})
# 11-27: 부품 견본의 태그 Address(씬 안 태그 번호)가 그대로 오면 다른 태그와 겹침(처음 만든 V7_plc_2에서 Y1608과 같은 3 → 크레인 B 포크가 안 움직임) → 같은 종류 최대 + 1
nxt = max(int(v) for v in re.findall(r'<BinaryOutput Name="[^"]*" Address="(\d+)"', t)) + 1
o = re.sub(r'(<BinaryOutput Name="Y1695" Address=")\d+', rf'\g<1>{nxt}', o)
last = t.rfind("</Object>") + len("</Object>")
t = t[:last] + "\n  " + o + t[last:]
t, added = F.map_modbus(t, only=["Y1695"])
print("연결:", added)
t = re.sub(r'(<Description Data=")[^"]*', r'\g<1>Project B v7 line (1F inspect + 2F sort, elevator) + ISO rail remover Y1695', t, 1)
io.open(out, "w", encoding="utf-8-sig").write(t)
print("저장", out)
