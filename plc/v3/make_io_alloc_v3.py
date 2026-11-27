"""
v3 래더 I/O 할당표 만들기 (11-27, 안건 A30)

래더 명령어 목록(plc/v3/ladder_mnemonic_v3.txt)에 실제로 나오는 번지를 모두 모아
뜻 · 출처 · 쓰는 프로그램 · MX OPC 등록 여부를 한 표로 만듭니다.
  - 설명 출처: Factory I/O 번지 안(computer_use/fio_io_map_v6.csv) → 내부 번지 배정(plc/ladder_alloc_v6.csv)
    → v3 스텝 릴레이(plc/v3/steps_relay_v3.md) → 이 파일의 V3_EXTRA(v3에서 더한 번지)
  - MX OPC 등록: test_results/MXOPC_B_v7c.mdb 태그 이름(computer_use/mxopc_db.py로 읽음, 없으면 빈칸)
사용:
  python plc/v3/make_io_alloc_v3.py          → plc/v3/io_alloc_v3.csv · plc/v3/io_alloc_v3.md
"""
import csv
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
MNEMONIC = os.path.join(HERE, "ladder_mnemonic_v3.txt")
FIO_MAP = os.path.join(ROOT, "computer_use", "fio_io_map_v6.csv")
ALLOC = os.path.join(ROOT, "plc", "ladder_alloc_v6.csv")
STEPS_MD = os.path.join(HERE, "steps_relay_v3.md")
MDB = os.path.join(ROOT, "test_results", "MXOPC_B_v7c.mdb")

# v3에서 더했거나 배정 초안 · 번지 안에 뜻이 없는 번지 (11-27 기준)
V3_EXTRA = {
    "M1745": "픽앤플레이스 스텝 U29: L 높이에 상자가 없어 M 높이로 더 내려감(11-26)",
    "M1958": "알람: 박스 벨트 상자 걸림 — 박스 벨트 단계 30초 초과(DRIVE Y06, 11-27)",
    "M1959": "HMI 알람 발생 중 = M1500 · M1800 · M1690 · M1951~M1958 중 하나(LAMP W07, 11-27)",
    "M1961": "초기화 요청: 랙 LOCK 일괄 해제, 정지 중이면 래더 초기화(HMI LOCK 해제 2초 · opc_reset.py). LAMP W06이 끔",
    "M1962": "초기화 중(Z01 결과 → Z02~Z06 초기화 회로, 11-26)",
    "M1960": "알람 확인(HMI 비트 셋 · 조작반 리셋 X1503 짧게). LAMP W04가 끔",
    "M1920": "카운터 리셋(HMI 2초 · 비트 셋, 조작반 리셋 X1503 2초). LAMP W05가 끔",
    "D1603": "크레인 A 목표 칸 보관(운전 중에만 D1601로 내보냄, 11-26)",
    "D1604": "크레인 B 목표 칸 보관(운전 중에만 D1602로 내보냄, 11-26)",
    "D1917": "픽앤플레이스 집기 높이 Z(L 750 → 없으면 M 980)",
    "D1918": "팔레타이저에 올린 상자 수(2개면 배출)",
    "T1577": "픽앤플레이스 L 높이 도착 뒤 상자 감지 확인 1.5초",
    "T1579": "조작반 리셋 X1503 2초 누름(카운터 리셋)",
    "T1580": "픽앤플레이스 M 높이 도착 뒤 1.5초",
    "T1581": "배치 끝: 상자 1개인 채 2층이 6분 쉬면 배출(O17, 11-27)",
    "T1582": "박스 벨트 상자 걸림 30초(Y06 → M1958, 11-27)",
    "T1583": "재검사 전 정치: RETEST 팩을 재검사기 스토퍼에서 20초(N10, 11-27 A22)",
    "T1525": "격리 기록 응답 대기 10초(넘으면 M1957)",
    "T1527": "메인 검사 응답 대기 10초(넘으면 M1955)",
    "T1531": "재검사 응답 대기 10초(넘으면 M1956)",
    "M1500": "비상정지 중(= NOT X1500) — 출력 차단 · 알람",
    "M1510": "C 인계 수신(PACK ID · 셀 수 · 팩 전압을 받으면 ON, 입고 RFID①이 처리)",
    "M1600": "크레인 A(입고면) 동작 중",
    "M1601": "크레인 B(출고면) 동작 중",
    "M1690": "보관 중 이상 발열 → 크레인 B 우선 인출 · 격리 · 칸 LOCK",
    "M1700": "메인 검사 프로브(검사 중)",
    "M1730": "재검사 프로브(검사 중)",
    "M1746": "구간 기억 비트 블록 시작(M1746~M1764: 팩이 어느 구간에 있는지 · 판정 넘김) — 초기화 때 함께 지움",
    "M1755": "메인 검사 RFID② 태그를 못 읽음(0 · 직전 시리얼 · 남은 셀 수 판정)",
    "M1766": "재검사 RFID③ 태그를 못 읽음",
    "M1800": "재검사 라인 만차(줄이 분기점까지 참) → GOOD 외 팩은 메인 검사 출구 대기",
    "M1980": "TT5 → E1 앞 구간 팩이 GOOD",
    "M1981": "E1에 실린 팩이 GOOD",
    "M1982": "픽앤플레이스가 집은 상자가 GOOD",
    "M1983": "방금 놓은 상자가 GOOD(박스 벨트 → 팔레타이저)",
    "M1984": "E1 앞 구간에 팩 1개(GOOD 직진 · 재검사 합류가 번갈아 들어감)",
    "D1516": "C 인계 PACK ID(입고 RFID①에 씀)",
    "D1517": "입고 RFID① 태그 시리얼",
    "D1518": "C 인계 셀 수(4/6) — 박스 크기 D1519와 대조",
    "D1526": "메인 검사 RFID②가 읽은 PACK ID",
    "D1527": "메인 검사 RFID②가 읽은 재검사 횟수",
    "D1536": "재검사 RFID③가 읽은 PACK ID",
    "D1537": "재검사 RFID③가 읽은 재검사 횟수",
    "D1600": "크레인이 다룰 랙 칸 번호(1~24)",
    "D1610": "칸별 LOCK 경과 시간 블록 시작(D1610~D1633, 24칸)",
    "D1650": "발열 격리 DB 기록 요청(PLC → Python)",
    "D1651": "발열 격리 PACK ID",
    "D1652": "발열 격리 가상 온도(0.1 °C)",
    "D1653": "발열 격리 기록 완료(Python → PLC)",
    "D1700": "메인 검사 판정(1 PASS · 2 RETEST · 3 NG-ΔV · 4 NG-IR · 5 NG-TEMP)",
    "D1701": "메인 검사 팩 ΔV(mV)",
    "D1702": "메인 검사 팩 IR(0.01 mΩ)",
    "D1703": "메인 검사 온도(0.1 °C)",
    "D1710": "메인 검사 요청(PLC → Python)",
    "D1711": "메인 검사 PACK ID",
    "D1712": "메인 검사 재검사 횟수",
    "D1713": "메인 검사 완료(Python → PLC)",
    "D1714": "메인 검사 셀 수(태그)",
    "D1730": "재검사 판정",
    "D1731": "재검사 팩 ΔV(mV)",
    "D1732": "재검사 팩 IR(0.01 mΩ)",
    "D1733": "재검사 온도(0.1 °C)",
    "D1740": "재검사 요청(PLC → Python)",
    "D1741": "재검사 PACK ID",
    "D1742": "재검사 재검사 횟수",
    "D1743": "재검사 완료(Python → PLC)",
    "D1744": "재검사 셀 수(태그)",
    "D1800": "재검사 라인 위 팩 수",
    "SM400": "항상 ON(특수 릴레이)",
    "SM402": "RUN 뒤 첫 스캔만 ON(특수 릴레이)",
    "SM412": "1초 클록(특수 릴레이)",
}

