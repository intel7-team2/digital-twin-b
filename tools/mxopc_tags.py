"""
MX OPC Server 태그 목록 (1500~19FF 블록, v5) 생성 · 변환 · 확인 도구

MX OPC 는 Configurator 에 등록된 태그만 읽고 쓸 수 있습니다(직접 번지 QSIM.D1700 → 0xC0040007).
Project B 는 **태그 이름 = 디바이스 이름**(D1700, M1920, X1900 …)으로 등록합니다. plc_link.py 가 이 이름을 씁니다.

1) 목록 보기 / 기본 CSV 만들기 (설치 불필요, 64비트 Python 도 됨)
     python tools/mxopc_tags.py                         # 화면에 목록
     python tools/mxopc_tags.py --csv tools/mxopc_tags_v5.csv

2) Configurator 가져오기(Import)용 CSV 만들기  ← 권장
   Configurator 의 CSV 열 구성은 버전마다 달라서, 실제 내보내기 파일을 견본으로 씁니다.
     ① MX OPC Configurator 에서 장치 QSIM 의 태그를 CSV 로 내보내기(Export) → 예: qsim_export.csv
     ② python tools/mxopc_tags.py --template qsim_export.csv --out qsim_import_v5.csv
        견본에서 워드 태그(D…) 1행과 비트 태그(M…/X…) 1행을 골라, 이름 · 디바이스 · 설명 칸만 바꿔 v5 태그를 만듭니다.
        (열 자동 인식이 틀리면 --name-col / --addr-col / --desc-col 로 열 번호(0부터) 지정)
     ③ Configurator 에서 qsim_import_v5.csv 가져오기(Import) → 저장 → MX OPC Server 재시작

3) 기존 3000번대 태그 번지 옮기기 (D9 블록 이동: 30xx→15xx, 32xx→16xx, 33xx→17xx, 34xx→18xx, 35xx→19xx)
     python tools/mxopc_tags.py --remap-old qsim_export.csv --out qsim_remap.csv
   이름은 그대로 두고 번지만 바꿉니다(기존 Factory I/O 씬의 OPC 연결 이름 유지).
   v5 에서 쓰지 않는 번지(BYPASS · M1710 등)는 목록으로 알려 줍니다.

4) 등록 확인 (MX OPC Server 가 있는 PC, 32비트 Python + pywin32)
     python3.12-32 tools/mxopc_tags.py --check            # 모든 v5 태그 AddItem + 읽기
"""

import argparse
import csv
import io
import os
import re
import sys

