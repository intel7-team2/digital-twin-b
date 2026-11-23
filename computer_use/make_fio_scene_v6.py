"""Project B v6 Factory I/O 씬 만들기 (상면도 layout/factoryio_topview_v6.png 기준).

python computer_use/make_fio_scene_v6.py            → factoryio_test/ProjectB_v6.factoryio (드라이버 MX OPC, CSIM.<번지>)
                                                       factoryio_test/ProjectB_v6_mb.factoryio (Modbus TCP Server, 크레인 시험용)
                                                       factoryio_test/ProjectB_v6_demo.factoryio (PLC 없이 흐름 보기: 컨베이어 · 분기 강제값)

배치 원칙
- 좌표 1u = 0.125 m, 정수만. 흐름 = +X(동쪽). Factory I/O에서 +X로 흐를 때 오른쪽 = -Z.
- AS/RS(랙 · 크레인 A/B · 입고점 · 출고점)는 Factory I/O 기본 씬 "Automated Warehouse"의
  크레인 ↔ 랙(10u) ↔ 로딩 컨베이어(옆 9u, 통로 끝 38u) 거리를 그대로 씀.
  - 크레인 B = 기본 씬 크레인 위치 · 방향 그대로(랙 서쪽 10u), 출고점 = 기본 씬 Load Conveyor 자리.
  - 크레인 A = 기본 씬 크레인을 랙 축 기준 180° 돌린 것(랙 동쪽 10u), 입고점 = 기본 씬 Load Conveyor를 180° 돌린 자리.
  - 랙 2개(3열 × 6단 중 아래 4단 사용 = 6열 × 4단, A27) = 두 크레인에게 모두 "입출고점에서 가까운 두 칸" 자리.
  → 포크 길이 · 높이 · 랙 깊이가 기본 씬과 같아 포크가 랙 기둥 · 컨베이어에 부딪히지 않음.
  팩은 Pallet 위에 싣고 다님(포크는 팔레트 밑으로 들어감, F2d: 팔레트 + Large box가 Pop-up Wheel을 지나감).
- 안전 펜스: AS/RS 구역 안쪽 펜스(기본 씬과 같은 X 간격, 컨베이어가 지나는 곳은 SafeguardI) + 라인 전체 바깥 펜스(출입구 1곳).
- 태그 이름 = PLC 번지(computer_use/fio_io_map_v6.csv). 번지가 없는 I/O는 설명 이름(연결 안 함).
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fio_build as fb  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE.parent / "factoryio_test"
IO_CSV = HERE / "fio_io_map_v6.csv"
WH = "Automated Warehouse"
SW = "Sorting by Weight"
SS = "Sorting Station"
OX = -60                      # 전체를 서쪽으로 (씬 가운데 쪽으로)
# 크레인 A(기본 씬을 180° 돌린 것) + 입고 라인 X 보정. 랙은 돌리지 않아(크레인 B와 같이 씀)
# 랙 기준점이 깊이 가운데가 아니면 크레인 A 쪽에서만 팔레트 깊이가 어긋남 → 시험으로 맞춘 값
import os
DXA = int(os.environ.get("FIO_DXA", "-1"))   # 크레인 A + 입고 라인
DXB = int(os.environ.get("FIO_DXB", "-1"))   # 크레인 B + 출고점
# 11-23 시험: A만 -2 → 랙 안 팔레트가 A 쪽으로 치우쳐 B가 들다 떨어뜨림, A +2 → 주행 막힘, A 0 → 랙 보에 걸림.
# A -1 · B -1 → 랙 안 팔레트 중심이 두 크레인에게 같아 입고 · 출고 모두 정상
RF_OFF = int(os.environ.get("FIO_RF_OFF", "4"))    # RFID 리더: 라인 중심에서 거리(u)
RF_Y = int(os.environ.get("FIO_RF_Y", "5"))        # RFID 높이 (사용자 맞춤 Y5, 프레임 위)
RF_DX = int(os.environ.get("FIO_RF_DX", "-2"))     # 정위치 센서 기준: 막대에 선 팔레트 가운데 (막대 5u 앞)
RF_FROT = os.environ.get("FIO_RF_FROT", "-89.75396")   # RFID FineRotation (사용자 맞춤)
RF_FPOS = os.environ.get("FIO_RF_FPOS", "-0.025")     # RFID FinePosition (사용자 맞춤)
RF_DIR = int(os.environ.get("FIO_RF_DIR", "1"))    # 1 = 앞면이 라인 쪽 (반대면 Status 1, 11-23 시험)
RS_Y = int(os.environ.get("FIO_RS_Y", "3"))        # Roller Stop 높이: Y3 = 내리면 롤러 높이 · 올리면 롤러 위 (11-23 화면 확인)
RS_DX = int(os.environ.get("FIO_RS_DX", "3"))      # Roller Stop 흐름 방향 보정 (사용자 맞춤 +3)
SEN_Y = int(os.environ.get("FIO_SEN_Y", "5"))     # 롤러 옆 확산 센서 높이 (기본 씬 Converge Station과 같음. Y4는 빔이 팔레트 밑으로 지나감, 11-23)
RS_FPOS = os.environ.get("FIO_RS_FPOS", "0")      # Roller Stop FinePosition (미세 위치)
RS_ROT = int(os.environ.get("FIO_RS_ROT", "0"))    # 0 = 막대가 흐름을 가로지름 (1은 흐름과 나란해 막지 못함, 11-23 화면 확인)
H1511 = int(os.environ.get("FIO_H1511", "5"))      # 높이 센서 높이 (사용자 맞춤 Y5)
BR_Y = int(os.environ.get("FIO_BR_Y", "9"))        # 비전 Bracket 높이 (사용자 맞춤 Y9, 비전 Y13)
OUT_DIRECT = int(os.environ.get("FIO_OUT_DIRECT", "0"))  # 1 = 출고점 = 벨트(포크가 바로 내려놓음)
CURVE_MODE = os.environ.get("FIO_CURVE_MODE", "1")      # 곡선 롤러 동작 모드 (0 CW · 1 CCW 추정)
BELT_DY = int(os.environ.get("FIO_BELT_DY", "-1"))  # 출고 뒤 벨트 · Pop-up · 센서 높이 보정
USE_POPUP = int(os.environ.get("FIO_POPUP", "0"))  # 1 = 분기에 Pop-up Wheel Sorter (사용자 결정 11-23), 0 = Chain Transfer
PU_Y = int(os.environ.get("FIO_PU_Y", "4"))        # 롤러 라인 사이 Pop-up 높이 (벨트 Y3 ↔ Pop-up Y5 관계를 롤러 Y2에 맞춤)

LEN = {"BeltConveyor2M": 16, "BeltConveyor4M": 32, "BeltConveyor6M": 48, "RollerConveyor2M": 16,
       "RollerConveyor4M": 32, "LoadingConveyor": 10, "PopUpWheelSorter": 8}
YB, YR = 3, 2                 # 벨트 · 롤러 높이
ZI, ZM, ZR = 115, 184, 160    # 입고 라인 · 메인 라인 · 재검사 라인


class V6:
    def __init__(self, demo=False):
        self.s = fb.Scene()
        self.demo = demo
        self._dx = 0
        self._dy = 0

    # ------------------------------------------------------------ 기본 놓기
    def put(self, prefab, scene, x, y, z, fwd, names=None, force=None, nth=0):
        o = fb.template(prefab, scene, nth=nth)
        for e in o.iter("Object"):
            e.set("GroupKey", "00000000-0000-0000-0000-000000000000")
        o.set("GroupKey", "00000000-0000-0000-0000-000000000000")
        if prefab.startswith(("Safeguard", "ElectricSwitchboard", "StartPush", "StopPush", "ResetPush",
                              "EmergencyStop", "DigitalDisplay", "VisualStatus", "AlarmSiren")):
            dy = 0
        else:
            dy = self._dy
        return self.s.add(o, (x + OX + self._dx, y + dy, z), fwd, names, force)

    def conv(self, prefab, x, z, fwd, tag, scene=SW):
        y = YR if prefab.startswith(("Roller", "Loading")) else YB
        src = {"BeltConveyor2M": (SW if prefab != "BeltConveyor2M" else SW), }.get(prefab, scene)
        src = {"BeltConveyor2M": SW, "BeltConveyor4M": SW, "BeltConveyor6M": "Separating Station",
               "RollerConveyor2M": WH, "RollerConveyor4M": "Converge Station", "LoadingConveyor": WH}[prefab]
        force = {0: "True"} if self.demo else None
        return self.put(prefab, src, x, y, z, fwd, [tag], force)

    def sensor(self, x, z, side, tag, y=None, belt=True):
        """side: 라인 중심에서 센서 쪽 단위벡터 (nx, nz). 빔 = 반대쪽(가로질러)."""
        nx, nz = side
        fwd = (nz, -nx)
        y = y if y is not None else (8 if belt else SEN_Y)     # 롤러 옆: 빔이 팔레트 높이로 지나게
        off = 4                                            # 프레임에 붙는 거리(기본 씬 Converge · Sorting by Weight 모두 4u)
        return self.put("DiffusePhotoelectricSensor", SW, x + nx * off, y, z + nz * off, fwd, [tag])

    def popup(self, x, z, fwd, left, right, forward, force=None):
        f = dict(force or {})
        return self.put("PopUpWheelSorter", SW, x, 5, z, fwd, [left, right, forward],
                        {i: "True" for i in f} if f else None)

    def ct(self, x, z, fwd, names, force=None):
        """분기 · 모퉁이 · 합류. names = (+) 직진, (-), (Left), (Right) — Chain Transfer 기준 이름.
        USE_POPUP이면 같은 자리에 Pop-up Wheel Sorter(태그 Send left · Send right · Send forward)로 놓음."""
        if not USE_POPUP:
            # 태그 순서 그대로: 3번째 (Left) = 흐름 기준 왼쪽(+Z), 4번째 (Right) = 오른쪽(-Z)
            # (11-23 시험: Square Pallet로 확인. 긴 Pallet은 CT보다 길어 옆 이송이 안 되고 떨어짐)
            io = list(names)
            fmap = {0: 0, 1: 1, 2: 2, 3: 3}
            return self.put("ChainTransfer", "_parts", x, 2, z, fwd, io,
                            {fmap[i]: "True" for i in (force or {})} or None)
        fx, fz = fwd
        pnames = [names[2], names[3], names[0]]                    # left, right, forward
        pforce = {{0: 2, 2: 0, 3: 1}[i]: "True" for i in (force or {}) if i in (0, 2, 3)}
        # CT는 흐름 기준 앞 끝 -3 · 뒤 끝 +4, Pop-up은 ±4 → 가운데를 +1 옮겨 앞 컨베이어 끝에 맞춤
        return self.put("PopUpWheelSorter", SW, x + fx, PU_Y, z + fz, fwd, pnames, pforce or None)

    def stop(self, x, z, fwd, tag):
        """정지 위치. Stop Blade(경하중)는 내려도 팔레트를 막아(11-23 시험) Roller Stop(중하중)을 롤러 위에 씀."""
        fx, fz = fwd
        rfwd = (fz, -fx) if RS_ROT else fwd           # 막대가 흐름을 가로지르게 90° (11-23: 흐름 방향이면 팔레트가 지나감)
        fx2, fz2 = fwd
        o = self.put("RollerStop", "_parts", x + fx2 * RS_DX, RS_Y, z + fz2 * RS_DX, rfwd, [tag])
        o.find("Proxy").find("FinePosition").text = RS_FPOS
        return o

    def rfid(self, x, z, side, names, belt=False):
        nx, nz = side
        # 읽기 범위 0.5 m(4u): 컨베이어 프레임 바로 옆(5u), 롤러 높이에 붙임 (바닥 7u는 범위 밖이었음)
        fx, fz = (-nz, nx) if False else (abs(nz), abs(nx))   # 흐름 방향(+X 라인은 +X, +Z 라인은 +Z)
        o = self.put("RFIDReader", "_parts", x + nx * RF_OFF + fx * RF_DX, RF_Y + (1 if belt else 0), z + nz * RF_OFF + fz * RF_DX,
                     (RF_DIR * -nx, RF_DIR * -nz), names)
        # 사용자가 RFID ①을 편집 화면에서 맞춘 자세 (11-23 14:11 저장본): 프레임 위, 정위치 센서 7u 앞,
        # FineRotation -89.75 · FinePosition -0.025 · Rotation(Y -0.7056, W 0.7086). ② · ③도 같은 자세(+X 라인, -Z 쪽)
        px = o.find("Proxy")
        px.find("FineRotation").text = RF_FROT
        px.find("FinePosition").text = RF_FPOS
        if RF_FROT != "0":
            px.find("Rotation").attrib.update(X="0", Y="-0.7055868", Z="0", W="0.7086235")
        return o

    def remover(self, x, z, fwd, roller=False):
        # 벨트 위 Y9(Sorting by Weight), 롤러 위 Y6(Automated Warehouse)
        return self.put("Remover", WH if roller else SW, x, 6 if roller else 9, z, fwd, ["Remover"], {0: "True"})

    # ------------------------------------------------------------ 펜스
    def fence_wall(self, axis, fixed, a0, a1, crossings=(), fwd=None):
        """axis 'z': X = fixed 인 벽(Z 방향으로 a0..a1). crossings: 컨베이어가 지나는 좌표(SafeguardI)."""
        P = 17
        n = max(1, round((a1 - a0) / P))
        step = (a1 - a0) / n
        centers = [a0 + step * (i + 0.5) for i in range(n)]
        # 컨베이어가 지나는 칸은 가운데를 컨베이어에 맞춤
        cs = list(crossings)
        for c in cs:
            i = min(range(n), key=lambda k: abs(centers[k] - c))
            centers[i] = c
        for c in centers:
            kind = "SafeguardI" if any(abs(c - k) < 1e-6 for k in cs) else "SafeguardL"
            src = SW if kind == "SafeguardI" else WH
            if axis == "z":
                self.put(kind, src, fixed, 10, round(c), fwd or (0, 1))
            else:
                self.put(kind, src, round(c), 10, fixed, fwd or (1, 0))

    def fence_rect(self, x0, x1, z0, z1, cross=None, gaps=None):
        cross = cross or {}
        gaps = gaps or {}
        for side, axis, fixed, a0, a1 in (("W", "z", x0, z0, z1), ("E", "z", x1, z0, z1),
                                          ("N", "x", z0, x0, x1), ("S", "x", z1, x0, x1)):
            if side in gaps:          # 출입구: 그 구간을 비움
                g0, g1 = gaps[side]
                self.fence_wall(axis, fixed, a0, g0, cross.get(side, ()))
                self.fence_wall(axis, fixed, g1, a1, cross.get(side, ()))
            else:
                self.fence_wall(axis, fixed, a0, a1, cross.get(side, ()))

    # ------------------------------------------------------------ 씬
    def build(self):
        E, N, S_, W = (1, 0), (0, -1), (0, 1), (-1, 0)     # N = -Z(흐름 오른쪽), S_ = +Z
        d = self.demo

        # ---- 15 입고 · RFID ① (Z = 115, 동쪽으로) — 크레인 A와 같이 DXA만큼 옮김
        self._dx = DXA
        em = self.put("Emitter", "_parts", 182, 6, ZI, E, ["Y1500", "D1509", "D1508"],
                      {0: "True", 1: "2", 2: "5"} if d else None)
        emi = em.find("Emitter")
        if d:                                              # 데모: 강제 배출이라 간격을 둠 (PLC 씬은 1~2초)
            emi.set("MinTimeToEmit", "20"), emi.set("MaxTimeToEmit", "25")
        emi.find("Bases").attrib.clear(), emi.find("Bases").set("Pallet", "True")
        emi.find("Bases").set("SquarePallet", "True")   # Chain Transfer 옆 이송용 (긴 팔레트는 CT보다 길어 옆으로 안 감, 11-23)
        emi.find("Parts").attrib.clear(), emi.find("Parts").set("BoxS", "True"), emi.find("Parts").set("BoxL", "True")
        # 입고 라인은 Emitter부터 입고점까지 전부 롤러(중하중): 벨트 → 롤러 턱에서 팔레트가 걸려
        # 박스가 미끄러져 떨어짐(11-23 시험) → 턱을 없앰
        self.conv("RollerConveyor4M", 194, ZI, E, "Y1501")            # 178..210
        self.conv("RollerConveyor2M", 218, ZI, E, "Y1501")            # 210..226 RFID ① 정지 롤러
        # 비전 센서 타워(Bracket + Vision): 상면도대로 둠. 기본 높이(Bracket Y9)는 팔레트 위 Large box가 걸려
        # 박스가 긁혀 올라탐(11-23 시험) → BR_Y만큼 올림. 비전 값은 박스를 못 알아봄(A26)
        self.put("Bracket", SS, 194, BR_Y, ZI, W)
        self.put("VisionSensor", SS, 194, BR_Y + 4, ZI, S_, ["Vision sensor (D1519 아님, A26)"])
        # 높이 센서 X1511: 라인 옆 기둥에 담 (Large box만 가림, 11-23: Y8 = Large만 · Y9 = 둘 다 안 가림)
        self.put("Column", WH, 205, 8, ZI - 5, S_)
        self.sensor(204, ZI, (0, -1), "X1511", y=H1511, belt=False)
        self.sensor(223 + RS_DX - 3, ZI, (0, 1), "X1510", belt=False)  # RFID ① 정위치: Roller Stop 막대 3u 앞
        self.stop(223, ZI, E, "Y1502")
        self.rfid(223 + RS_DX - 3, ZI, (0, -1), ["M1511", "D1514", "D1513", "D1510", "D1515", "D1512", "D1511"])
        self.conv("RollerConveyor2M", 234, ZI, E, "Y1504")
        self.conv("LoadingConveyor", 247, ZI, E, "Y1505")              # 크레인 A 입고점
        # 입고점 도착: 기본 씬 "At Load"처럼 크레인 쪽 끝 1u 안(251). 켜지면 바로 Y1505 정지(래더 V02)
        # → 팔레트가 포크 가운데에 섬. 가운데(247)에 두고 더 돌리면 끝을 넘어 포크에서 기울어 박스가 떨어짐(11-23 시험)
        self.sensor(251, ZI, (0, 1), "X1512", belt=False)

        # ---- 16 AS/RS
        self.put("StackerCrane", WH, 256, 33, 153, (0, 1),
                 ["D1601", "X1600", "X1601", "X1602", "X1603", "X1604", "Y1600", "Y1601", "Y1602"])   # 크레인 A
        self._dx = 0
        for z in (136, 163):
            self.put("Rack", WH, 266, 25, z, (0, 1))
        self._dx = DXB
        self.put("StackerCrane", WH, 276, 33, 146, (0, -1),
                 ["D1602", "X1608", "X1609", "X160A", "X160B", "X160C", "Y1608", "Y1609", "Y160A"])   # 크레인 B
        if OUT_DIRECT:
            # 크레인 B가 포크로 벨트에 바로 내려놓음 (로딩 컨베이어 → 벨트 턱 없앰, 사용자 제안 11-23)
            self._dy = BELT_DY
            # 크레인 쪽 끝을 로딩 컨베이어 끝(280)에 맞춤: 2 m 벨트를 포크 자리 가운데에 두면 크레인 통로로
            # 3u 들어가 플랫폼과 부딪힘(11-23 시험) → 280..296, 포크 자리(285)는 벨트 위
            self.conv("BeltConveyor2M", 288, ZM, E, "Y1610")
            self.sensor(285, ZM, (0, 1), "X1610")
            self._dy = 0
        else:
            self.conv("LoadingConveyor", 285, ZM, E, "Y1610")          # 크레인 B 출고점
            self.sensor(285, ZM, (0, 1), "X1610", belt=False)
        self._dx = 0

        # ==== 출고 뒤 라인: 롤러 + Chain Transfer (중하중, 사용자 결정 11-23) ====
        # 시험 결과(11-23): 출고점(로딩 컨베이어) → 벨트 경계는 롤러 경유 · 직결 · 포크 직하 · 경사 벨트 모두 실패
        # (박스 낙하 또는 정체). 팔레트용 중하중 부품끼리는 높이가 맞아 박스가 떨어지지 않음.
        # Chain Transfer(CT) 간격(기본 씬 Converge Station): 흐름 기준 앞 컨베이어 끝 = CT - 3, 뒤 = CT + 4, 옆 = CT ± 4.5
        # 태그 순서: (+) 흐름 방향 굴림, (-) 반대, (Left) 올려 왼쪽 체인, (Right) 올려 오른쪽 체인

        # ---- 1차 분리 (CT1, 오른쪽 = -Z = 발열 격리)
        self.conv("RollerConveyor2M", 297, ZM, E, "Y1611")            # 289..305 (출고점 -1u에 맞춤)
        self.conv("RollerConveyor2M", 314, ZM, E, "Y1611")            # 306..322
        c1 = 325
        self.ct(c1, ZM, E, ["M1660", "CT1 (-)", "CT1 left (미사용)", "M1661"], force={0: 1} if d else None)
        self.sensor(c1 + 3, ZM, (0, 1), "X1660", belt=False)          # CT1 하류 끝: 팔레트 앞 끝이 닿으면 CT 가운데 (11-23)
        self.conv("RollerConveyor4M", c1, ZM - 21, N, "Y1690")         # 격리 라인 147..179
        self.sensor(c1, 160, (1, 0), "X1902", belt=False)              # Remover(152)보다 앞: 붙어 있으면 지워진 뒤라 신호 없음 (11-23)
        self.remover(c1, 152, N, roller=True)
        # 발열 경보: 격리 라인 옆 기둥 위 Stack Light, 기둥 옆 사이렌 (바닥에 두지 않음)
        self.put("Column", WH, c1 + 10, 8, 156, S_)
        self.put("VisualStatusIndicator", "_parts", c1 + 10, 16, 156, S_, ["Y1691", "Y1692", "Y1693"])
        self.put("AlarmSiren", "_parts", c1 + 11, 13, 156, E, ["Y1694"])

        # ---- 17 메인 검사 (RFID ②, Roller Stop Y1701)
        self.conv("RollerConveyor4M", 345, ZM, E, "Y1700")            # 329..361
        self.conv("RollerConveyor2M", 369, ZM, E, "Y1700")            # 361..377 정지 롤러
        self.sensor(374 + RS_DX - 3, ZM, (0, 1), "X1700", belt=False)  # Roller Stop 막대 3u 앞
        self.stop(374, ZM, E, "Y1701")
        self.rfid(374 + RS_DX - 3, ZM, (0, -1), ["M1521", "D1524", "D1523", "D1520", "D1525", "D1522", "D1521"])
        self.conv("RollerConveyor2M", 385, ZM, E, "Y1702")            # 377..393
        self.sensor(389, ZM, (0, 1), "X1720", belt=False)
        c2 = 396                                                       # M1720 분기 CT2 (오른쪽 = 재검사)
        self.ct(c2, ZM, E, ["M1720 CT (+) (번지 없음, A31)", "CT2 (-)", "CT2 left (미사용)", "M1720"],
                force={0: 1} if d else None)

        # ---- 18 재검사 라인 (연속, 정치 없음)
        # 모퉁이는 Curved Roller Conveyor (사용자 결정 11-23, 번지 안 Y1801 "재검사 라인 곡선").
        # 곡선 롤러(fwd +X) 실측(11-23 위에서 본 화면): 입구(남쪽에서 들어옴) = 기준점 + (-5, +7), 출구(동쪽) = + (7.6, -5.5)
        self.conv("RollerConveyor2M", c2, 172, N, "Y1800")            # 164..180
        self.sensor(c2, 176, (1, 0), "X1800", belt=False)
        self.sensor(c2, 168, (-1, 0), "X1801", belt=False)
        cx, cz = c2 + 4, 157                                           # 곡선 기준점: 입구를 들어오는 롤러 가운데에 맞춤 (+5는 1u 어긋나 팔레트가 걸림, 11-23 사용자 지적)
        cv = self.put("CurvedRollerConveyor", "_parts", cx, 2, cz, E, ["Y1801"], {0: "True"} if d else None)
        # 위에서 볼 때 반시계로 도는 모퉁이 → CCW 모드 (기본 CW면 팔레트를 입구로 되밀어 멈춤, 11-23)
        cv.find("ComponentIO").set("CurrentOperatingMode", CURVE_MODE)
        cv.find("OperatingMode").set("Description", "$C_CurvedRollerConveyor_OM_CCW_NAME" if CURVE_MODE == "1"
                                     else "$C_CurvedRollerConveyor_OM_CW_NAME")
        c3 = 153                                                       # 재검사 라인 Z (곡선 출구에 맞춤: 152는 1u 어긋나 팔레트가 걸림, 11-23)
        self.conv("RollerConveyor4M", 424, c3, E, "Y1801")            # 408..440
        self.conv("RollerConveyor2M", 448, c3, E, "Y1801")            # 440..456 재검사 정지 롤러
        self.sensor(453 + RS_DX - 3, c3, (0, -1), "X1730", belt=False) # Roller Stop 막대 3u 앞
        self.stop(453, c3, E, "Y1730")
        # 곡선 롤러를 지나 팔레트가 90° 돌아 박스 태그 면이 바뀜 → RFID ③은 +Z 쪽 (11-23)
        self.rfid(453 + RS_DX - 3, c3, (0, 1), ["M1531", "D1534", "D1533", "D1530", "D1535", "D1532", "D1531"])
        self.conv("RollerConveyor2M", 464, c3, E, "Y1801")            # 456..472
        self.conv("RollerConveyor2M", 472, c3, E, "Y1801")            # 464..480 (8u 겹침: CT5 앞 끝 맞춤)
        self.sensor(476, c3, (0, -1), "X1731", belt=False)
        c5 = 483                                                       # 2차 분리 CT5: 왼쪽(+Z) GOOD, 오른쪽(-Z) NG
        self.ct(c5, c3, E, ["Sorter2 CT (+) (미사용)", "CT5 (-)", "M1731", "M1732"], force={3: 1} if d else None)
        self.conv("RollerConveyor2M", c5, 165, S_, "Y1731")            # 157..173 → 메인 합류
        self.conv("RollerConveyor2M", c5, 172, S_, "Y1731")            # 164..180 (겹침)
        self.conv("RollerConveyor4M", c5, c3 - 21, N, "Y1732")         # NG 라인 115..147
        self.conv("RollerConveyor2M", c5, 107, N, "Y1901")             # NG OUT 99..115
        self.sensor(c5, 111, (1, 0), "X1901", belt=False)              # Remover(104)보다 앞
        self.remover(c5, 104, N, roller=True)

        # ---- 메인 GOOD (CT2 → 합류 CT4 → GOOD OUT)
        self.conv("RollerConveyor4M", 416, ZM, E, "Y1702")            # 400..432
        self.conv("RollerConveyor4M", 448, ZM, E, "Y1702")            # 432..464
        self.conv("RollerConveyor2M", 472, ZM, E, "Y1702")            # 464..480
        self.sensor(476, ZM, (0, 1), "X1903", belt=False)             # 합류 앞 간격
        self.ct(c5, ZM, E, ["Merge CT (+) (번지 없음, A31)", "CT4 (-)", "Merge CT left (번지 없음, A31)", "CT4 right"],
                force={0: 1} if d else None)
        self.conv("RollerConveyor4M", 503, ZM, E, "Y1900")            # 487..519
        self.sensor(505, ZM, (0, -1), "X1900", belt=False)            # Remover(514)보다 앞
        self.remover(514, ZM, E, roller=True)

        # ---- 조작반 (Sorting by Weight 조작반과 같은 배치)
        px, pz = 300, 214
        self.put("ElectricSwitchboard", SW, px, 12, pz, S_)
        self.put("EmergencyStopButton", SW, px + 2, 13, pz - 1, S_, ["X1500"], {0: "True"} if d else None)
        self.put("StartPushButton", SW, px + 2, 12, pz - 1, S_, ["X1501", "Start light"])
        self.put("StopPushButton", SW, px + 2, 12, pz, S_, ["X1502", "Stop light"])
        self.put("ResetPushButton", SW, px + 2, 12, pz + 1, S_, ["X1503", "Reset light"])
        for (y, dz), tag in zip([(11, -1), (11, 0), (11, 1), (10, -1), (10, 0)],
                                ["D1900", "D1901", "D1902", "D1903", "D1904"]):
            self.put("DigitalDisplay", SW, px + 2, y, pz + dz, S_, [tag])

        # ---- 안전 펜스
        # AS/RS 안쪽: 기본 씬(X 247..282, Z 75..224)과 같은 간격. 입고(Z 115) · 출고(Z 184)는 SafeguardI
        self.fence_rect(250, 282, 75, 224, cross={"W": [ZI], "E": [ZM]})
        # 라인 바깥 펜스: 조작반 앞(남쪽)에 출입구 1곳
        self.fence_rect(168, 530, 64, 232, gaps={"S": (292, 326)})
        return self

    def write(self, name, driver, current=1):
        cx, cz = (168 + 530) / 2 + OX, (64 + 232) / 2
        m = 0.125
        views = [("Overview", (cx * m, 32, (cz + 120) * m), (cx * m, 0, cz * m)),
                 ("AS/RS", ((205 + OX) * m, 12, 88 * m), ((262 + OX) * m, 2, 140 * m)),
                 ("Inspection", (420 * m + OX * m, 7, 215 * m), (430 * m + OX * m, 1, 175 * m)),
                 ("Top", (cx * m, 50, cz * m + 0.5), (cx * m, 0, cz * m))]
        opc = None
        if driver == "opc":
            opc = []
            for io in self.s.io_by_name():
                if io and io[0] in "XYMD" and io[1:].isalnum() and len(io) == 5:
                    kind = "Int" if io[0] == "D" else "Boolean"
                    opc.append((io, f"CSIM.{io}", kind))
        out = self.s.write(OUT_DIR / name, views, current=current, base=WH, opc_items=opc,
                           desc="Project B v6 (상면도 factoryio_topview_v6 기준) - 태그 이름 = PLC 번지")
        if driver == "modbus":
            import fio_scene as fs
            import re
            t = fs.load(str(out))
            # 기본 씬에서 따라온 Modbus 연결(지금 씬에 없는 태그 Key)을 지우고 새로 매김
            mb = fs.driver_block(t, "ModbusTCPServer")
            body = re.sub(r'\s*<(Bit|Numeric)(Input|Output)\d+ PointIOKey="[^"]*" />', "", mb.group(2))
            body = re.sub(r'(Bit|Numeric)(Input|Output)Count="\d+"', r'\1\2Count="0"', body)
            t = t[:mb.start(2)] + body + t[mb.end(2):]
            t, added = fs.map_modbus(t)
            fs.save(str(out), t)
        return out


def check_tags(scene: V6):
    want = {r["번지"] for r in csv.DictReader(IO_CSV.open(encoding="utf-8-sig")) if r["Factory I/O 태그"] != "–"}
    have = {n for n in scene.s.io_by_name() if n and len(n) == 5 and n[0] in "XYMD"}
    return sorted(want - have), sorted(have - want)


def main():
    v = V6().build()
    print("[저장]", v.write("ProjectB_v6.factoryio", "opc"))
    print("[저장]", V6().build().write("ProjectB_v6_mb.factoryio", "modbus", current=2))
    print("[저장]", V6(demo=True).build().write("ProjectB_v6_demo.factoryio", "modbus"))
    miss, extra = check_tags(v)
    print(f"부품 {len(v.s.objects)}개 · 번지 태그 {len(v.s.io_by_name())}개")
    print("CSV에 있으나 씬에 없는 번지:", miss)
    print("씬에만 있는 번지:", extra)


if __name__ == "__main__":
    main()