DEV = re.compile(r"\b(SM\d+|[XY][0-9A-F]{4}|[MDT]\d{4})(Z\d)?\b")


def load_fio():
    out = {}
    with io.open(FIO_MAP, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            d = r["번지"].strip()
            if d and d not in out:
                out[d] = (r["설명"].strip(), r.get("Factory I/O 태그", "").strip(), r["구분"].strip())
    return out


def load_alloc():
    out = {}
    with io.open(ALLOC, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            m = re.match(r"([MDT])(\d+)", r["배정(초안)"].strip())
            if not m:
                continue
            kind, start, n = m.group(1), int(m.group(2)), int(r["개수"] or 1)
            for k in range(n):
                out.setdefault(f"{kind}{start + k}", (r["내용"].strip(), r["자리 표시"].strip()))
    return out


def load_steps():
    out = {}
    for line in io.open(STEPS_MD, encoding="utf-8"):
        m = re.match(r"\|\s*(\w+)\s*\|\s*M(\d+)\s*\|", line)
        if m:
            out[f"M{m.group(2)}"] = m.group(1)
    return out


def load_opc():
    try:
        sys.path.insert(0, os.path.join(ROOT, "computer_use"))
        import mxopc_db as M
        out = M.run_vbs('Set r = cn.Execute("SELECT Name FROM MX_DataTagsRoot")\r\ns=""\r\nDo While Not r.EOF\r\n'
                        's = s & r("Name") & " "\r\nr.MoveNext\r\nLoop\r\nWScript.Echo s\r\n', MDB)
        return set(out.split())
    except Exception:
        return None


def step_group(name):
    groups = {"R": "RFID 명령 게이트", "I": "입고", "T": "TT1 · 1차 분리", "M": "TTM", "P": "TT5 합류", "Q": "TT3",
              "J": "메인 검사", "C": "입고 RFID①", "A": "크레인 A", "B": "크레인 B", "G": "격리 기록", "N": "재검사",
              "K": "TT2 분기", "E": "엘리베이터 E1", "H": "박스 벨트", "U": "픽앤플레이스", "L": "팔레타이저"}
    return groups.get(name[0], "")


def main():
    fio, alloc, steps, opc = load_fio(), load_alloc(), load_steps(), load_opc()
    used, prog, tuse = {}, "", {}
    for line in io.open(MNEMONIC, encoding="utf-8"):
        m = re.match(r";\s*@PROGRAM\s+(\w+)", line)
        if m:
            prog = m.group(1)
            continue
        if line.startswith(";") or not line.strip():
            continue
        for tm in re.finditer(r"OUT (T\d{4}) K(\d+)", line):
            rid = line.split()[0]
            tuse.setdefault(tm.group(1), (rid, f"{int(tm.group(2)) / 10:g}초"))
        for dm in DEV.finditer(line.split(";")[0]):
            d = dm.group(1)
            e = used.setdefault(d, {"progs": [], "index": False})
            if prog not in e["progs"]:
                e["progs"].append(prog)
            if dm.group(2):
                e["index"] = True

    def kind(d):
        if d.startswith("SM"):
            return "특수 릴레이"
        return {"X": "입력", "Y": "출력", "M": "내부 비트", "D": "데이터", "T": "타이머"}[d[0]]

    def key(d):
        order = {"X": 0, "Y": 1, "M": 2, "D": 3, "T": 4, "S": 5}
        num = int(d[2:]) if d.startswith("SM") else int(d[1:], 16 if d[0] in "XY" else 10)
        return order[d[0]], num

    rows, missing = [], []
    for d in sorted(used, key=key):
        e = used[d]
        if d in V3_EXTRA:
            desc, src = V3_EXTRA[d], "v3 추가"
        elif d in steps:
            desc, src = f"스텝 릴레이 {steps[d]} ({step_group(steps[d])})", "v3 스텝"
        elif d in fio:
            desc, src = fio[d][0] + (f" [Factory I/O: {fio[d][1]}]" if fio[d][1] else ""), f"번지 안({fio[d][2]})"
        elif d in alloc:
            desc, src = alloc[d][0], f"배정 초안 {alloc[d][1]}"
        elif d.startswith("T") and d in tuse:
            desc, src = f"{tuse[d][0]} 렁 타이머 {tuse[d][1]}", "v3 렁"
        else:
            desc, src = "", ""
            missing.append(d)
        if e["index"]:
            desc += " — 인덱스(Z)로 이어지는 블록의 시작 번지"
        reg = "" if opc is None else ("O" if d in opc else "")
        rows.append([kind(d), d, desc, src, " · ".join(e["progs"]), reg])

    head = ["구분", "번지", "뜻", "출처", "쓰는 프로그램", "MX OPC 등록"]
    with io.open(os.path.join(HERE, "io_alloc_v3.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(head)
        w.writerows(rows)
    cnt = {}
    for r in rows:
        cnt[r[0]] = cnt.get(r[0], 0) + 1
    md = ["# v3 래더 I/O 할당표 (11-27 확정, 안건 A30)", "",
          "> `python plc/v3/make_io_alloc_v3.py`가 래더 명령어 목록(`ladder_mnemonic_v3.txt`)에서 실제로 쓰는 번지를 모아 만듭니다. "
          "래더를 바꾸면 다시 실행하세요. 같은 내용의 CSV: `io_alloc_v3.csv`.", "",
          "- 확정 방식(11-27 사용자 지시): 11-20 배정 초안(`plc/ladder_alloc_v6.csv`)과 v3에서 더한 번지를 **그대로 확정**. 번지 범위는 1500~19FF(Factory I/O · HMI · Python과 같은 블록)",
          "- C 인계 값(`M1510` · `D1516` · `D1518` · 팩 전압)을 PLC에 쓰는 주체: **`measurement_engine.py serve`**로 정함 — 구현은 공유 DB 연결(A14) 때. 그 전까지는 시험 도구(`opc_outside.py`)가 대신 씀",
          "- MX OPC 등록 = `test_results/MXOPC_B_v7c.mdb`에 태그가 있음(HMI · Python이 읽고 쓰는 번지). 래더 안에서만 쓰는 번지는 등록하지 않음",
          "", "| 구분 | 개수 |", "|---|---|"] + [f"| {k} | {v} |" for k, v in cnt.items()] + ["", "| " + " | ".join(head) + " |",
                                                                                         "|" + "---|" * len(head)]
    md += ["| " + " | ".join(c.replace("|", "/") for c in r) + " |" for r in rows]
    io.open(os.path.join(HERE, "io_alloc_v3.md"), "w", encoding="utf-8", newline="\n").write("\n".join(md) + "\n")
    print(f"번지 {len(rows)}개 {cnt} → io_alloc_v3.csv · io_alloc_v3.md")
    if missing:
        print("뜻 없음:", " ".join(missing))


if __name__ == "__main__":
    main()