# (디바이스, 형식, 설명) — 형식: W = 16비트 워드(Short), B = 비트(Boolean)
TAGS = [
    # 15xx 입고 · RFID
    ("M1500", "B", "비상정지 (전 출력 차단)"),
    ("M1510", "B", "Project C 인계 수신"),
    ("D1510", "W", "RFID① 명령 (0 태그확인 1 시리얼 2 읽기 3 쓰기 4 지우기)"),
    ("M1511", "B", "RFID① 실행 펄스"),
    ("D1511", "W", "RFID① 메모리 주소 (0~127)"),
    ("D1512", "W", "RFID① 쓰기 데이터"),
    ("D1513", "W", "RFID① 명령 ID"),
    ("D1514", "W", "RFID① 상태 (0 정상)"),
    ("D1515", "W", "RFID① 읽은 데이터"),
    ("D1516", "W", "PACK ID (1~32767)"),
    ("D1517", "W", "태그 시리얼"),
    ("D1518", "W", "DB 셀 수 (4 = 4S, 6 = 6S)"),
    ("D1519", "W", "비전 박스 크기"),
    ("D1520", "W", "RFID② 명령"),
    ("M1521", "B", "RFID② 실행 펄스"),
    ("D1521", "W", "RFID② 메모리 주소"),
    ("D1522", "W", "RFID② 쓰기 데이터"),
    ("D1523", "W", "RFID② 명령 ID"),
    ("D1524", "W", "RFID② 상태"),
    ("D1525", "W", "RFID② 읽은 데이터"),
    ("D1526", "W", "RFID② 읽은 PACK ID"),
    ("D1527", "W", "RFID② 읽은 재검사 횟수"),
    ("D1530", "W", "RFID③ 명령"),
    ("M1531", "B", "RFID③ 실행 펄스"),
    ("D1531", "W", "RFID③ 메모리 주소"),
    ("D1532", "W", "RFID③ 쓰기 데이터"),
    ("D1533", "W", "RFID③ 명령 ID"),
    ("D1534", "W", "RFID③ 상태"),
    ("D1535", "W", "RFID③ 읽은 데이터"),
    ("D1536", "W", "RFID③ 읽은 PACK ID"),
    ("D1537", "W", "RFID③ 읽은 재검사 횟수"),
    # 16xx AS/RS · 격리 · 1차 분리
    ("M1600", "B", "크레인 A (입고면)"),
    ("M1601", "B", "크레인 B (출고면)"),
    ("D1600", "W", "랙 번호 (1~3열 4S · 4~6열 6S)"),
    *[(f"D{1610 + i}", "W", f"R{i + 1:02d} LOCK 경과 시간") for i in range(24)],
    ("D1650", "W", "발열 격리 DB 기록 요청"),
    ("D1651", "W", "발열 격리 PACK ID"),
    ("D1652", "W", "발열 격리 가상 온도 (0.1 °C)"),
    ("D1653", "W", "발열 격리 DB 기록 완료"),
    ("M1660", "B", "1차 분리 Pop-up Wheel 직진 (→ 메인 검사)"),
    ("M1661", "B", "1차 분리 Pop-up Wheel 아래 (→ 발열 격리)"),
    ("M1690", "B", "보관 중 이상 발열"),
    # 17xx 검사 · 분류
    ("M1700", "B", "메인 검사 프로브"),
    ("D1700", "W", "메인 판정 (1 PASS 2 RETEST 3 NG-ΔV 4 NG-IR 5 NG-TEMP)"),
    ("D1701", "W", "메인 팩 ΔV (mV)"),
    ("D1702", "W", "메인 팩 IR (0.01 mΩ)"),
    ("D1703", "W", "메인 온도 (0.1 °C)"),
    ("D1710", "W", "메인 계측 요청"),
    ("D1711", "W", "메인 요청 PACK ID"),
    ("D1712", "W", "메인 요청 재검사 횟수"),
    ("D1713", "W", "메인 계측 완료"),
    ("D1714", "W", "메인 요청 셀 수"),
    ("M1720", "B", "재검사 라인 분기 Sorter (판정 2·3·4·5)"),
    ("M1730", "B", "재검사 프로브"),
    ("D1730", "W", "재검사 판정"),
    ("D1731", "W", "재검사 팩 ΔV (mV)"),
    ("D1732", "W", "재검사 팩 IR (0.01 mΩ)"),
    ("D1733", "W", "재검사 온도 (0.1 °C)"),
    ("M1731", "B", "2차 분리 Pop-up Wheel 위 (GOOD 합류)"),
    ("M1732", "B", "2차 분리 Pop-up Wheel 아래 (NG OUT)"),
    ("D1740", "W", "재검사 계측 요청"),
    ("D1741", "W", "재검사 요청 PACK ID"),
    ("D1742", "W", "재검사 요청 재검사 횟수"),
    ("D1743", "W", "재검사 계측 완료"),
    ("D1744", "W", "재검사 요청 셀 수"),
    # 18xx 재검사 라인 (v6: 정치 버퍼 삭제, 번지는 유지)
    ("M1800", "B", "재검사 라인 분기점까지 참 (메인 출구 대기)"),
    ("D1800", "W", "재검사 라인 위 팩 수"),
    # 19xx 게이트 · HMI
    ("X1900", "B", "GOOD OUT 게이트 센서"),
    ("X1901", "B", "NG OUT 게이트 센서"),
    ("X1902", "B", "발열 격리 게이트 센서"),
    ("X1903", "B", "재검사 GOOD 합류 간격 센서"),
    ("D1900", "W", "카운터 GOOD"),
    ("D1901", "W", "카운터 NG"),
    ("D1902", "W", "카운터 발열 격리"),
    ("D1903", "W", "카운터 합계"),
    ("D1904", "W", "수율 (0.1 %)"),
    ("M1920", "B", "HMI 카운터 리셋"),
]
TYPE_NAME = {"W": "Short", "B": "Boolean"}
USED = {d for d, _, _ in TAGS}

OLD_BLOCK = {"30": "15", "32": "16", "33": "17", "34": "18", "35": "19"}   # D9
ADDR_RE = re.compile(r"^([DMXY])([0-9A-F]{4})$")


