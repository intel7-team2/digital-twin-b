"""[래더 연결용 · 태그 이름 = PLC 번지 (D23, 11-23)] Project B v6 라인 — 중량물(롤러 · Chain Transfer · 곡선 롤러 · Roller Stop)로 통일한 2차 배치.
치수(실측): 롤러 2/4/6 m = 16/32/48칸(중심 기준, 폭 ≈8.6), Chain Transfer 8×8(중심), Loading Conveyor 길이 10,
곡선 롤러 16×16(중심), 방향 S의 입구 = +Z면(X−4 선) · +X면(Z−4 선). 모두 Y=2.
Chain Transfer: 방향 = 롤러(+)로 들어오는 진행 방향(반대쪽 끝에 고정 스토퍼), 체인 좌/우 = 진행 방향 기준 왼쪽(−Right)/오른쪽(Right).
사용: build_v6_roller.py <출력>"""
import re, sys, io, uuid
sys.path.insert(0, r"C:/Users/user/AppData/Local/Temp/claude/e8d7333cd358df48/2a20cd28-28b0-4a51-bdd3-4e3ff36dede8/scratchpad/work")
from fio_lib import place, scene, F
out = sys.argv[1]; O = []
FP = lambda o: o.replace("<FinePosition>0</FinePosition>", "<FinePosition>-0.0625</FinePosition>")
FPR = lambda o: re.sub(r'<Sensor Range="[^"]*"', '<Sensor Range="6"', FP(o))      # 견본(From A to B) 감지 거리 1 m → 반사판(1.25 m)까지 못 닿음
def roller(L, x, z, yaw, name): O.append(place(f"RollerConveyor{L}M", x, 2, z, yaw, names={"Entry conveyor": name, "Conveyor": name, "Box conveyor": name}))
def curve(x, z, yaw, name, ccw=False):
    """ccw=True: 반시계(−Z면으로 들어와 −X로 나가는 재검사 · NG 곡선). 기본 CW는 +Z면 → −X(메인 · GOOD)."""
    ex = (lambda o: o.replace('CurrentOperatingMode="0"', 'CurrentOperatingMode="1"').replace("_OM_CW_NAME", "_OM_CCW_NAME")) if ccw else None
    O.append(place("CurvedRollerConveyor", x, 2, z, yaw, names={"Curved Roller Conveyor 0 CW": name}, extra=ex))
CTN = {"CT1": ("Y1662", "Y1663", "Y1664", "X1662"), "CT2": ("Y1722", "Y1723", "Y1724", "X1723"), "CT3 merge": None,
       "CT3": ("Y1733", "Y1734", "Y1735", "X1733"), "CT4 wait": ("CT4 load", "Y1736", "CT4 right", "X1736"), "CT5 merge": ("Y1904", "CT5 left", "Y1905", "X1904"),
       "CTM corner": ("Y1665", "CTM left", "Y1666", "X1665"), "CTG corner": ("Y1706", "CTG left", "Y1707", "X1706"),
       "CTR corner": ("Y1806", "Y1807", "CTR right", "X1806")}
def ct(x, z, yaw, p):
    ld, lf, rt, sn = CTN[p]
    O.append(place("ChainTransfer", x, 2, z, yaw, src="Sorting by Height (Basic)",
                   names={"Load": ld, "Unload": f"{p} unload", "Transf. left": lf, "Transf. right": rt}))
    # 롤러 진행 방향 끝 4칸에 도착 센서(정전용량, 브래킷이 끝 막이 역할) — 예제 씬 Sorting by Height와 같은 배치
    fx, fz = {"W": (-1, 0), "E": (1, 0), "N": (0, -1), "S": (0, 1)}[yaw]
    syaw = {"W": "S", "E": "N", "N": "W", "S": "E"}[yaw]          # 센서 Right = −진행 방향(CT 쪽을 봄)
    O.append(place("CapacitiveSensor", x + 4 * fx, 5, z + 4 * fz, syaw, src="Sorting by Height (Basic)", names={"Loaded": sn}))
