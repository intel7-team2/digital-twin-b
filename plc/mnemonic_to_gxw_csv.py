"""
명령어 목록(plc/ladder_mnemonic_v6.txt) → GX Works2 "CSV 파일에서 읽기" 형식으로 변환.

GX Works2 심플 프로젝트 래더 편집 화면의 [편집] → [CSV 파일에서 읽기]가 받는 형식은
[CSV 파일로 쓰기]로 내보낸 파일과 같습니다(11-23 확인, GX Works2 1.494Q · Q03UDE):
  - UTF-16 LE(BOM) · 탭 구분 · 모든 칸 큰따옴표 · CRLF
  - 1행 프로젝트 이름, 2행 "PLC 정보:" + 기종, 3행 열 이름
  - 명령 1개 = 첫 행(스텝 번호 · 행 간 스테이트먼트 · 명령 · 첫 피연산자) + 피연산자마다 한 행
사용:
  python plc/mnemonic_to_gxw_csv.py plc/ladder_mnemonic_v6.txt test_results/B_v6_ladder_import.csv
목록에 "; @PROGRAM 이름" 줄이 있으면 프로그램 파일마다 따로 만듭니다: <출력>_<이름>.csv (예: B_v6_ladder_import_RFID.csv).
GX Works2에서 같은 이름의 프로그램을 만들고 각각 [CSV 파일에서 읽기], PLC 파라미터 [프로그램 설정]에 위 순서대로 스캔 등록.
"""
import re
import sys

CPU = "QCPU (Q mode) Q03UDE"
HEADER = ["스텝 번호", "행 간 스테이트먼트", "명령", "I/O(디바이스)", "공백란", "PI 스테이트먼트", "노트"]
RUNG = re.compile(r"^([A-Z]\d{2})\s+(.*)$")
BLOCK = re.compile(r"^;\s*=+\s*(.+?)\s*=+\s*$")
PROGRAM = re.compile(r"^;\s*@PROGRAM\s+(\w+)")


def split_code(body):
    """'LD X0 | AND X1  =>  OUT Y0 | MOV K1 D0 ; 설명' → (접점 목록, 출력 목록, 설명)"""
    note = ""
    if ";" in body:
        body, note = body.split(";", 1)
    if "=>" in body:
        left, right = body.split("=>", 1)
        conds = [c.strip() for c in left.split("|") if c.strip()]
        outs = [c.strip() for c in right.split("|") if c.strip()]
    else:
        conds, outs = [], [c.strip() for c in body.split("|") if c.strip()]
    return conds, outs, note.strip()


def rows_for(instr, statement=""):
    parts = instr.split()
    op, args = parts[0], parts[1:]
    first = args[0] if args else ""
    rows = [["", statement, op, first, "", "", ""]]
    for a in args[1:]:
        rows.append(["", "", "", a, "", "", ""])
    return rows


def convert(src):
    """[(프로그램 이름, 행, 회로 수, 명령 수)] — @PROGRAM 표시가 없으면 MAIN 하나"""
    progs = []
    rows, n_rung, n_instr, name_p = [], 0, 0, "MAIN"
    pending_stmt = ""
    for raw in open(src, encoding="utf-8-sig"):
        line = raw.rstrip("\r\n")
        m = PROGRAM.match(line)
        if m:
            if n_rung:
                progs.append((name_p, rows, n_rung, n_instr))
            rows, n_rung, n_instr, name_p = [], 0, 0, m.group(1)
            pending_stmt = ""
            continue
        m = BLOCK.match(line)
        if m:
            pending_stmt = m.group(1)
            continue
        m = RUNG.match(line)
        if not m:
            continue                      # 설명 줄(; ...)과 빈 줄은 건너뜀
        name, body = m.groups()
        conds, outs, _ = split_code(body)
        n_rung += 1
        if pending_stmt:                  # 행 간 스테이트먼트는 명령과 다른 행에 둬야 읽힘(11-23 확인)
            rows.append(["", pending_stmt, "", "", "", "", ""])
            pending_stmt = ""
        for ins in conds + outs:
            rows += rows_for(ins)
            n_instr += 1
    if n_rung:
        progs.append((name_p, rows, n_rung, n_instr))
    return progs


def main():
    src, dst = sys.argv[1], sys.argv[2]
    progs = convert(src)
    for name_p, rows, n_rung, n_instr in progs:
        path = dst if len(progs) == 1 else dst[:-4] + f"_{name_p}.csv"
        out = [["B_v6_ladder"], ["PLC 정보:", CPU], HEADER] + rows + [["", "", "END", "", "", "", ""]]
        text = "\r\n".join("\t".join(f'"{c}"' for c in r) for r in out) + "\r\n"
        with open(path, "wb") as f:
            f.write(b"\xff\xfe" + text.encode("utf-16-le"))
        print(f"{path}: 프로그램 {name_p} · 회로 {n_rung} · 명령 {n_instr} · 행 {len(rows)}")


if __name__ == "__main__":
    main()