# ------------------------------------------------------------------ CSV 입출력
def read_csv(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp949", "utf-16"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        sys.exit(f"인코딩을 알 수 없습니다: {path}")
    try:
        dialect = csv.Sniffer().sniff(text.splitlines()[0], delimiters=",\t;")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.reader(io.StringIO(text), dialect))
    return rows, enc, dialect


def write_csv(path, rows, enc="utf-8-sig", dialect=csv.excel):
    with open(path, "w", encoding=enc, newline="") as f:
        csv.writer(f, dialect).writerows(rows)


def _addr_of(cell):
    """'D3302', 'QSIM.D3302', ' d3302 ' → 'D3302' (디바이스 부분만)"""
    c = cell.strip().upper()
    c = c.rsplit(".", 1)[-1] if "." in c else c
    return c if ADDR_RE.match(c) else None


def find_cols(rows, name_col=None, addr_col=None, desc_col=None):
    header, body = rows[0], rows[1:]
    ncol = max(len(r) for r in rows)
    if addr_col is None:
        score = [sum(1 for r in body if i < len(r) and _addr_of(r[i])) for i in range(ncol)]
        addr_col = max(range(ncol), key=score.__getitem__)
        if score[addr_col] == 0:
            sys.exit("디바이스 번지 열을 찾지 못했습니다. --addr-col 로 지정하세요.")
    low = [h.strip().lower() for h in header]
    if name_col is None:
        cand = [i for i, h in enumerate(low) if i != addr_col and any(k in h for k in ("name", "tag", "이름", "태그"))]
        name_col = cand[0] if cand else (0 if addr_col != 0 else 1)
    if desc_col is None:
        cand = [i for i, h in enumerate(low) if any(k in h for k in ("desc", "comment", "설명", "코멘트"))]
        desc_col = cand[0] if cand else None
    return name_col, addr_col, desc_col


def _set_addr(cell, new):
    """원래 칸 형식(접두어 · 대소문자)을 유지하면서 디바이스 부분만 교체"""
    s = cell.strip()
    return (s.rsplit(".", 1)[0] + "." + new) if "." in s else new


# ------------------------------------------------------------------ 명령
def cmd_list(_args):
    for d, t, desc in TAGS:
        print(f"{d:<7}{TYPE_NAME[t]:<9}{desc}")
    w = sum(1 for _, t, _ in TAGS if t == "W")
    print(f"\n총 {len(TAGS)}개 (워드 {w} · 비트 {len(TAGS) - w}). 태그 이름 = 디바이스 이름")


def cmd_csv(args):
    rows = [["TagName", "Device", "DataType", "Access", "Description"]]
    rows += [[d, d, TYPE_NAME[t], "Read/Write", desc] for d, t, desc in TAGS]
    write_csv(args.csv, rows)
    print(f"[저장] {args.csv} · {len(TAGS)}개 (Configurator 가져오기 형식이 다르면 --template 을 쓰세요)")


def cmd_template(args):
    rows, enc, dialect = read_csv(args.template)
    name_c, addr_c, desc_c = find_cols(rows, args.name_col, args.addr_col, args.desc_col)
    header, body = rows[0], rows[1:]
    print(f"[견본] {args.template} ({enc}) · 이름 열 {name_c} '{header[name_c] if name_c < len(header) else ''}'"
          f" · 번지 열 {addr_c} '{header[addr_c] if addr_c < len(header) else ''}'"
          + (f" · 설명 열 {desc_c} '{header[desc_c]}'" if desc_c is not None else " · 설명 열 없음"))

    def pick(kinds):
        for r in body:
            a = _addr_of(r[addr_c]) if addr_c < len(r) else None
            if a and a[0] in kinds:
                return r
        return None

    word_row, bit_row = pick("D"), pick("MXY")
    if word_row is None or bit_row is None:
        sys.exit("견본에 워드(D…) 태그와 비트(M/X/Y…) 태그가 각각 1개 이상 있어야 합니다.")
    existing = {r[name_c].strip().upper() for r in body if name_c < len(r)}
    out, skipped = [header], []
    if args.keep_existing:
        out += body
    for d, t, desc in TAGS:
        if d in existing:
            skipped.append(d)
            continue
        r = list(word_row if t == "W" else bit_row)
        r[name_c] = d
        r[addr_c] = _set_addr(r[addr_c], d)
        if desc_c is not None and desc_c < len(r):
            r[desc_c] = desc
        out.append(r)
    write_csv(args.out, out, enc, dialect)
    print(f"[저장] {args.out} · 새 태그 {len(out) - 1 - (len(body) if args.keep_existing else 0)}개"
          + (f" · 이미 있는 이름이라 건너뜀 {len(skipped)}개: {' '.join(skipped)}" if skipped else ""))
    print("        워드 견본:", " | ".join(word_row))
    print("        비트 견본:", " | ".join(bit_row))
    print("  → 견본 행의 데이터 형식이 16비트 정수 / 비트인지 확인한 뒤 Configurator 에서 가져오기 하세요.")


