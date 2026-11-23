"""A28 재시험 씬: Pop-up Wheel Sorter + SquarePallet, Emitter는 코일로 1개씩, Run 신호 코일 연결.
기본: 'Sorting by Weight' (F2c/F2d와 같은 원본)."""
import re, sys, os
sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
import fio_scene as F
bases, parts, out = sys.argv[1], sys.argv[2], sys.argv[3]
t = F.load(os.path.join(F.SCENES_DIR, "Sorting by Weight.factoryio"))
t, n = F.set_emitter(t, parts.split(","), [] if bases == "none" else bases.split(","))
for nm in ["Entry conveyor", "Left conveyor", "Right conveyor"]:   # Load scale · Front conveyor는 코일로 제어
    t, _ = F.set_force(t, nm, "on")
t, _ = F.set_force(t, "Emitter", "release")
t, _ = F.set_force(t, "Load scale", "release")
t, _ = F.set_force(t, "Front conveyor", "release")
t, added = F.map_modbus(t)
run = re.search(r'RunOutputKey="([0-9a-f-]{36})"', t).group(1)
mb = F.modbus_points(t); nout = mb["count"]["BitOutput"]
bs, be = mb["match"].span(); blk = t[bs:be]
blk = re.sub(r'BitOutputCount="\d+"', f'BitOutputCount="{nout + 1}"', blk, 1)
last = re.search(rf'([ \t]*)<BitOutput{nout - 1} PointIOKey="[^"]*" />', blk)
blk = blk[:last.end()] + "\n" + f'{last.group(1)}<BitOutput{nout} PointIOKey="{run}" />' + blk[last.end():]
t = t[:bs] + blk + t[be:]
t = F.touch_header(t, f"Project B A28 retest: Pop-up Wheel + {bases} + {parts}, one at a time")
F.save(out, t)
