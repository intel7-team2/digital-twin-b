"""
Project B · 배터리 팩 후공정 v5 (4S 2×2 / 6S 2×3, 18650 3.7V) · Python 가상 계측 엔진(검사기 2대) + 공유 DB

전처리(Project C)와 Project B는 **같은 DB(공유 DB)**를 씁니다.
  Project C 가 기록  : packs (팩 종류 · 팩 전압 · Σ셀 · C 판정), cells (셀 ID · 슬롯 · 극성 · 셀 전압)
  Project B 가 기록  : measurements, results (팩 계측 · 최종 판정 · 보관 중 발열 격리)
  공통 키            : PACK ID (하우징 ID, 정수 1~32767) = RFID 태그 idx0 = PLC D1516
셀 정보는 태그가 아니라 DB에만 있습니다. 팩 RFID를 찍어 PACK ID를 얻으면 그 키로 셀 이력을 조회합니다.

팩 종류 (Factory I/O 공작물)
  4S  2×2  셀 4개  Small box  공칭 14.8 V
  6S  2×3  셀 6개  Large box  공칭 22.2 V
  셀 규격: 18650 3.7 V (공칭). 판정 기준은 셀 1개 기준 × 셀 수.

검사기 2대 (v4 구조 B)
  station 1 = 메인 검사기   : RFID②(D1520~D1527) → 요청 D1710~D1714 → 결과 D1700~D1703
  station 2 = 재검사 검사기 : RFID③(D1530~D1537) → 요청 D1740~D1744 → 결과 D1730~D1733
  두 검사기 모두 팩 OCV(ΔV) · AC-IR · 온도를 잽니다. 핸드셰이크를 따로 두어 동시에 요청해도 충돌하지 않습니다.
  RFID가 태그 idx0(PACK ID) · idx4(재검사) · idx9(셀 수)를 읽으면 PLC가 요청 블록에 넘기고,
  엔진은 공유 DB에서 팩 종류를 확인한 뒤 팩 ΔV · 팩 AC-IR · 온도를 난수 생성해 판정을 회신하고 DB에 저장합니다(측정 스테이션 포함).
  측정은 팩 단자 2점(+/−) 기준이라 셀별 불량은 가려내지 않습니다. NG 팩은 NG 라인 배출로 프로젝트 범위가 끝납니다.
  (셀별 측정은 범위 밖에서 사람이 한다는 가정이며, 이 엔진에는 포함하지 않습니다.)

판정 기준 (셀 기준: ΔV PASS ≤ 80 mV / RETEST ≤ 150 mV, IR PASS ≤ 2.50 mΩ / RETEST ≤ 3.20 mΩ · 시연값)
               팩 ΔV PASS / RETEST / NG          팩 IR PASS / RETEST / NG
  4S          ≤ 0.320 / ≤ 0.600 / > 0.600 V     ≤ 10.00 / ≤ 12.80 / > 12.80 mΩ
  6S          ≤ 0.480 / ≤ 0.900 / > 0.900 V     ≤ 15.00 / ≤ 19.20 / > 19.20 mΩ
  온도        PASS ≤ 38.0 °C / NG > 38.0 °C (공통)
판정 코드: 1 PASS / 2 RETEST / 3 NG-ΔV / 4 NG-IR / 5 NG-TEMP (우선순위 Temp → ΔV → AC-IR)
  메인 검사의 2·3·4·5는 모두 M1720으로 아래 재검사 라인(정치 없이 연속 → 재검사기)에 갑니다(v5: M1710 삭제, v6: 정치 버퍼 삭제).
  재검사기는 RETEST(2)만 다시 재고, 이미 NG(3·4·5)인 팩은 재지 않고 2차 분리에서 NG OUT으로 보냅니다.
  원인은 DB의 ng_cause 로만 구분합니다.

보관 중 발열 격리 (station 0)
  랙 보관 중 가상 온도 초과 → 크레인 B가 정상 팩과 같은 출구로 내보냄 → 1차 분리(Pop-up Wheel Sorter)에서 아래로 격리.
  PLC가 격리 알림 블록(D1650~D1653)에 PACK ID · 온도를 쓰면 엔진이 results 에 ISO(발열 격리)로 기록합니다.

공유 DB
  경로: --db 옵션 > 환경변수 PROJECT_DB > inspection.db
  SQLite WAL 모드 + busy_timeout 으로 C/B 프로그램이 같은 파일을 동시에 씁니다.
  SQLite 파일은 한 PC의 로컬 디스크에 두고 그 PC에서 C/B 프로그램을 돌리는 구성을 전제로 합니다
  (네트워크 공유 폴더 위의 SQLite는 잠금이 불안정 → 그 경우 서버 DB로 이전 필요).

사용법
  python measurement_engine.py handoff --count 20     # Project C 인계(팩 + 셀) 모사 → 공유 DB 기록
  python measurement_engine.py demo --count 20 --db   # 인계 + 계측/판정까지 저장 (PLC 없이)
  python measurement_engine.py lookup --pack 17       # 팩 RFID 조회: 셀 + C 데이터 + B 판정
  python measurement_engine.py lookup --cell CELL-00017B   # 셀 ID로 소속 팩 역조회
  python measurement_engine.py report                 # 양품 · 원인별 불량 · 발열 격리 · 팩 종류별
  python measurement_engine.py isolate --pack 9 --temp 412   # 발열 격리 기록 모사 (PLC 알림 대신)
  python measurement_engine.py stats --count 10000 --cells 6
  python3.12-32 measurement_engine.py serve           # PLC 핸드셰이크 + DB 저장 (기본: MX OPC Server, 장치 QSIM)
  python measurement_engine.py serve --link modbus --host 192.168.0.214   # Modbus TCP 직접 (시연 PC = 이 PC, A21)

PLC 통신 (plc_link.py, 결정 D17)
  기본은 MX OPC Server(OPC DA) 경유입니다. GX Simulator2(또는 실물 PLC) ↔ MX OPC Server ↔ 이 엔진.
  OPC DA 가 32비트 COM 이라 serve 만 **32비트 Python + pywin32** 로 실행합니다(나머지 명령은 64비트도 됨).
  MX OPC Configurator 에 디바이스 이름 그대로의 태그(D1700 …)가 등록돼 있어야 합니다 → tools/mxopc_tags.py

serve 모드 핸드셰이크 (검사기마다 같은 순서, 번지는 STATIONS 에서 PLC 매핑에 맞게 수정)
  0) PLC: 검사기 RFID로 idx0(PACK ID) · idx4(재검사) · idx9(셀 수) 판독
  1) PLC: 요청 블록 +1 ← PACK ID, +2 ← 재검사, +4 ← 셀 수(4/6) 기록 후 +0 (MEAS_REQ) = 1
  2) 엔진: 공유 DB에서 팩 종류 확인 → 결과 블록(판정 · ΔV · IR · 온도) 기록 → DB 저장 → +3 (MEAS_DONE) = 1
  3) PLC: 값 읽고 태그 idx4~8 기록, MEAS_REQ = 0, 판정으로 분기
       메인: 1 GOOD 직진 / 2·3·4·5 → M1720 → 재검사 라인 (줄이 분기점까지 차면 M1800 → 메인 검사기 출구에서 대기)
       재검사: 2차 분리 Pop-up Wheel Sorter — 1 GOOD 위(M1731) → X1903 간격 확인 후 메인 라인 합류 / 3·4·5 아래(M1732) → NG OUT
  4) 엔진: MEAS_DONE = 0
  발열 격리 알림: PLC D1651 ← PACK ID, D1652 ← 온도(0.1 °C), D1650 = 1 → 엔진 DB 기록 → D1653 = 1 → PLC D1650 = 0 → 엔진 D1653 = 0
"""

