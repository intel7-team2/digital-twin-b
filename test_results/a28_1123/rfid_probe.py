"""RFID 리더 배치 찾기: 롤러 위 Roller Stop에 팩(SquarePallet + 박스)을 세우고, 옆에 높이 · 방향을 달리한 리더 16개.
사용: rfid_probe.py build <출력> | rfid_probe.py run <씬>"""
import sys, re, time
sys.path.insert(0, r"C:/Users/user/AppData/Local/Temp/claude/e8d7333cd358df48/2a20cd28-28b0-4a51-bdd3-4e3ff36dede8/scratchpad/work")
sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
CASES = [(y, yaw, side) for y in (3, 4, 5, 6) for yaw, side in (("N", 5), ("S", 5), ("E", 5), ("W", 5))]
if sys.argv[1] == "build":
    from fio_lib import place, scene, F
    O = [place("RollerConveyor4M", 200, 2, 140, "W", names={"Conveyor": "R conv"}),
         place("RollerStop", 192, 2, 140, "W", names={"Load stop": "R stop"}),
         place("Emitter", 212, 6, 140, "W", names={"Emitter": "R emit"}, src="Automated Warehouse",
               extra=lambda o: F.set_emitter(re.sub(r'UpTo="\d+"', 'UpTo="0"', o), ["BoxS"], ["SquarePallet"])[0])]
    for i, (y, yaw, side) in enumerate(CASES):
        x = 190 + (i % 4) * 4; z = 140 + side if i < 8 else 140 - side      # 리더를 정지 위치 주변 앞뒤 · 양옆에 흩어 놓음
        n = {"RFID Reader 0 Command": f"R{i} cmd", "RFID Reader 0 Execute Command": f"R{i} exe", "RFID Reader 0 Memory Index": f"R{i} idx",
             "RFID Reader 0 Write Data": f"R{i} wr", "RFID Reader 0 Command ID": f"R{i} id", "RFID Reader 0 Status": f"R{i} st", "RFID Reader 0 Read Data": f"R{i} rd"}
        O.append(place("RFIDReader", x, y, z, yaw, names=n))
    scene(O, sys.argv[2], "RFID reader placement probe", camera=((24.5, 4.0, 19.5), (24.5, 0.3, 17.5)))
else:
    import fio_scene as F
    from pyModbusTCP.client import ModbusClient
    txt = F.load(sys.argv[2]); table = F.modbus_address_table(txt)
    A = {t["name"]: table[t["key"]] for t in F.tags(txt) if t["key"] in table}
    c = ModbusClient("127.0.0.1", 502)
    c.write_single_coil(table[re.search(r'RunOutputKey="([0-9a-f-]{36})"', txt).group(1)][1], 1); time.sleep(1)
    c.write_single_coil(A["R stop"][1], 1); c.write_single_coil(A["R conv"][1], 1)
    c.write_single_coil(A["R emit"][1], 1); time.sleep(0.3); c.write_single_coil(A["R emit"][1], 0)
    time.sleep(12); c.write_single_coil(A["R conv"][1], 0)
    res = []
    for i, (y, yaw, side) in enumerate(CASES):
        c.write_single_register(A[f"R{i} cmd"][1], 0); c.write_single_register(A[f"R{i} idx"][1], 0)
        cid = c.read_input_registers(A[f"R{i} id"][1], 1)[0]
        c.write_single_coil(A[f"R{i} exe"][1], 1); time.sleep(0.4); c.write_single_coil(A[f"R{i} exe"][1], 0); time.sleep(0.4)
        st = c.read_input_registers(A[f"R{i} st"][1], 1)[0]; cid2 = c.read_input_registers(A[f"R{i} id"][1], 1)[0]
        x = 190 + (i % 4) * 4; z = 140 + side if i < 8 else 140 - side
        res.append(f"R{i:02d} X={x} Y={y} Z={z} 방향 {yaw}: 상태 {st}{' (응답 없음)' if cid2 == cid else ''}")
    print("\n".join(res))
