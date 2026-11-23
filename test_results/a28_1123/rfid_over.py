"""라인 씬의 RFID① 자리(X=322, Z=184) 위에 높이별 리더 6개(Y=6~11)를 더해 만든 씬으로 s1 정지 후 판독.
사용: rfid_over.py build <원본> <출력> | rfid_over.py run <씬>"""
import sys, re, time, io
sys.path.insert(0, r"C:/Users/user/AppData/Local/Temp/claude/e8d7333cd358df48/2a20cd28-28b0-4a51-bdd3-4e3ff36dede8/scratchpad/work")
sys.path.insert(0, r"D:\seojung\digital-twin-b\computer_use")
YS = [(x, 4) for x in (317, 318, 319, 320, 321, 322)] + [(319, 3), (319, 5)]   # 옆 +Z 5칸 · 방향 N
if sys.argv[1] == "build":
    from fio_lib import place, F
    t = F.load(sys.argv[2]); objs = []
    for i, (lat, y) in enumerate(YS):
        n = {"RFID Reader 0 Command": f"P{i} cmd", "RFID Reader 0 Execute Command": f"P{i} exe", "RFID Reader 0 Memory Index": f"P{i} idx",
             "RFID Reader 0 Write Data": f"P{i} wr", "RFID Reader 0 Command ID": f"P{i} id", "RFID Reader 0 Status": f"P{i} st", "RFID Reader 0 Read Data": f"P{i} rd"}
        objs.append(place("RFIDReader", lat, y, 189, "N", names=n))
    for m in list(F.OBJ_RE.finditer(t)):                      # 원래 위에 단 RFID①은 치움(박스가 걸림)
        if 'PrefabName="RFIDReader"' in m.group(0) and 'X="322" Y="7"' in m.group(0):
            t = t.replace(m.group(0), m.group(0).replace('<Position X="322" Y="7" Z="184"', '<Position X="200" Y="0" Z="40"'), 1)
    last = list(F.OBJ_RE.finditer(t))[-1]
    t = t[:last.end()] + "".join("\n  " + o for o in objs) + t[last.end():]
    cnt = {}
    def renum(m):
        k = m.group(1); cnt[k] = cnt.get(k, -1) + 1
        return f'<{k} Name="{m.group(2)}" Address="{cnt[k]}"'
    t = re.sub(r'<((?:Binary|Int|Analogue)(?:Input|Output)) Name="([^"]*)" Address="-?\d+"', renum, t)
    t, _ = F.map_modbus(t)
    F.save(sys.argv[3], t)
else:
    import fio_scene as F
    from pyModbusTCP.client import ModbusClient
    txt = F.load(sys.argv[2]); table = F.modbus_address_table(txt)
    A = {t["name"]: table[t["key"]] for t in F.tags(txt) if t["key"] in table}
    c = ModbusClient("127.0.0.1", 502)
    c.write_single_coil(table[re.search(r'RunOutputKey="([0-9a-f-]{36})"', txt).group(1)][1], 1); time.sleep(1)
    for n in ("Y1501", "Y1501-2", "Y1502"): c.write_single_coil(A[n][1], 1)
    c.write_single_coil(A["Y1500"][1], 1); time.sleep(0.3); c.write_single_coil(A["Y1500"][1], 0)
    t0 = time.time()
    while c.read_discrete_inputs(A["X1510"][1], 1)[0] and time.time() - t0 < 20: time.sleep(0.05)
    time.sleep(1.5); print("X1510 가림" if not c.read_discrete_inputs(A["X1510"][1], 1)[0] else "X1510 안 가려짐")
    for y in range(len(YS)):
        p = f"P{y}"
        cmd, idx, exe, cid, st = ((f"{p} cmd", f"{p} idx", f"{p} exe", f"{p} id", f"{p} st") if p else ("D1510", "D1511", "M1511", "D1513", "D1514"))
        c.write_single_register(A[cmd][1], 0); c.write_single_register(A[idx][1], 0)
        a0 = c.read_input_registers(A[cid][1], 1)[0]
        c.write_single_coil(A[exe][1], 1); time.sleep(0.4); c.write_single_coil(A[exe][1], 0); time.sleep(0.4)
        print(f"리더 X·Y={YS[y]}: 상태 {c.read_input_registers(A[st][1], 1)[0]}{' (응답 없음)' if c.read_input_registers(A[cid][1], 1)[0] == a0 else ''}")