import argparse
import math
import os
import random
import sqlite3
import sys
import time
from datetime import datetime

# ---------------------------------------------------------------------------
# 계측 분포 / 판정 기준  (v7.html · 3d_layout.html 의 MEAS 와 반드시 같은 값 유지)
# 셀 1개 기준 분포를 셀 수만큼 키워 팩 값으로 씀. 카테고리 확률은 셀 기준과 같음.
# ---------------------------------------------------------------------------
SEED_BASE = 20261118
CELL_DV = {"good": (20, 80, 0.82), "warn": (81, 150, 0.12), "ng": (151, 250)}     # mV / 셀
CELL_IR = {"good": (150, 250, 0.85), "warn": (251, 320, 0.10), "ng": (321, 450)}  # 0.01 mΩ / 셀
TEMP = {"good": (240, 380, 0.95), "ng": (381, 450)}                               # 0.1 °C (팩 최고)
TEMP_NG = 380

# 팩 종류 (Factory I/O 공작물)
PACK_TYPES = {
    4: {"name": "4S", "layout": "2x2", "box": "SMALL", "fio": "Small box"},
    6: {"name": "6S", "layout": "2x3", "box": "LARGE", "fio": "Large box"},
}

# Project C 인계 데이터 모사 (실제로는 C 라인이 공유 DB에 기록)
SEED_C = 20261028
SHARE_6S = 0.30                    # 모사 투입 비율: 6S 30% / 4S 70%
SLOT_NAMES = "ABCDEF"              # 슬롯 A·C·E = + 위, B·D·F = − 위 (직렬 교차)
CELL_MV = (3650, 3750)             # 18650 3.7 V 공칭 부근 (시연값)
PACK_ERR_MV = 30                   # C 팩 전압 − Σ셀 차이 범위 ±30 mV (C 허용 ±100 mV 안)

PASS, RETEST, NG_DV, NG_IR, NG_TEMP = 1, 2, 3, 4, 5
VERDICT_NAME = {PASS: "PASS", RETEST: "RETEST", NG_DV: "NG-DV", NG_IR: "NG-IR", NG_TEMP: "NG-TEMP"}
NG_CAUSE = {NG_DV: "DV", NG_IR: "IR", NG_TEMP: "TEMP"}  # DB ng_cause 값
CAUSE_LABEL = {"DV": "ΔV", "IR": "AC-IR", "TEMP": "온도"}
DEFAULT_DB = os.environ.get("PROJECT_DB", "inspection.db")
SCHEMA_VERSION = 5  # 1 셀 단위, 2 4S 팩, 3 4S/6S, 4 측정 스테이션, 5 보관 중 발열 격리(ISO · station 0)

# PLC 디바이스 매핑 (D 번호). plc_link.py 가 OPC 태그(QSIM.D1700) 또는 Modbus 주소(1700)로 바꿉니다.
# 디바이스 번지: 1500~19FF 블록 사용 (M·D는 10진 1500~1999, X·Y는 16진 1500~19FF)
# 검사기별 블록: result = 판정·ΔV·IR·온도 4워드 시작, req = 요청·PACK ID·재검사·완료·셀 수 5워드 시작
STATIONS = {
    1: {"name": "메인 검사", "result": 1700, "req": 1710},    # D1700~D1703 / D1710~D1714 (RFID② D1520~D1527)
    2: {"name": "재검사",    "result": 1730, "req": 1740},    # D1730~D1733 / D1740~D1744 (RFID③ D1530~D1537)
}
REQ, PACK, RETEST_CNT, DONE, CELLS = 0, 1, 2, 3, 4          # 요청 블록 안의 오프셋
ISO_BLOCK = 1650                                              # D1650 요청 · D1651 PACK ID · D1652 온도(0.1 °C) · D1653 완료
STATION_NAME = {0: "발열 격리", 1: "메인 검사", 2: "재검사"}    # 0 = 랙 보관 중 (검사기 아님)
REG = {  # 메인 검사기 이름표 (이전 코드·문서와 호환)
    "VERDICT": 1700, "DV": 1701, "IR": 1702, "TEMP": 1703,
    "MEAS_REQ": 1710, "MEAS_PACK_ID": 1711, "MEAS_RETEST": 1712, "MEAS_DONE": 1713, "MEAS_CELLS": 1714,
}

MASK = 0xFFFFFFFF


def _imul(a, b):
    return (a * b) & MASK


def mulberry32(seed):
    """JS mulberry32 와 비트 단위로 동일한 32-bit PRNG."""
    a = seed & MASK

    def rnd():
        nonlocal a
        a = (a + 0x6D2B79F5) & MASK
        t = _imul(a ^ (a >> 15), a | 1)
        t = ((t + _imul(t ^ (t >> 7), t | 61)) & MASK) ^ t
        return ((t ^ (t >> 14)) & MASK) / 4294967296

    return rnd


def pack_spec(cell_spec, n):
    """셀 기준 분포를 셀 n개 팩 분포로 변환 (구간 경계 × n)."""
    g, w, ng = cell_spec["good"], cell_spec["warn"], cell_spec["ng"]
    return {"good": (g[0] * n, g[1] * n, g[2]), "warn": (g[1] * n + 1, w[1] * n, w[2]), "ng": (w[1] * n + 1, ng[1] * n)}


# 11-27 A16(팀 결정): 실측값이 없어 판정 기준은 '18650 셀 가정값 × 셀 수'로 정함(아래 CELL_DV · CELL_IR · TEMP_NG).
# 6S는 셀 사이 연결부(니켈 스트립 · 용접) 저항이 더해지므로 IR 기준에 여유 10%를 둠(가정값, 실측이 생기면 이 표만 바꿈)
IR_LINK_MARGIN = {4: 1.00, 6: 1.10}


def limits(n):
    k = IR_LINK_MARGIN.get(n, 1.0)
    return {"dv_warn": CELL_DV["good"][1] * n, "dv_ng": CELL_DV["warn"][1] * n,
            "ir_warn": round(CELL_IR["good"][1] * n * k), "ir_ng": round(CELL_IR["warn"][1] * n * k), "temp_ng": TEMP_NG}


