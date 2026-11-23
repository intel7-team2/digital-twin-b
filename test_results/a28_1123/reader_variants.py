"""RFID 리더 배치 비교(박스 밀림 재현): V6_plc_9에서 리더 ① 위치 · 높이 · 감지 거리를 바꾸고 Emitter 박스 위치를 무작위로.
① = ③과 같은 배치(막대 +1 · 라인 +Z 5칸 · Y4). 팩마다 시리얼(명령 1)을 읽어 성공 · 어느 태그(투입 순번으로 팔레트/박스 구분)인지 셈.
사용: reader_variants.py <이름> <dx(막대 기준)> <dz(라인 기준)> <Y> <감지 m> <팩 수>"""
import sys, re, io, time, subprocess
sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
import fio_scene as F
from pyModbusTCP.client import ModbusClient
name, dx, dz, y, rng, n = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5], int(sys.argv[6])
src = r"D:/seojung/digital-twin-b/factoryio_test/V6_plc_9.factoryio"; out = rf"D:/seojung/digital-twin-b/factoryio_test/RV_{name}.factoryio"
t = io.open(src, encoding="utf-8-sig").read()
objs = re.findall(r"<Object .*?</Object>", t, re.S)
rd = [o for o in objs if 'PrefabName="RFIDReader"' in o and 'Name="D1510"' in o][0]
r2 = re.sub(r'<Position X="[^"]*" Y="[^"]*" Z="[^"]*" />', f'<Position X="{318+dx}" Y="{y}" Z="{184+dz}" />', rd, 1)
r2 = re.sub(r'<Sensor Range="[^"]*"', f'<Sensor Range="{rng}"', r2)
if dz < 0: r2 = re.sub(r'<Rotation [^>]*/>', '<Rotation X="0" Y="0" Z="0" W="1" />', r2, 1)   # −Z 쪽이면 +Z를 봄
t = t.replace(rd, r2).replace('RandomPartPosition="False"', 'RandomPartPosition="True"')
F.save(out, t)
subprocess.run(["bash", "open_scene.sh", f"RV_{name}.factoryio"], capture_output=True)
txt = F.load(out); table = F.modbus_address_table(txt)
T = {}
for tg in F.tags(txt):
    if tg["key"] in table: T.setdefault(tg["name"], []).append(table[tg["key"]])
c = ModbusClient("127.0.0.1", 502)
def co(k, v):
    for ar, a, _ in T[k]: c.write_single_coil(a, v)
def hr(k, v):
    for ar, a, _ in T[k]: c.write_single_register(a, v & 0xFFFF)
def ir(k): return c.read_input_registers(T[k][0][1], 1)[0]
def di(k): return c.read_discrete_inputs(T[k][0][1], 1)[0]
def cmd(k_, idx=0):
    co("M1511", 0); hr("D1511", idx); hr("D1510", k_); cid = ir("D1513"); time.sleep(0.2); co("M1511", 1); st = time.time()
    while time.time() - st < 2 and ir("D1513") == cid: time.sleep(0.02)
    co("M1511", 0); time.sleep(0.15); return ir("D1514"), ir("D1515")
c.write_single_coil(table[re.search(r'RunOutputKey="([0-9a-f-]{36})"', txt).group(1)][1], 1); time.sleep(1)
co("Y1501", 1); co("Y1502", 1); hr("D1509", 2)
ok = box = 0; seen = []
for i in range(n):
    hr("D1508", 1 if i % 2 == 0 else 4); time.sleep(0.3); co("Y1500", 1); time.sleep(0.5); co("Y1500", 0)
    st = time.time()
    while time.time() - st < 12 and di("X1510"): time.sleep(0.05)
    time.sleep(1.0); co("Y1501", 0); time.sleep(0.4)
    s, v = cmd(1)
    seen.append(v)
    if v: ok += 1
    co("Y1502", 0); co("Y1501", 1); time.sleep(3.5); co("Y1502", 1)
# 시리얼은 투입마다 2개(팔레트 · 박스)씩 늘어남 → 같은 짝수/홀수면 같은 종류 태그
par = [v % 2 for v in seen if v]
print(f"{name}: dx={dx} dz={dz} Y={y} 거리 {rng} → 읽음 {ok}/{n} · 시리얼 {seen} · 태그 종류 {'한 가지' if len(set(par)) <= 1 else '섞임(팔레트 · 박스)'}", flush=True)