def rstop(x, z, yaw, name): O.append(place("RollerStop", x, 2, z, yaw, names={"Load stop": name}))
def retro(x, z, axis, name):
    """반사형 한 쌍(빔 높이 Y=5, 세밀 위치 −0.35). axis='X'면 X 방향 라인을 가로지름(센서 Z+4, 거울 Z−4)."""
    if axis == "X":
        O.append(place("RetroreflectivePhotoelectricSensor", x, 5, z + 5, "E", names={"Sensor": name}, extra=FPR))
        O.append(place("RetroreflectiveMirror", x, 5, z - 5, "E", extra=FP))
    else:
        O.append(place("RetroreflectivePhotoelectricSensor", x + 5, 5, z, "N", names={"Sensor": name}, extra=FPR))
        O.append(place("RetroreflectiveMirror", x - 5, 5, z, "N", extra=FP))
def rfid(x, z, yaw, base, y=4):
    n = {"RFID Reader 0 Command": f"D{base}", "RFID Reader 0 Execute Command": f"M{base+1}", "RFID Reader 0 Memory Index": f"D{base+1}",
         "RFID Reader 0 Write Data": f"D{base+2}", "RFID Reader 0 Command ID": f"D{base+3}", "RFID Reader 0 Status": f"D{base+4}", "RFID Reader 0 Read Data": f"D{base+5}"}
    O.append(place("RFIDReader", x, y, z, yaw, names=n))
_rm = [0]
def remover(x, z):
    _rm[0] += 1; O.append(place("Remover", x, 1, z, "S", names={"Remover": f"Remover {_rm[0]}"}))

# ---- 크레인 구간(F2t, 검증) ----
t2 = io.open(r"D:/seojung/digital-twin-b/factoryio_test/F2t_two_cranes_same.factoryio", encoding="utf-8-sig").read()
REN = {"Target Position": "D1601", "Forks Left": "Y1600", "Forks Right": "Y1601", "Lift": "Y1602", "Moving X": "X1600",
       "Moving Z": "X1601", "At Left": "X1602", "At Middle": "X1603", "At Right": "X1604",
       "Target Position B": "D1602", "Forks Left B": "Y1608", "Forks Right B": "Y1609", "Lift B": "Y160A", "Moving X B": "X1608",
       "Moving Z B": "X1609", "At Left B": "X160A", "At Middle B": "X160B", "At Right B": "X160C",
       "Load speed": "D1505", "Entry Conveyor": "Y1504", "At Load": "X1512", "At Entry": "X1513"}
for o in F.OBJ_RE.findall(t2):
    pn = re.search(r'PrefabName="([^"]+)"', o).group(1); x, y, z = re.search(r'<Position X="([^"]+)" Y="([^"]+)" Z="([^"]+)"', o).groups()
    if not ((pn == "StackerCrane") or (pn == "Rack" and z in ("163", "136")) or (pn == "LoadingConveyor" and x == "285") or
            (pn == "RollerConveyor2M" and x == "298") or (pn in ("RetroreflectivePhotoelectricSensor", "RetroreflectiveMirror") and x in ("281", "302"))):
        continue
    o = re.sub(r'Key="[0-9a-f-]{36}"', lambda m: f'Key="{uuid.uuid4()}"', o).replace('UseForcedValue="True"', 'UseForcedValue="False"')
    o = o.replace("<FinePosition>-0.35</FinePosition>", "<FinePosition>-0.0625</FinePosition>")
    for a, b in sorted(REN.items(), key=lambda kv: -len(kv[0])): o = re.sub(rf'(?<=\s)Name="{re.escape(a)}"', f'Name="{b}"', o)
    O.append(o)
O.append(place("LoadingConveyor", 246, 2, 184, "W", names={"Unload Conveyor": "Y1610"}, src="Automated Warehouse"))   # 247이면 크레인 B 몸체와 부딪힘(11-23 시험)
retro(243, 184, "X", "X1610")
# ---- 입고(Z=184, −X) ----
O.append(place("Emitter", 334, 6, 184, "W", names={"Emitter": "Y1500"}, src="Automated Warehouse",
               extra=lambda o: F.set_emitter(re.sub(r'UpTo="\d+"', 'UpTo="0"', o), ["BoxS"], ["SquarePallet"])[0]))