def _pick(rnd, spec):
    r = rnd()  # 카테고리용 1회 소비 (JS와 스트림 정렬)
    if r < spec["good"][2]:
        cat = "good"
    elif "warn" in spec and r < spec["good"][2] + spec["warn"][2]:
        cat = "warn"
    else:
        cat = "ng"
    lo, hi = spec[cat][0], spec[cat][1]
    return lo + math.floor(rnd() * (hi - lo + 1))


def measure(pack_id, retest_count=0, mode="id", n_cells=4):
    """PACK ID로 팩 계측값 생성. mode='id'는 재현 가능한 시드 난수, 'random'은 매번 새 난수."""
    if mode == "random":
        rnd = random.SystemRandom().random
    else:
        rnd = mulberry32(SEED_BASE + pack_id * 7919 + retest_count * 104729)
    return {"dv": _pick(rnd, pack_spec(CELL_DV, n_cells)),
            "ir": _pick(rnd, pack_spec(CELL_IR, n_cells)),
            "temp": _pick(rnd, TEMP)}


# 11-27 A2(팀 결정 ②): 랙 보관 중 이상 발열은 엔진이 PACK별로 정함(Factory I/O에는 온도 센서가 없음).
# 원래 설계대로 팩당 6% 확률로 이상 발열(41.0~45.0 °C), 그 밖은 25.0~35.0 °C. --mode id면 PACK ID 시드(재현), random이면 매번 새로
HOT_P, HOT_T, NORMAL_T = 0.06, (410, 450), (250, 350)


def storage_temp(pack_id, mode="id", forced=None):
    """보관 중 온도(0.1 °C)와 이상 발열 여부. forced = True/False면 시험용 지정(--hot-packs), None이면 6% 확률"""
    rnd = random.SystemRandom().random if mode == "random" else mulberry32(SEED_BASE + pack_id * 31337 + 17)
    r = rnd()
    hot = (r < HOT_P) if forced is None else forced
    lo, hi = HOT_T if hot else NORMAL_T
    return lo + math.floor(rnd() * (hi - lo + 1)), hot


def judge(m, retest_count=0, n_cells=4):
    L = limits(n_cells)
    if m["temp"] > L["temp_ng"]:
        return NG_TEMP
    if m["dv"] > L["dv_ng"]:
        return NG_DV
    if m["ir"] > L["ir_ng"]:
        return NG_IR
    dv_warn = m["dv"] > L["dv_warn"]
    ir_warn = m["ir"] > L["ir_warn"]
    if dv_warn or ir_warn:
        if retest_count >= 1:
            return NG_DV if dv_warn else NG_IR
        return RETEST
    return PASS


def fmt(m):
    return f"팩ΔV {m['dv'] / 1000:.3f}V · 팩IR {m['ir'] / 100:.2f}mΩ · T {m['temp'] / 10:.1f}°C"


def cell_id(pack_id, slot):
    """셀 ID 형식(모사). 실제 형식은 전처리 쪽 셀 ID 체계를 따름."""
    return f"CELL-{pack_id:05d}{slot}"


def c_handoff(pack_id):
    """Project C 가 PACK ID 하나에 대해 공유 DB에 쓰는 데이터 (v7.html makeHandoff 와 동일)."""
    rnd = mulberry32(SEED_C + pack_id * 7919)
    n = 6 if rnd() < SHARE_6S else 4
    cells = []
    for i, slot in enumerate(SLOT_NAMES[:n]):
        mv = CELL_MV[0] + math.floor(rnd() * (CELL_MV[1] - CELL_MV[0] + 1))
        cells.append({"cell_id": cell_id(pack_id, slot), "slot": slot,
                      "polarity": "+" if i % 2 == 0 else "-", "cell_mv": mv})
    sigma = sum(c["cell_mv"] for c in cells)
    pack_mv = sigma - PACK_ERR_MV + math.floor(rnd() * (2 * PACK_ERR_MV + 1))
    return {"pack_id": pack_id, "cell_count": n, "box": PACK_TYPES[n]["box"],
            "pack_mv": pack_mv, "sigma_mv": sigma, "c_result": "OK", "cells": cells}