def cmd_remap(args):
    rows, enc, dialect = read_csv(args.remap_old)
    name_c, addr_c, _ = find_cols(rows, args.name_col, args.addr_col, args.desc_col)
    out, moved, unmapped, unused = [rows[0]], 0, [], []
    for r in rows[1:]:
        r = list(r)
        a = _addr_of(r[addr_c]) if addr_c < len(r) else None
        name = r[name_c] if name_c < len(r) else "?"
        if a and a[1] == "3":
            kind, num = a[0], a[1:]
            blk = OLD_BLOCK.get(num[:2])
            if blk is None:
                unmapped.append(f"{name}({a})")
            else:
                new = kind + blk + num[2:]
                r[addr_c] = _set_addr(r[addr_c], new)
                moved += 1
                if new not in USED or "BYP" in name.upper():
                    # BYPASS 카운터(이전 D1903)는 v4부터 같은 번지가 '합계'로 바뀌어 번지만으로는 못 가림 → 이름으로도 표시
                    unused.append(f"{name}({a}→{new})")
        out.append(r)
    write_csv(args.out, out, enc, dialect)
    print(f"[저장] {args.out} · 번지 이동 {moved}개 (이름은 그대로)")
    if unmapped:
        print(f"[확인] 블록 규칙에 없는 3000번대 {len(unmapped)}개 (그대로 둠): {' '.join(unmapped)}")
    if unused:
        print(f"[정리 대상] v5 디바이스 표에 없는 번지 {len(unused)}개 (BYPASS · M1710 등 삭제된 기능일 수 있음):")
        print("   " + " ".join(unused))


def cmd_check(args):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from plc_link import LinkError, OpcLink

    link = OpcLink(args.server, args.device, args.wrapper)
    ok, bad = 0, []
    try:
        for d, _, _ in TAGS:
            try:
                link.read(d)
                ok += 1
            except LinkError as e:
                bad.append(f"{d}: {e}")
    finally:
        link.close()
    print(f"[확인] {link.label} · 읽기 성공 {ok}/{len(TAGS)}")
    for b in bad:
        print("   " + b)


def main():
    p = argparse.ArgumentParser(description="MX OPC 태그 목록 (1500~19FF, v5)")
    p.add_argument("--csv", metavar="OUT", help="기본 형식 CSV 저장")
    p.add_argument("--template", metavar="EXPORT_CSV", help="Configurator 내보내기 CSV 를 견본으로 가져오기용 CSV 생성")
    p.add_argument("--remap-old", metavar="EXPORT_CSV", help="기존 3000번대 태그 번지를 1500~19FF 로 이동")
    p.add_argument("--out", help="--template / --remap-old 결과 파일")
    p.add_argument("--keep-existing", action="store_true", help="--template 결과에 견본의 기존 행도 포함")
    p.add_argument("--name-col", type=int)
    p.add_argument("--addr-col", type=int)
    p.add_argument("--desc-col", type=int)
    p.add_argument("--check", action="store_true", help="MX OPC Server 에서 v5 태그 읽기 확인 (32비트 Python)")
    p.add_argument("--server", default="Mitsubishi.MXOPC.6")
    p.add_argument("--device", default="QSIM")
    p.add_argument("--wrapper", default="OPC.SiemensDAAuto")
    args = p.parse_args()

    if (args.template or args.remap_old) and not args.out:
        p.error("--out 이 필요합니다")
    if args.check:
        cmd_check(args)
    elif args.template:
        cmd_template(args)
    elif args.remap_old:
        cmd_remap(args)
    elif args.csv:
        cmd_csv(args)
    else:
        cmd_list(args)


if __name__ == "__main__":
    main()
