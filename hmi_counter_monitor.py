"""
Project B v4 · 팩 후공정(4S/6S) · STEP 05 출하·배출 게이트 카운터 HMI 모니터 (Modbus TCP) + 팩 이력 DB 집계

실제 HMI(GOT 등)에 바인딩할 PLC 레지스터를 PC에서 읽어 확인하는 도구입니다.
  D1900 GOOD OUT / D1901 NG(메인 NG + 재검사 NG, 한 라인) / D1902 M1690 격리
  D1903 합계 / D1904 수율(0.1% 단위)   ·   M1920 리셋 비트
  (v5: 발열 격리도 공유 DB에 ISO로 기록되므로 D1902와 DB 격리 수를 대조합니다.)
  (v4: BYPASS 라인이 없어져 카운터가 5개로 줄었습니다. 재검사 GOOD도 GOOD OUT 게이트에서 셉니다.)

NG는 한 라인으로 배출하므로 PLC에는 원인별 카운터가 없습니다.
원인별 불량 수량(ΔV · AC-IR · 온도)은 measurement_engine.py 가 저장한 DB(inspection.db)에서 읽어 함께 표시합니다.
카운터 1 EA = 팩 1개(4S 셀 4개 / 6S 셀 6개). 팩별 셀 ID는 `python measurement_engine.py lookup --pack N` 으로 조회합니다.

사용법
  python hmi_counter_monitor.py --host 127.0.0.1 --port 502          # 1초마다 표시
  python hmi_counter_monitor.py --once                                # 한 번만 읽기
  python hmi_counter_monitor.py --reset                               # M1920 펄스(리셋, DB는 유지)
  python hmi_counter_monitor.py --demo                                # PLC 없이 표시 형식 확인
  python hmi_counter_monitor.py --db inspection.db                    # 공유 DB 경로 (기본: 환경변수 PROJECT_DB 또는 inspection.db)

레지스터/코일 번호는 PLC 기종의 Modbus 매핑에 맞게 아래 값을 수정하세요.
"""

import argparse
import os
import sys
import time

from measurement_engine import CAUSE_LABEL, DEFAULT_DB, _client_call, open_db, summary

COUNTER_BASE = 1900  # D1900 → holding register 1900 (0-based)
COUNTER_COUNT = 5    # D1900~D1904
RESET_COIL = 1920    # M1920 → coil 1920
LABELS = ["GOOD OUT", "NG OUT", "M1690 격리", "합계", "수율"]


def render(values, db=None):
    good, ng, m290, total, yld = values
    lines = [
        f"{'항목':<12}{'디바이스':>8}{'값':>10}",
        "-" * 30,
    ]
    for i, name in enumerate(LABELS):
        dev = f"D{COUNTER_BASE + i}"
        val = f"{values[i] / 10:.1f}%" if i == 4 else f"{values[i]} EA"
        lines.append(f"{name:<12}{dev:>8}{val:>10}")
    lines.append("-" * 30)
    lines.append(f"GOOD {good} / NG {ng + m290} (검사 NG {ng} + 발열 격리 {m290})")
    # PLC 계산값과 재계산값이 다르면 표시 (HMI 연동 검증용)
    calc_total = good + ng + m290
    calc_yld = (good * 1000 // calc_total) if calc_total else 0
    if (total, yld) != (calc_total, calc_yld):
        lines.append(f"[경고] PLC D1903/D1904({total}/{yld}) ≠ 재계산({calc_total}/{calc_yld})")

    if db is not None:
        lines.append("")
        lines.append("팩 이력 DB (PACK ID별 최종 판정)")
        lines.append("-" * 30)
        lines.append(f"{'GOOD':<12}{db['GOOD']:>18} EA")
        lines.append(f"{'NG 합계':<12}{db['NG']:>18} EA")
        for key in ("DV", "IR", "TEMP"):
            lines.append(f"  └ {CAUSE_LABEL[key]:<8}{db[key]:>18} EA")
        lines.append(f"{'발열 격리':<12}{db.get('ISO', 0):>18} EA")
        if db.get("ISO", 0) < m290:
            lines.append(f"[경고] PLC 격리 카운터 D1902({m290}) > DB 격리 기록({db.get('ISO', 0)}) → 격리 알림(D1650) 누락 의심")
        lines.append(f"{'팩 종류':<12}{'4S ' + str(db.get('4S', 0)) + ' / 6S ' + str(db.get('6S', 0)):>21}")
        # 게이트 카운터는 리셋되고 DB는 누적되므로, 리셋 이후로는 DB 쪽이 크거나 같아야 정상
        if db["NG"] < ng:
            lines.append(f"[경고] PLC NG 카운터 D1901({ng}) > DB NG 기록({db['NG']}) → DB 저장 누락 의심")
    return "\n".join(lines)


def read_db(path):
    if not os.path.exists(path):
        return None
    conn = open_db(path)
    try:
        return summary(conn)
    finally:
        conn.close()


def main():
    p = argparse.ArgumentParser(description="출하·배출 게이트 카운터 HMI 모니터")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=502)
    p.add_argument("--unit", type=int, default=1)
    p.add_argument("--interval", type=float, default=1.0)
    p.add_argument("--once", action="store_true")
    p.add_argument("--reset", action="store_true", help="M1920 리셋 펄스 전송")
    p.add_argument("--demo", action="store_true", help="PLC 없이 예시 값 표시")
    p.add_argument("--db", default=DEFAULT_DB, help="검사 이력 DB 경로 (없으면 DB 집계 생략)")
    args = p.parse_args()

    if args.demo:
        sample = [812, 152, 12]
        total = sum(sample)
        demo_db = {"GOOD": 812, "NG": 152, "DV": 64, "IR": 47, "TEMP": 41, "4S": 690, "6S": 274, "ISO": 12}
        print(render(sample + [total, sample[0] * 1000 // total], demo_db))
        return

    try:
        from pymodbus.client import ModbusTcpClient
    except ImportError:
        sys.exit("pymodbus 가 필요합니다: pip install pymodbus")

    client = ModbusTcpClient(args.host, port=args.port)
    if not client.connect():
        sys.exit(f"Modbus 연결 실패: {args.host}:{args.port}")

    try:
        if args.reset:
            for state in (True, False):
                rr = _client_call(client.write_coil, RESET_COIL, state, unit=args.unit)
                if rr.isError():
                    sys.exit(f"리셋 실패: {rr}")
                time.sleep(0.2)
            print("[HMI] M1920 리셋 펄스 전송 완료 (DB 이력은 유지)")
            return

        while True:
            rr = _client_call(client.read_holding_registers, COUNTER_BASE, count=COUNTER_COUNT, unit=args.unit)
            if rr.isError():
                sys.exit(f"읽기 실패: {rr}")
            print("\033[2J\033[H" if not args.once else "", end="")
            print(time.strftime("%H:%M:%S"), f"{args.host}:{args.port}")
            print(render(rr.registers, read_db(args.db)))
            if args.once:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        client.close()


if __name__ == "__main__":
    main()
