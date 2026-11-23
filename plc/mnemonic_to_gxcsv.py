"""plc/ladder_mnemonic_v6.txt → GX Works2 [편집] → [CSV 파일에서 읽기]용 CSV (UTF-16, 탭 구분).

python plc/mnemonic_to_gxcsv.py [--out test_results/B_v6_ladder.csv]

CSV 형식 (11-23 GX Works2 1.x에서 CSV 쓰기로 확인):
  머리 3줄 + [스텝 번호, 행 간 스테이트먼트, 명령, I/O(디바이스), 공백란, PI 스테이트먼트, 노트]
  오퍼랜드가 여럿이면 둘째부터 다음 줄의 디바이스 칸 (스텝 번호는 GX Works2가 다시 매김)
  행 간 스테이트먼트는 명령 줄과 따로 한 줄

번지 미정(A24, '#'이 남은 자리 표시) 처리 — 설계서 8장 "그 접점 · 출력을 빼고 넣고 기록":
  M#60(운전 중)        → 항상 ON으로 보고 SM400으로 바꿈 (SET/RST M#60 출력은 뺌)
  M#68 · M#69(버튼 입력) → OFF로 봄: 직렬 접점이면 그 회로를 뺌
  그 밖의 '#' 출력(알람 비트 M#61~M#67) → 그 출력만 뺌. 출력이 다 빠지면 회로를 뺌
  '; Xnn <A..>' 주석 회로(A09 · C06 · C09 등)는 넣지 않음
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "plc" / "ladder_mnemonic_v6.txt"
RUNG = re.compile(r"^([A-Z]\d{2})\s+(.*)$")
ALWAYS_ON = {"M#60"}

CONTACT_TO_LD = {"AND": "LD", "ANI": "LDI", "ANDP": "LDP", "ANDF": "LDF"}


def to_ld(ins):
    if ins in CONTACT_TO_LD:
        return CONTACT_TO_LD[ins]
    if ins.startswith("AND") and ins[3:] and ins[3:][0] in "=<>":
        return "LD" + ins[3:]
    return ins


def has_ph(tok):
    return "#" in tok


def convert(lines):
    rows, log = [], []
    statement = ""
    for raw in lines:
        line = raw.rstrip("\n")
        if not line.strip():
            continue
        if line.startswith(";"):
            m = re.match(r";\s*=+\s*(.*?)\s*=+\s*$", line)
            if m:
                statement = m.group(1)
            elif re.match(r";\s*[A-Z]\d{2}\s", line):
                log.append(f"넣지 않음(주석 회로): {line[1:].strip()}")
            continue
        m = RUNG.match(line)
        if not m:
            continue
        rid, body = m.group(1), m.group(2)
        body = body.split(";", 1)[0].strip()
        if "=>" in body:
            left, right = [x.strip() for x in body.split("=>", 1)]
        else:
            left, right = "", body
        contacts = [c.split() for c in left.split("|") if c.strip()] if left else []
        outputs = [o.split() for o in right.split("|") if o.strip()]

        drop, notes = False, []
        new_c = []
        for c in contacts:
            if any(has_ph(t) for t in c[1:]):
                dev = next(t for t in c[1:] if has_ph(t))
                if dev in ALWAYS_ON:
                    new_c.append([c[0]] + ["SM400" if t == dev else t for t in c[1:]])
                    notes.append(f"{dev}→SM400")
                elif c[0].startswith("OR"):
                    notes.append(f"병렬 접점 {' '.join(c)} 뺌")
                else:
                    drop = True
                    notes.append(f"직렬 접점 {' '.join(c)}(OFF로 봄)")
            else:
                new_c.append(c)
        new_o = []
        for o in outputs:
            if any(has_ph(t) for t in o[1:]):
                notes.append(f"출력 {' '.join(o)} 뺌")
            else:
                new_o.append(o)
        if not new_o:
            drop = True
        if drop:
            log.append(f"뺀 회로 {rid}: {line.strip()}  [{'; '.join(notes)}]")
            continue
        if notes:
            log.append(f"고친 회로 {rid}: {'; '.join(notes)}")
        if new_c and not new_c[0][0].startswith("LD"):
            new_c[0][0] = to_ld(new_c[0][0])
        first = True
        for ins in new_c + new_o:
            rows.append((statement if first and statement else "", ins[0], ins[1:], rid if first else ""))
            if first:
                statement = ""
            first = False
    rows.append(("", "END", [], ""))
    return rows, log


def write_csv(rows, out):
    lines = ['"(프로젝트 미설정)"', '"PLC 정보:"\t"QCPU (Q mode) Q03UDE"',
             '"스텝 번호"\t"행 간 스테이트먼트"\t"명령"\t"I/O(디바이스)"\t"공백란"\t"PI 스테이트먼트"\t"노트"']
    q = lambda xs: "\t".join(f'"{x}"' for x in xs)
    for step, (stmt, ins, ops, _rid) in enumerate(rows):
        if stmt:   # 행 간 스테이트먼트는 명령과 다른 줄 (같은 줄이면 GX Works2가 읽지 못함, 11-23)
            lines.append(q(["", stmt, "", "", "", "", ""]))
        lines.append(q([str(step), "", ins, ops[0] if ops else "", "", "", ""]))
        for o in ops[1:]:
            lines.append(q(["", "", "", o, "", "", ""]))
    Path(out).write_bytes(("\r\n".join(lines) + "\r\n").encode("utf-16"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(SRC))
    ap.add_argument("--out", default=str(ROOT / "test_results" / "B_v6_ladder.csv"))
    a = ap.parse_args()
    rows, log = convert(Path(a.src).read_text(encoding="utf-8").splitlines())
    write_csv(rows, a.out)
    rungs = sum(1 for r in rows if r[3])
    print(f"명령 {len(rows)}줄 · 회로 {rungs}개 → {a.out}")
    for x in log:
        print(" -", x)


if __name__ == "__main__":
    main()