roller(2, 330, 184, "W", "Y1501")
roller(2, 314, 184, "W", "Y1501")
rstop(318, 184, "W", "Y1502")
retro(322, 184, "X", "X1510")
O.append(place("RetroreflectivePhotoelectricSensor", 322, 8, 189, "E", names={"Sensor": "X1511"}, extra=FPR)); O.append(place("RetroreflectiveMirror", 322, 8, 179, "E", extra=FP))   # 높이 센서: 가림 = Large (11-23 실측 BoxS ≤ Y7, BoxL ≤ Y8)
rfid(319, 189, "N", 1510)          # 옆 +Z 5칸 · Y=4 · 롤러 쪽을 봄. 위에 달면 박스가 걸려 떨어짐(11-23)
# ---- 출고 → CT1(1차 분리) ----
roller(2, 234, 184, "W", "Y1611")
retro(229, 184, "X", "X1660")
ct(222, 184, "W", "CT1")                     # 왼쪽(−Z) = 메인, 오른쪽(+Z) = 격리
roller(2, 222, 197, "S", "Y1690"); retro(222, 200, "Z", "X1902"); remover(222, 210)
# ---- 메인 ----  (11-23: 검사 전 경로의 곡선 롤러를 코너 CT로 바꿈. 곡선을 지나면 팔레트가 90° 돌아 박스 태그 면이 옆 → 앞/뒤로 가서
#                  옆에 단 RFID ② · ③이 못 읽음. 코너 CT는 팔레트 방향을 그대로 둠. 격자는 이음부가 맞게 다시 계산)
roller(2, 222, 171, "N", "Y1700")
ct(222, 159, "N", "CTM corner")              # 롤러(−Z)로 받아 체인 오른쪽(−X)으로
roller(4, 201, 159, "W", "Y1700")
rstop(189, 159, "W", "Y1701"); retro(193, 159, "X", "X1700"); rfid(190, 164, "N", 1520)
roller(2, 177, 159, "W", "Y1702")
retro(172, 159, "X", "X1720")
ct(165, 159, "W", "CT2")                     # M1720: 왼쪽(−Z) = GOOD, 오른쪽(+Z) = 재검사
# GOOD (CT2 → 코너 CTG → CT5)
roller(2, 165, 147, "N", "Y1703")
ct(165, 135, "N", "CTG corner")              # 롤러(−Z)로 받아 체인 오른쪽(−X)으로
roller(2, 153, 135, "W", "Y1703")
retro(147, 135, "X", "X1903")
ct(141, 135, "N", "CT5 merge")               # 재검사 GOOD은 롤러로 받아 체인 오른쪽(−X), 메인 GOOD은 체인으로 통과
roller(6, 113, 135, "W", "Y1900"); retro(93, 135, "X", "X1900"); remover(85, 135)
# 재검사 (CT2 → 코너 CTR → 재검사기 → CT3)
roller(2, 165, 172, "S", "Y1800")
retro(165, 175, "Z", "X1800")
ct(165, 184, "S", "CTR corner")              # 롤러(+Z)로 받아 체인 왼쪽(−X)으로
roller(2, 153, 184, "W", "Y1800")
rstop(149, 184, "W", "Y1730"); retro(153, 184, "X", "X1730"); rfid(150, 189, "N", 1530)
retro(146, 184, "X", "X1731")
ct(141, 184, "W", "CT3")                     # 2차 분리: 왼쪽(−Z) = GOOD 합류 쪽, 오른쪽(+Z) = NG
roller(2, 141, 172, "N", "Y1731")
ct(141, 160, "W", "CT4 wait")                # 합류 대기(체인으로 통과)
roller(2, 141, 148, "N", "Y1731")
# NG (판독이 다 끝난 뒤라 곡선 그대로)
roller(2, 141, 196, "S", "Y1732")
curve(137, 211, "W", "Y1732", ccw=True)
roller(4, 113, 215, "W", "Y1901"); retro(101, 216, "X", "X1901"); remover(93, 215)
# ---- 조작반 ----
O.append(place("ElectricSwitchboard", 100, 12, 96, "W"))
O.append(place("EmergencyStopButton", 100, 13, 98, "W", names={"Emergency stop": "X1500"}))
O.append(place("StartPushButton", 101, 12, 98, "W", names={"Fill": "X1501", "Filling": "Y1693"}))
O.append(place("StopPushButton", 100, 12, 98, "W", names={"Discharge": "X1502", "Discharging": "stop lamp"}))
O.append(place("ResetPushButton", 99, 12, 98, "W", names={"Reset": "X1503", "Reset light": "reset lamp"}))
added = scene(O, out, "Project B v6 line (roller + chain transfer)", camera=((24.0, 34.0, 20.6), (24.0, 0.0, 20.5)))
print("부품", len(O), "· 연결", len(added))