# ---------------------------------------------------------------------------
# 공유 DB (SQLite)  — Project C 와 Project B 가 같은 파일을 씀
# ---------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS packs (                 -- Project C 기록
    pack_id       INTEGER PRIMARY KEY CHECK (pack_id BETWEEN 1 AND 32767),
    c_ts          TEXT    NOT NULL,
    cell_count    INTEGER NOT NULL CHECK (cell_count IN (4, 6)),        -- 4S 2x2 / 6S 2x3
    box           TEXT    NOT NULL CHECK (box IN ('SMALL', 'LARGE')),   -- Factory I/O Small / Large box
    pack_mv       INTEGER NOT NULL,                -- C R3 팩 전압
    sigma_mv      INTEGER NOT NULL,                -- C R1 셀 전압 합계
    c_result      TEXT    NOT NULL CHECK (c_result IN ('OK', 'NG'))
);
CREATE TABLE IF NOT EXISTS cells (                 -- Project C 기록
    cell_id       TEXT    PRIMARY KEY,             -- 전처리에서 받은 셀 ID
    pack_id       INTEGER NOT NULL REFERENCES packs (pack_id),
    slot          TEXT    NOT NULL CHECK (slot IN ('A', 'B', 'C', 'D', 'E', 'F')),
    polarity      TEXT    NOT NULL CHECK (polarity IN ('+', '-')),
    cell_mv       INTEGER NOT NULL,                -- C R1 셀 전압
    UNIQUE (pack_id, slot)
);
CREATE TABLE IF NOT EXISTS measurements (          -- Project B 기록
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            TEXT    NOT NULL,
    pack_id       INTEGER NOT NULL,
    station       INTEGER NOT NULL CHECK (station IN (0, 1, 2)),   -- 0 보관 중 발열 / 1 메인 검사 / 2 재검사
    cell_count    INTEGER NOT NULL,
    retest_count  INTEGER NOT NULL,
    dv_mv         INTEGER NOT NULL,
    ir_x100       INTEGER NOT NULL,
    temp_x10      INTEGER NOT NULL,
    verdict       INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS results (               -- Project B 기록
    pack_id       INTEGER PRIMARY KEY,
    ts            TEXT    NOT NULL,
    station       INTEGER NOT NULL CHECK (station IN (0, 1, 2)),   -- 최종 판정을 낸 곳 (0 = 보관 중 발열 격리)
    cell_count    INTEGER NOT NULL,
    result        TEXT    NOT NULL CHECK (result IN ('GOOD', 'NG', 'ISO')),   -- ISO = 보관 중 발열 격리
    ng_cause      TEXT             CHECK (ng_cause IN ('DV', 'IR', 'TEMP')),
    verdict       INTEGER NOT NULL,
    retest_count  INTEGER NOT NULL,
    dv_mv         INTEGER NOT NULL,
    ir_x100       INTEGER NOT NULL,
    temp_x10      INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS rfid_failures (         -- Project B 기록 (11-27, A11): RFID 판독 실패 팩. PACK ID를 몰라 results 에는 못 남김
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            TEXT    NOT NULL,
    station       INTEGER NOT NULL CHECK (station IN (1, 2, 3)),   -- RFID ① 입고 / ② 메인 검사 / ③ 재검사
    status        INTEGER,                         -- 리더 상태: 0 정상 1 태그 없음 2 태그 여러 개 3 주소 오류 4 명령 오류
    serial        INTEGER,                         -- 이번 팩 태그 시리얼(못 읽었으면 NULL)
    note          TEXT
);
CREATE TABLE IF NOT EXISTS storage_heat (          -- Project B 기록 (11-27, A2): 랙 보관 중 온도(가상). 팩이 랙에 들어갈 때 엔진이 정함
    pack_id       INTEGER PRIMARY KEY,
    ts            TEXT    NOT NULL,
    temp_x10      INTEGER NOT NULL,                -- 0.1 °C
    hot           INTEGER NOT NULL,                -- 1 = 이상 발열 → PLC에 발열 접수(격리)
    forced        INTEGER NOT NULL DEFAULT 0       -- 1 = 시험용 지정(--hot-packs)
);
CREATE TABLE IF NOT EXISTS batches (               -- Project B 기록 (11-27, A9): 회차(C 인계 묶음)별 결과. 회차가 끝나면 한 줄
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            TEXT    NOT NULL,                -- 회차 끝(마지막 상자까지 셈 · 팔레타이저 빔) 시각
    pack_from     INTEGER NOT NULL,
    pack_to       INTEGER NOT NULL,
    packs         INTEGER NOT NULL,
    good          INTEGER NOT NULL,                -- PLC 카운터 D1900 · D1901 · D1902(HMI에 보이는 값)
    ng            INTEGER NOT NULL,
    iso           INTEGER NOT NULL,
    yield_x10     INTEGER NOT NULL                 -- D1904 = GOOD ÷ (GOOD + NG + 격리) × 1000 (A5: 발열 격리를 분모에 넣음)
);
CREATE INDEX IF NOT EXISTS idx_cells_pack ON cells (pack_id);
CREATE INDEX IF NOT EXISTS idx_meas_pack ON measurements (pack_id);
"""


def open_db(path=DEFAULT_DB):
    conn = sqlite3.connect(path, timeout=10)  # 다른 쪽(C/B)이 쓰는 중이면 최대 10초 대기
    ver = conn.execute("PRAGMA user_version").fetchone()[0]
    has_tables = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
    if has_tables and ver != SCHEMA_VERSION:
        conn.close()
        sys.exit(f"{path} 는 이전 형식(version {ver}) DB입니다. 다른 이름으로 옮긴 뒤 다시 실행하세요.")
    conn.execute("PRAGMA journal_mode = WAL")      # 읽기/쓰기 동시 접근
    conn.execute("PRAGMA busy_timeout = 10000")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    return conn


def now():
    return datetime.now().isoformat(timespec="seconds")


def save_handoff(conn, h):
    """Project C 인계 데이터 기록 (같은 PACK ID면 덮어씀). C 쪽 프로그램도 이 함수(또는 같은 SQL)를 씀."""
    conn.execute(
        "INSERT INTO packs (pack_id, c_ts, cell_count, box, pack_mv, sigma_mv, c_result) VALUES (?, ?, ?, ?, ?, ?, ?)"
        " ON CONFLICT(pack_id) DO UPDATE SET c_ts=excluded.c_ts, cell_count=excluded.cell_count, box=excluded.box,"
        " pack_mv=excluded.pack_mv, sigma_mv=excluded.sigma_mv, c_result=excluded.c_result",
        (h["pack_id"], now(), h["cell_count"], h["box"], h["pack_mv"], h["sigma_mv"], h["c_result"]),
    )
    conn.execute("DELETE FROM cells WHERE pack_id = ?", (h["pack_id"],))
    conn.executemany(
        "INSERT OR REPLACE INTO cells (cell_id, pack_id, slot, polarity, cell_mv) VALUES (?, ?, ?, ?, ?)",
        [(c["cell_id"], h["pack_id"], c["slot"], c["polarity"], c["cell_mv"]) for c in h["cells"]],
    )
    conn.commit()


def record(conn, pack_id, n_cells, retest_count, m, verdict, station=1):
    """계측 1건 저장. RETEST가 아니면 results 에 PACK ID별 최종 판정을 덮어씀(upsert)."""
    ts = now()
    conn.execute(
        "INSERT INTO measurements (ts, pack_id, station, cell_count, retest_count, dv_mv, ir_x100, temp_x10, verdict)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (ts, pack_id, station, n_cells, retest_count, m["dv"], m["ir"], m["temp"], verdict),
    )
    if verdict != RETEST:
        conn.execute(
            "INSERT INTO results (pack_id, ts, station, cell_count, result, ng_cause, verdict, retest_count,"
            " dv_mv, ir_x100, temp_x10) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(pack_id) DO UPDATE SET ts=excluded.ts, station=excluded.station, cell_count=excluded.cell_count,"
            " result=excluded.result, ng_cause=excluded.ng_cause, verdict=excluded.verdict,"
            " retest_count=excluded.retest_count, dv_mv=excluded.dv_mv, ir_x100=excluded.ir_x100,"
            " temp_x10=excluded.temp_x10",
            (pack_id, ts, station, n_cells, "GOOD" if verdict == PASS else "NG", NG_CAUSE.get(verdict), verdict,
             retest_count, m["dv"], m["ir"], m["temp"]),
        )
    conn.commit()


def record_isolation(conn, pack_id, temp_x10):
    """보관 중 발열 격리 1건 저장 (station 0, 판정 5 · 결과 ISO). 계측값은 온도만 있음."""
    info = pack_info(conn, pack_id)
    n_cells = info[0] if info else 4
    ts = now()
    conn.execute(
        "INSERT INTO measurements (ts, pack_id, station, cell_count, retest_count, dv_mv, ir_x100, temp_x10, verdict)"
        " VALUES (?, ?, 0, ?, 0, 0, 0, ?, ?)",
        (ts, pack_id, n_cells, temp_x10, NG_TEMP),
    )
    conn.execute(
        "INSERT INTO results (pack_id, ts, station, cell_count, result, ng_cause, verdict, retest_count,"
        " dv_mv, ir_x100, temp_x10) VALUES (?, ?, 0, ?, 'ISO', 'TEMP', ?, 0, 0, 0, ?)"
        " ON CONFLICT(pack_id) DO UPDATE SET ts=excluded.ts, station=0, result='ISO', ng_cause='TEMP',"
        " verdict=excluded.verdict, retest_count=0, dv_mv=0, ir_x100=0, temp_x10=excluded.temp_x10",
        (pack_id, ts, n_cells, NG_TEMP, temp_x10),
    )
    conn.commit()
    return info is not None


def record_rfid_failure(conn, station, status, serial, note):
    """RFID 판독 실패 1건 저장 (A11). PACK ID는 몰라 태그 시리얼 · 리더 상태로 남김"""
    conn.execute("INSERT INTO rfid_failures (ts, station, status, serial, note) VALUES (?, ?, ?, ?, ?)",
                 (now(), station, status, serial, note))
    conn.commit()


def pack_info(conn, pack_id):
    return conn.execute(
        "SELECT cell_count, box, pack_mv, sigma_mv, c_result, c_ts FROM packs WHERE pack_id = ?", (pack_id,)
    ).fetchone()


def pack_cells(conn, pack_id):
    return conn.execute(
        "SELECT cell_id, slot, polarity, cell_mv FROM cells WHERE pack_id = ? ORDER BY slot", (pack_id,)
    ).fetchall()


def summary(conn):
    """양품 · NG 합계 · 원인별 · 발열 격리 · 팩 종류별 (팩 기준)."""
    s = {"GOOD": 0, "NG": 0, "ISO": 0, "DV": 0, "IR": 0, "TEMP": 0, "4S": 0, "6S": 0}
    for result, cause, n_cells, n in conn.execute(
        "SELECT result, ng_cause, cell_count, COUNT(*) FROM results GROUP BY result, ng_cause, cell_count"
    ):
        s[result] += n
        s[PACK_TYPES[n_cells]["name"]] += n
        if cause and result == "NG":      # 원인별 수량은 검사 NG만 (발열 격리는 ISO로 따로)
            s[cause] += n
    return s


# ---------------------------------------------------------------------------
# CLI 모드
# ---------------------------------------------------------------------------
def cmd_handoff(args):
    conn = open_db(args.db)
    types = {4: 0, 6: 0}
    for pid in range(args.start, args.start + args.count):
        h = c_handoff(pid)
        types[h["cell_count"]] += 1
        save_handoff(conn, h)
    print(f"[C → 공유 DB] PACK {args.start}~{args.start + args.count - 1} · 4S {types[4]}팩 / 6S {types[6]}팩"
          f" · 셀 {types[4] * 4 + types[6] * 6}개 → {args.db}")
    conn.close()


def run_pack(pid, mode, conn=None, out=print):
    h = c_handoff(pid)
    n = h["cell_count"]
    if conn:
        save_handoff(conn, h)
    rc = 0
    while True:
        m = measure(pid, rc, mode, n)
        v = judge(m, rc, n)
        station = 1 if rc == 0 else 2
        if v == PASS:
            route = "GOOD OUT" if rc == 0 else "2차 분리 위 → 합류 → GOOD OUT"
        elif v == RETEST:
            route = "M1720 → 재검사 라인 → 재검사기"
        else:
            route = (f"M1720 → 재검사 라인 → 재검사기 통과 → 2차 분리 아래 → NG OUT (원인 {NG_CAUSE.get(v)})" if rc == 0
                     else f"2차 분리 아래 → NG OUT (원인 {NG_CAUSE.get(v)})")
        out(f"PACK-{pid:04d} {PACK_TYPES[n]['name']} {rc:>2}  {m['dv']:>6} {m['ir']:>10} {m['temp']:>8}  "
            f"{VERDICT_NAME[v]}({v}) [{STATIONS[station]['name']}] → {route}")
        if conn:
            record(conn, pid, n, rc, m, v, station)
        if v == RETEST and rc == 0:
            rc = 1
            continue
        return v


def cmd_demo(args):
    conn = open_db(args.db) if args.db else None
    print(f"{'PACK':>9} 종류 {'RC':>2}  {'ΔV(mV)':>6} {'IR(0.01mΩ)':>10} {'T(0.1°C)':>8}  판정 → 배출")
    for pid in range(args.start, args.start + args.count):
        run_pack(pid, args.mode, conn)
    if conn:
        print()
        print(f"[DB] {args.db} 저장 완료 → python measurement_engine.py lookup --pack {args.start} --db {args.db}")
        conn.close()


def print_lookup(conn, pack_id):
    pack = pack_info(conn, pack_id)
    print(f"[RFID 조회] PACK-{pack_id:04d}")
    if pack is None:
        print("  C 인계 정보 없음 (공유 DB packs 테이블에 없음)")
    else:
        t = PACK_TYPES[pack[0]]
        print(f"  {t['name']} ({t['layout']}, {t['fio']}) · C 팩 {pack[2] / 1000:.3f}V · Σ셀 {pack[3] / 1000:.3f}V"
              f" · 차이 {(pack[2] - pack[3]) / 1000:+.3f}V · C 판정 {pack[4]} @ {pack[5]}")
    print(f"  {'슬롯':<4}{'극성':<4}{'셀 ID':<16}{'셀 전압':>8}")
    for cid, slot, pol, mv in pack_cells(conn, pack_id):
        print(f"  {slot:<5}{pol:<5}{cid:<16}{mv / 1000:>7.3f}V")
    res = conn.execute(
        "SELECT result, ng_cause, verdict, retest_count, dv_mv, ir_x100, temp_x10, ts, station FROM results WHERE pack_id = ?",
        (pack_id,),
    ).fetchone()
    if res is None:
        print("  B 판정: 아직 없음 (검사 전이거나 RETEST 대기)")
    elif res[0] == "ISO":
        print(f"  B 판정: ISO 보관 중 발열 격리 · 온도 {res[6] / 10:.1f}°C @ {res[7]}")
    else:
        print(f"  B 판정: {res[0]} {VERDICT_NAME[res[2]]}({res[2]}) 원인={CAUSE_LABEL.get(res[1], '-')} 재검사={res[3]}"
              f" · {STATION_NAME[res[8]]} · {fmt({'dv': res[4], 'ir': res[5], 'temp': res[6]})} @ {res[7]}")
    logs = conn.execute(
        "SELECT ts, retest_count, dv_mv, ir_x100, temp_x10, verdict, station FROM measurements WHERE pack_id = ? ORDER BY id",
        (pack_id,),
    ).fetchall()
    if logs:
        print("  계측 로그:")
        for ts, rc, dv, ir, t_, v, st in logs:
            if st == 0:
                print(f"    {ts}  {STATION_NAME[st]:<5} 보관 중 온도 {t_ / 10:.1f}°C → 격리")
            else:
                print(f"    {ts}  {STATION_NAME[st]:<5} RC={rc}  {fmt({'dv': dv, 'ir': ir, 'temp': t_})} → {VERDICT_NAME[v]}({v})")


def cmd_lookup(args):
    conn = open_db(args.db)
    if args.cell:
        row = conn.execute("SELECT pack_id FROM cells WHERE cell_id = ?", (args.cell,)).fetchone()
        if row is None:
            print(f"셀 {args.cell}: DB에 없음")
            conn.close()
            return
        print(f"셀 {args.cell} → PACK-{row[0]:04d}")
        print_lookup(conn, row[0])
    else:
        print_lookup(conn, args.pack)
    conn.close()


def cmd_isolate(args):
    conn = open_db(args.db)
    known = record_isolation(conn, args.pack, args.temp)
    print(f"[발열 격리 기록] PACK-{args.pack:04d} 온도 {args.temp / 10:.1f}°C → results ISO"
          + ("" if known else " (경고: 공유 DB에 C 인계 정보 없음)"))
    print_lookup(conn, args.pack)
    conn.close()


def cmd_report(args):
    conn = open_db(args.db)
    s = summary(conn)
    total = s["GOOD"] + s["NG"] + s["ISO"]
    n_packs = conn.execute("SELECT COUNT(*) FROM packs").fetchone()[0]
    n_cells = conn.execute("SELECT COUNT(*) FROM cells").fetchone()[0]
    print(f"[공유 DB] {args.db} · C 인계 팩 {n_packs}개 / 셀 {n_cells}개 · B 최종 판정 {total}팩 (4S {s['4S']} · 6S {s['6S']})")
    print(f"  양품 GOOD    {s['GOOD']:>6} 팩")
    print(f"  불량 NG      {s['NG']:>6} 팩")
    for key in ("DV", "IR", "TEMP"):
        print(f"    └ {CAUSE_LABEL[key]:<6} {s[key]:>6} 팩")
    print(f"  발열 격리 ISO {s['ISO']:>6} 팩   (보관 중, 검사 전)")
    n_fail = conn.execute("SELECT COUNT(*) FROM rfid_failures").fetchone()[0]
    if n_fail:                                        # 11-27(A11): PACK ID를 몰라 results 밖에 남긴 RFID 판독 실패
        print(f"  RFID 판독 실패 {n_fail:>5} 건  (PACK ID 모름 · rfid_failures 테이블, 태그 시리얼 기준)")
        for ts, st, stat, ser, note in conn.execute("SELECT ts, station, status, serial, note FROM rfid_failures ORDER BY id DESC LIMIT 5"):
            print(f"    └ {ts} RFID {'①②③'[st - 1]} 상태 {stat} 시리얼 {ser if ser is not None else '-'} · {note}")
    # 11-27 A2 · A9: 보관 온도(엔진이 정함) · 회차별 결과
    n_st, n_hot = conn.execute("SELECT COUNT(*), COALESCE(SUM(hot), 0) FROM storage_heat").fetchone()
    if n_st:
        print(f"  보관 온도    {n_st:>5} 팩 기록 · 이상 발열 {n_hot} 팩 (storage_heat 테이블)")
    for b in conn.execute("SELECT id, ts, pack_from, pack_to, packs, good, ng, iso, yield_x10 FROM batches ORDER BY id DESC LIMIT 5"):
        print(f"  회차 {b[0]:>3}  {b[1]}  PACK {b[2]}~{b[3]} ({b[4]}팩) · GOOD {b[5]} · NG {b[6]} · 격리 {b[7]} · 수율 {b[8] / 10:.1f}%")
    if total:
        print(f"  수율         {s['GOOD'] / total * 100:6.1f} %")
    print()
    print(f"최근 {args.limit}건 (셀 ID는 lookup --pack 으로 조회)")
    print(f"  {'PACK':>9} 종류 {'결과':<4} {'원인':<6} RC  계측값")
    for pid, n, res, cause, rc, dv, ir, t_ in conn.execute(
        "SELECT pack_id, cell_count, result, ng_cause, retest_count, dv_mv, ir_x100, temp_x10"
        " FROM results ORDER BY ts DESC, pack_id DESC LIMIT ?", (args.limit,)
    ):
        print(f"  PACK-{pid:04d} {PACK_TYPES[n]['name']}  {res:<4} {CAUSE_LABEL.get(cause, '-'):<6} {rc:>2}"
              f"  {fmt({'dv': dv, 'ir': ir, 'temp': t_})}")
    conn.close()


def cmd_stats(args):
    counts = {k: 0 for k in VERDICT_NAME}
    n = args.cells
    for pid in range(1, args.count + 1):
        v = judge(measure(pid, 0, n_cells=n), 0, n)
        if v == RETEST:
            v = judge(measure(pid, 1, n_cells=n), 1, n)  # 재검사 후 최종 판정
        counts[v] += 1
    total = args.count
    print(f"최종 판정 분포 ({PACK_TYPES[n]['name']} 기준, PACK 1~{total}, 재검사 반영)")
    for code, name in VERDICT_NAME.items():
        if code == RETEST:
            continue
        print(f"  {name:<8} {counts[code]:>6}  {counts[code] / total * 100:5.1f}%")


def cmd_serve(args):
    from plc_link import LinkError, open_link

    link = open_link(args)
    conn = open_db(args.db)
    print(f"[ENGINE] {link.label} 연결, {args.interval * 1000:.0f}ms 주기로 검사기 2대(D1710 · D1740) · 발열 격리(D1650) 요청 감시"
          f" · 난수 모드 {args.mode} · 공유 DB {args.db}")

    def read(addr, count=1):
        return link.read_words(f"D{addr}", count)

    def write(addr, values):
        link.write_words(f"D{addr}", values)

    # 11-26: MX OPC 캐시(--opc-source cache)는 쓴 값이 읽기에 늦게 보여, 완료를 쓴 직후에도 done = 0으로 읽혀
    # 같은 요청에 두 번 답함(DB 계측 기록 2줄) → 요청이 0으로 내려갈 때까지 다시 답하지 않음
    answered = set()

    def handle(st_no):
        st = STATIONS[st_no]
        base = st["req"]
        req, _, _, done = read(base, 4)
        if req == 0:
            answered.discard(st_no)
        if req == 1 and done == 0 and st_no not in answered:
            answered.add(st_no)
            pack_id, rc = read(base + PACK, 2)            # 검사기 RFID가 읽은 idx0 / idx4
            try:
                last_ok_serial[st_no + 1] = read(1558 if st_no == 1 else 1568)[0]   # A11: 이 팩의 정상 시리얼(다음 실패 판단용)
            except LinkError:
                pass
            tag_cells = read(base + CELLS)[0]             # 태그 idx9
            info = pack_info(conn, pack_id) if pack_id else None
            n = info[0] if info else (tag_cells if tag_cells in PACK_TYPES else 4)
            tag = f"[{st['name']}]"
            if pack_id == 0:
                print(f"{tag} 경고: PACK ID 0 (미등록 태그) 요청 → DB 기록 생략")
            elif info is None:
                print(f"{tag} 경고: PACK-{pack_id:04d} 공유 DB에 C 인계 정보 없음 → 태그 셀 수 {n}로 계측, 확인 필요")
            elif tag_cells != info[0]:
                print(f"{tag} 경고: PACK-{pack_id:04d} 태그 셀 수 {tag_cells} ≠ DB {info[0]} → DB 기준으로 계측")
            m = measure(pack_id, rc, args.mode, n)
            v = judge(m, rc, n)
            write(st["result"], [v, m["dv"], m["ir"], m["temp"]])   # 결과 블록 4워드 연속
            if pack_id != 0:
                record(conn, pack_id, n, rc, m, v, st_no)
            write(base + DONE, [1])
            cause = f" 원인={NG_CAUSE[v]}" if v in NG_CAUSE else ""
            print(f"{tag} PACK-{pack_id:04d} {PACK_TYPES[n]['name']} RC={rc} {fmt(m)} → {VERDICT_NAME[v]}({v}){cause}")
        elif req == 0 and done == 1:
            write(base + DONE, [0])

    # 11-27(A11): RFID 판독 실패 알람(M1952 ① · M1953 ② · M1954 ③)이 켜지는 순간 리더 상태와 태그 시리얼을 rfid_failures 에 남김.
    # 시리얼은 래더가 마지막으로 읽은 값(D1517 · D1558 · D1568). 직전 정상 팩의 값과 같으면 이번 팩 시리얼도 못 읽은 것 → NULL
    RFID_FAIL = {1: ("M1952", 1517, 1514), 2: ("M1953", 1558, 1524), 3: ("M1954", 1568, 1534)}
    fail_prev = {k: None for k in RFID_FAIL}
    last_ok_serial = {1: None, 2: None, 3: None}     # ② · ③은 검사 요청 때, ①은 알람이 없을 때 0.5초마다 갱신
    tick = [0]

    def handle_rfid_failures():
        tick[0] += 1
        if tick[0] % 5:                               # 알람은 리셋 전까지 켜져 있으므로 0.5초마다 봐도 충분(OPC 읽기 줄임)
            return
        for st, (bit, ser_addr, stat_addr) in RFID_FAIL.items():
            on = int(link.read(bit) or 0)
            if on and fail_prev[st] == 0:
                status = read(stat_addr)[0]
                serial = read(ser_addr)[0]
                if status == 1 or not serial:
                    rec, note = None, "태그 없음 · 시리얼 못 읽음"
                elif serial == last_ok_serial[st]:
                    rec, note = None, f"시리얼 못 읽음(직전 팩 값 {serial} 그대로)"
                else:
                    rec, note = serial, "시리얼은 읽음 · 데이터 판독 실패"
                record_rfid_failure(conn, st, status, rec, note)
                print(f"[RFID {'①②③'[st - 1]} 판독 실패] 상태 {status} · 시리얼 {rec} · {note} → DB rfid_failures")
            elif not on and st == 1:
                last_ok_serial[1] = read(ser_addr)[0]          # ①: 알람이 없을 때 본 시리얼 = 직전 팩 값(실패 순간 비교용)
            fail_prev[st] = on

    # 11-27 A2: 팩이 랙 칸에 들어가면(D1660+k = PACK ID, D1810+k = 넣은 시각) 보관 온도를 정해 DB에 남기고,
    # 이상 발열이면 PLC 발열 접수(D1697 칸 · D1698 온도 → M1672, 래더 H01이 받고 끔). 전에는 시험 도구가 계획의 'H'로 대신 함
    # --hot-packs를 주면(빈 값 '-' 포함) 그 팩만 이상 발열(시험 재현용), 안 주면 팩마다 6% 확률(시연 · A12 매번 다르게)
    hot_forced = None if args.hot_packs is None else {int(x) for x in args.hot_packs.replace(" ", "").split(",") if x.isdigit()}
    heat_done = {r[0] for r in conn.execute("SELECT pack_id FROM storage_heat")}
    heat_wait = []                                    # 접수 비트가 아직 켜져 있어 못 보낸 발열 (칸, 온도, PACK)

    def handle_storage():
        if tick[0] % 5 != 1 or args.no_storage_heat:
            return
        ids, ts_ = read(1660, 24), read(1810, 24)
        for k in range(24):
            pid = ids[k]
            if pid and ts_[k] and pid not in heat_done:
                t, hot = storage_temp(pid, args.mode, None if hot_forced is None else pid in hot_forced)
                conn.execute("INSERT OR REPLACE INTO storage_heat (pack_id, ts, temp_x10, hot, forced) VALUES (?, ?, ?, ?, ?)",
                             (pid, now(), t, int(hot), int(hot_forced is not None)))
                conn.commit()
                heat_done.add(pid)
                print(f"[보관] PACK-{pid:04d} 칸 {k + 1} 보관 온도 {t / 10:.1f}°C" + (" → 이상 발열(격리 대상)" if hot else ""))
                if hot:
                    heat_wait.append((k + 1, t, pid))
        if heat_wait and not int(link.read("M1672") or 0):
            slot, t, pid = heat_wait.pop(0)
            write(1697, [slot, t])
            link.write("M1672", 1)
            print(f"[발열 접수] PACK-{pid:04d} 칸 {slot} {t / 10:.1f}°C → PLC(M1672)")

    # 11-27 A9: 회차 = C 인계 묶음(공유 DB packs 중 아직 닫히지 않은 것). 그 팩이 모두 최종 판정 · 격리 기록을 받고,
    # PLC 카운터 합(D1903)이 팩 수에 닿고, 팔레타이저가 비면(D1918 = 0, 배치 끝 1개 팔레트까지 나감) 회차를 닫아 batches 에 한 줄.
    # 카운터는 HMI에 그대로 두었다가 다음 운전 시작(M1950 0 → 1) 때 엔진이 0으로(래더 R04 · R05가 합계 · 수율을 다시 셈)
    bstate = {"closed": False, "m1950": None}
    side_err = {}

    def handle_batch():
        if tick[0] % 5 != 3:
            return
        run = int(link.read("M1950") or 0)
        if bstate["closed"] and bstate["m1950"] == 0 and run == 1:
            write(1900, [0, 0, 0])
            bstate["closed"] = False
            bstate["base"] = (0, 0, 0)
            print("[회차] 운전 시작 → 카운터 D1900~D1902를 0으로(지난 회차는 batches 표에 있음)")
        bstate["m1950"] = run
        last_to = conn.execute("SELECT COALESCE(MAX(pack_to), 0) FROM batches").fetchone()[0]
        open_ids = [r[0] for r in conn.execute("SELECT pack_id FROM packs WHERE pack_id > ? ORDER BY pack_id", (last_to,))]
        if not open_ids:
            return
        judged_n = conn.execute(f"SELECT COUNT(*) FROM results WHERE pack_id IN ({','.join('?' * len(open_ids))})", open_ids).fetchone()[0]
        if judged_n < len(open_ids):
            return
        g, n, i, tot, y = read(1900, 5)
        # 11-28: 정지 없이 다음 회차로 이어지면 카운터가 0이 되지 않음(0은 다음 운전 시작 때) → 직전 회차를 닫을 때 값과의 차이로 셈.
        # 카운터가 기준보다 작아졌으면(HMI · 조작반 카운터 리셋) 기준을 0으로
        base = bstate.get("base", (0, 0, 0))
        if g < base[0] or n < base[1] or i < base[2]:
            base = bstate["base"] = (0, 0, 0)
        dg, dn, di = g - base[0], n - base[1], i - base[2]
        if dg + dn + di < len(open_ids) or read(1918)[0] != 0:
            return
        y = dg * 1000 // (dg + dn + di) if dg + dn + di else 0     # D1904와 같은 식(A5: 격리를 분모에 넣음), 이 회차분만
        g, n, i = dg, dn, di
        conn.execute("INSERT INTO batches (ts, pack_from, pack_to, packs, good, ng, iso, yield_x10) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                     (now(), open_ids[0], open_ids[-1], len(open_ids), g, n, i, y))
        conn.commit()
        bstate["closed"] = True
        bstate["base"] = (base[0] + dg, base[1] + dn, base[2] + di)
        print(f"[회차 끝] PACK {open_ids[0]}~{open_ids[-1]} · GOOD {g} · NG {n} · 격리 {i} · 수율 {y / 10:.1f}% → DB batches"
              " (카운터는 다음 운전 시작 때 0)")

    def handle_isolation():
        req, pack_id, temp_x10, done = read(ISO_BLOCK, 4)
        if req == 0:
            answered.discard("iso")
        if req == 1 and done == 0 and "iso" not in answered:
            answered.add("iso")
            if pack_id:
                known = record_isolation(conn, pack_id, temp_x10)
                print(f"[발열 격리] PACK-{pack_id:04d} 온도 {temp_x10 / 10:.1f}°C → DB ISO"
                      + ("" if known else " (경고: C 인계 정보 없음)"))
            else:
                print("[발열 격리] 경고: PACK ID 0 → DB 기록 생략")
            write(ISO_BLOCK + 3, [1])
        elif req == 0 and done == 1:
            write(ISO_BLOCK + 3, [0])

    # 11-26: 통신 오류(PLC 재시작 중 품질 불량 · MX OPC 재시작)로 끝나지 않고 2초마다 다시 시도
    # (전에는 여기서 종료돼, PLC를 다시 켠 뒤 serve를 안 띄우면 검사 요청에 답이 없어 라인이 검사기에서 멈춤)
    down = False
    try:
        while True:
            try:
                for st_no in STATIONS:
                    handle(st_no)
                handle_isolation()
                handle_rfid_failures()
                for _side in (handle_storage, handle_batch):   # 11-27: 보관 온도 · 회차는 부가 기능 — 한 번 읽기 오류로 검사 응답까지 재접속하지 않게
                    try:
                        _side()
                    except LinkError as _e:
                        if not side_err.get(_side.__name__):
                            print(f"[ENGINE] {_side.__name__} 읽기 실패(다음 주기에 다시): {_e}")
                        side_err[_side.__name__] = True
                    else:
                        side_err[_side.__name__] = False
                if down:
                    down = False
                    print("[ENGINE] 통신 복구")
            except (LinkError, OSError) as e:          # 11-27 검토: 닫힌 연결로 읽을 때의 OS 오류도 같은 재접속으로
                if not down:
                    down = True
                    print(f"[ENGINE] 통신 오류: {e} → 2초마다 다시 시도")
                answered.clear()                      # 답하던 중 끊겼을 수 있음 → 복구 뒤 같은 요청에 다시 답함
                time.sleep(2)
                try:
                    link.close()
                    link = open_link(args)
                except (Exception, SystemExit) as e2:  # 11-27 검토: 연결 실패의 sys.exit로 serve가 끝나지 않게
                    print(f"[ENGINE] 다시 연결 실패: {e2} → 2초 뒤 다시")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n[ENGINE] 종료")
    finally:
        link.close()
        conn.close()


def main():
    p = argparse.ArgumentParser(description="Project B 팩(4S/6S) STEP 03 Python 가상 계측 엔진 + 공유 DB")
    sub = p.add_subparsers(dest="cmd", required=True)
    db_help = "공유 DB 경로 (기본: 환경변수 PROJECT_DB 또는 inspection.db)"

    h = sub.add_parser("handoff", help="Project C 인계 데이터(팩 + 셀) 모사 → 공유 DB 기록")
    h.add_argument("--start", type=int, default=1)
    h.add_argument("--count", type=int, default=20)
    h.add_argument("--db", default=DEFAULT_DB, help=db_help)
    h.set_defaults(func=cmd_handoff)

    d = sub.add_parser("demo", help="PLC 없이 계측값/판정 출력")
    d.add_argument("--start", type=int, default=1)
    d.add_argument("--count", type=int, default=20)
    d.add_argument("--mode", choices=("id", "random"), default="id")
    d.add_argument("--db", nargs="?", const=DEFAULT_DB, default=None,
                   help="인계 데이터와 결과를 공유 DB에 저장 (경로 생략 시 기본 경로)")
    d.set_defaults(func=cmd_demo)

    lk = sub.add_parser("lookup", help="팩 RFID 조회: PACK ID → 셀 이력")
    g = lk.add_mutually_exclusive_group(required=True)
    g.add_argument("--pack", type=int, help="PACK ID")
    g.add_argument("--cell", help="셀 ID로 소속 팩 역조회")
    lk.add_argument("--db", default=DEFAULT_DB, help=db_help)
    lk.set_defaults(func=cmd_lookup)

    iso = sub.add_parser("isolate", help="보관 중 발열 격리 기록 (PLC 알림 모사)")
    iso.add_argument("--pack", type=int, required=True)
    iso.add_argument("--temp", type=int, default=400, help="온도 0.1 °C 단위 (예: 412 = 41.2 °C)")
    iso.add_argument("--db", default=DEFAULT_DB, help=db_help)
    iso.set_defaults(func=cmd_isolate)

    r = sub.add_parser("report", help="DB 집계: 양품 · 원인별 불량 · 발열 격리 · 팩 종류별")
    r.add_argument("--db", default=DEFAULT_DB, help=db_help)
    r.add_argument("--limit", type=int, default=10)
    r.set_defaults(func=cmd_report)

    s = sub.add_parser("stats", help="판정 비율 확인")
    s.add_argument("--count", type=int, default=10000)
    s.add_argument("--cells", type=int, choices=tuple(PACK_TYPES), default=4)
    s.set_defaults(func=cmd_stats)

    v = sub.add_parser("serve", help="PLC와 핸드셰이크 (기본 MX OPC Server, --link modbus 선택)")
    from plc_link import add_link_args
    add_link_args(v)
    v.add_argument("--interval", type=float, default=0.1)
    v.add_argument("--mode", choices=("id", "random"), default="id",
                   help="id: PACK ID 시드 난수(재현 가능, 시뮬레이터와 일치) / random: 매번 새 난수")
    v.add_argument("--db", default=DEFAULT_DB, help=db_help)
    v.add_argument("--hot-packs", default=None, help="A2 시험용: 이 PACK만 보관 중 이상 발열(예: 104 · 102,103 · '-' = 없음). 안 주면 팩마다 6%% 확률")
    v.add_argument("--no-storage-heat", action="store_true", help="보관 온도 · 발열 접수를 하지 않음(시험 도구가 대신할 때)")
    v.set_defaults(func=cmd_serve)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
