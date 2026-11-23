"""높이 센서(X1511) 위치 찾기: RFID① 정지 위치(X=322)에 반사형 Y=6 · 7 · 8 · 9를 두고 BoxS / BoxL이 어느 높이를 가리는지.
사용: height_probe.py build BoxS|BoxL <출력> | height_probe.py run <씬>"""
import sys, re, io, time
if sys.argv[1] == "build":
    part, out = sys.argv[2], sys.argv[3]
    s = io.open("build_v6_plc.py", encoding="utf-8").read()
    s = s.replace('["BoxS"]', f'["{part}"]')
    s = s.replace("# ---- 출고 → CT1(1차 분리) ----", "\n".join(
        f'O.append(place("RetroreflectivePhotoelectricSensor", 322, {y}, 189, "E", names={{"Sensor": "H{y}"}}, extra=FPR)); O.append(place("RetroreflectiveMirror", 322, {y}, 179, "E", extra=FP))'
        for y in (6, 7, 8, 9)) + "\n# ---- 출고 → CT1(1차 분리) ----")
    s = s.replace("out = sys.argv[1]", "out = sys.argv[1]")
    io.open("_hp_build.py", "w", encoding="utf-8").write(s)
    import subprocess; print(subprocess.run([sys.executable, "_hp_build.py", out], capture_output=True, text=True).stdout)
else:
    sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
    import fio_scene as F
    from pyModbusTCP.client import ModbusClient
    txt = F.load(sys.argv[2]); table = F.modbus_address_table(txt)
    A = {t["name"]: table[t["key"]] for t in F.tags(txt) if t["key"] in table}
    c = ModbusClient("127.0.0.1", 502)
    c.write_single_coil(table[re.search(r'RunOutputKey="([0-9a-f-]{36})"', txt).group(1)][1], 1); time.sleep(1)
    for t in F.tags(txt):
        if t["name"] in ("Y1501", "Y1502") and t["key"] in table: c.write_single_coil(table[t["key"]][1], 1)
    print("빈 상태:", {f"H{y}": c.read_discrete_inputs(A[f'H{y}'][1], 1)[0] for y in (6, 7, 8, 9)})
    c.write_single_coil(A["Y1500"][1], 1); time.sleep(0.3); c.write_single_coil(A["Y1500"][1], 0)
    st = time.time()
    while time.time() - st < 25 and c.read_discrete_inputs(A["X1510"][1], 1)[0]: time.sleep(0.05)
    print(f"X1510 가림까지 {time.time()-st:.1f} s")
    for k in range(6):
        time.sleep(0.5); print(" ", c.read_discrete_inputs(A["X1510"][1], 1)[0], {f"H{y}": c.read_discrete_inputs(A[f'H{y}'][1], 1)[0] for y in (6, 7, 8, 9)})
    print("정지 위치 X1510 =", c.read_discrete_inputs(A["X1510"][1], 1)[0], {f"H{y}": c.read_discrete_inputs(A[f'H{y}'][1], 1)[0] for y in (6, 7, 8, 9)}, "(False = 가림)")
