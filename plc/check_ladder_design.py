"""
plc/ladder_design_v6.md 대조 도구 — 설계서에 쓴 번지가 0-4 표 또는 번지 안에 있는지 글자로 검사합니다.

  python plc/check_ladder_design.py            (Windows 콘솔: PYTHONIOENCODING=utf-8)

검사 항목
  1) 실제 번지(D/M 1500~1999, X/Y 1500~19FF)가 모두 0-4 표(tools/mxopc_tags.py TAGS) 또는
     번지 안(computer_use/fio_io_map_v6.csv)에 있는지, 블록 밖 번지가 없는지
  2) 자리 표시(M#nn · D#nn · T#nn): 명령어 목록에 쓴 것과 3-3 · 3-4 표에 적은 것이 같은지
  3) 명령어 목록: 회로 이름 중복, 이중 코일(OUT 이 두 회로 이상에 나온 디바이스)
  4) 내부 번지 배정 초안(plc/ladder_alloc_v6.csv, 안건 A30): 배정끼리 · 0-4 표 · 번지 안 · 13장 E1 제안(칸별 비트
     M1610~M1657)과 겹치지 않는지, 블록 안인지, 목록의 자리 표시가 모두 배정됐는지(A24 몫은 빈칸)
래더가 뜻대로 도는지는 검사하지 않습니다(GX Works2 시뮬레이션에서 확인).

  python plc/check_ladder_design.py --apply plc/ladder_mnemonic_v6.txt
     5장 명령어 목록의 자리 표시를 배정 초안 번지로 바꾼 입력용 목록을 만듭니다(배정 없는 자리는 그대로 남김).
"""
import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import mxopc_tags  # noqa: E402

DOC = os.path.join(ROOT, "plc", "ladder_design_v6.md")
MAP = os.path.join(ROOT, "computer_use", "fio_io_map_v6.csv")
ALLOC = os.path.join(ROOT, "plc", "ladder_alloc_v6.csv")
E1_BITS = {("M", n) for n in range(1610, 1658)}     # 13장 E1 제안(보류): 칸별 LOCK · 숙성 완료 비트

REAL = re.compile(r"(?<![#\w])([DMXY])([0-9][0-9A-F]{3})(?![0-9A-Fa-f])")
RANGE = re.compile(r"(?<![#\w])([DMXY])([0-9][0-9A-F]{3})~(?:[DMXY])?([0-9][0-9A-F]{3})(?![0-9A-Fa-f])")
PH = re.compile(r"(?<!\w)([MDT])#(\d+)")
PH_RANGE = re.compile(r"(?<!\w)([MDT])#(\d+)~(?:[MDT]#)?(\d+)")
RUNG = re.compile(r"^([A-Z]\d{2})\s+(.*)$")


def expand(text, rng, single, base_of):
    """범위 표기(A~B)를 풀어서 집합으로."""
    found = set()
    for m in rng.finditer(text):
        kind, lo, hi = m.group(1), m.group(2), m.group(3)
        base = base_of(kind)
        for n in range(int(lo, base), int(hi, base) + 1):
            found.add((kind, n))
    for m in single.finditer(text):
        found.add((m.group(1), int(m.group(2), base_of(m.group(1)))))
    return found


def real_base(kind):
    return 16 if kind in "XY" else 10


def fmt(kind, n):
    return f"{kind}{n:X}" if kind in "XY" else f"{kind}{n}"


def in_block(kind, n):
    return 0x1500 <= n <= 0x19FF if kind in "XY" else 1500 <= n <= 1999


def load_alloc():
    """배정 초안 → {(종류, 자리 번호): (종류, 번지) 또는 None}, 행 목록"""
    table, rows = {}, []
    with open(ALLOC, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            kind, start, cnt = r["자리 표시"][0], int(r["자리 표시"][2:]), int(r["개수"])
            addr = r["배정(초안)"].strip()
            rows.append((kind, start, cnt, addr, r["안건"]))
            for i in range(cnt):
                table[(kind, start + i)] = (addr[0], int(addr[1:]) + i) if addr else None
    return table, rows


def main():
    alloc, alloc_rows = load_alloc()
    alloc_real = {v for v in alloc.values() if v}
    text = open(DOC, encoding="utf-8").read()
    if "\r\n" in text:
        print("[경고] 설계서 줄바꿈에 CRLF가 있습니다")

    # 기준 1: 0-4 표 = MX OPC 태그 100개 / 기준 2: 번지 안 CSV
    table04 = {(d[0], int(d[1:], real_base(d[0]))) for d in mxopc_tags.USED}
    with open(MAP, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    io_map = {(r["번지"][0], int(r["번지"][1:], real_base(r["번지"][0]))) for r in rows}

    used = expand(text, RANGE, REAL, real_base)
    in04 = {u for u in used if u in table04}
    in_map_only = {u for u in used if u not in table04 and u in io_map}
    in_alloc = {u for u in used if u in alloc_real}
    unknown = sorted(used - table04 - io_map - alloc_real)
    outside = sorted(u for u in used if not in_block(*u))

    # 명령어 목록(코드 블록 안의 회로 줄)과 그 밖(표 · 본문)을 나눔
    code, prose, inside = [], [], False
    for line in text.split("\n"):
        if line.startswith("```"):
            inside = not inside
            continue
        (code if inside else prose).append(line)
    rungs = []
    for line in code:
        body = line.split(";", 1)[0].rstrip()
        m = RUNG.match(body)
        if m:
            rungs.append((m.group(1), m.group(2)))
    # 2-2 표기 예시(J13)는 5장과 같은 줄이라 한 번만 셈
    uniq = {}
    dup = []
    for name, body in rungs:
        if name in uniq and uniq[name] != body:
            dup.append(name)
        uniq[name] = body

    ph_code = expand("\n".join(code), PH_RANGE, PH, lambda k: 10)
    tables = "\n".join(l for l in prose if l.startswith("|"))
    ph_table = expand(tables, PH_RANGE, PH, lambda k: 10)
    # 랙 표 4개는 표에 범위로, 목록에는 인덱스 수식(D#100Z0)으로 나오므로 첫 번지만 비교
    rack = {("D", b + i) for b in (100, 130, 160, 190) for i in range(1, 24)}
    missing = sorted(ph_code - ph_table)
    unused = sorted(ph_table - ph_code - rack)

    outs = {}
    for name, body in uniq.items():
        if "=>" not in body:
            continue
        for ins in body.split("=>", 1)[1].split("|"):
            p = ins.split()
            if len(p) >= 2 and p[0] == "OUT":
                outs.setdefault(p[1], []).append(name)
    double = {d: r for d, r in outs.items() if len(r) > 1}

    # 명령어 목록(회로 줄, 설명 제외)에 실제로 나온 번지만 따로 셈. D1610Z0 같은 인덱스 수식은 첫 번지로 셈
    used_code = expand(" ".join(uniq.values()), RANGE, REAL, real_base)
    code_unknown = sorted(used_code - table04 - io_map)   # 5장에는 배정 번지를 직접 쓰지 않음(자리 표시만)

    # 배정 초안 대조
    seen, clash = {}, []
    for key, v in alloc.items():
        if not v:
            continue
        if v in seen:
            clash.append(f"{fmt(*v)}: {seen[v][0]}#{seen[v][1]:02d} · {key[0]}#{key[1]:02d}")
        seen[v] = key
    hit04 = sorted(fmt(*v) for v in alloc_real if v in table04)
    hit_map = sorted(fmt(*v) for v in alloc_real if v in io_map)
    hit_e1 = sorted(fmt(*v) for v in alloc_real if v in E1_BITS)
    alloc_out = sorted(fmt(*v) for v in alloc_real if not (1500 <= v[1] <= 1999))
    no_row = sorted(ph_code - set(alloc))                              # 배정표에 줄이 없는 자리 표시
    blank = sorted(k for k in ph_code if k in alloc and not alloc[k])  # 줄은 있는데 번지 빈칸(A24)
    extra = sorted(set(alloc) - ph_table)                              # 배정표에만 있는 자리 표시

    if "--apply" in sys.argv:
        out_path = sys.argv[sys.argv.index("--apply") + 1]

        def sub(m):
            v = alloc.get((m.group(1), int(m.group(2))))
            return fmt(*v) if v else m.group(0)
        lines = ["; Project B v6 래더 명령어 목록 — plc/ladder_design_v6.md 5장을 배정 초안(plc/ladder_alloc_v6.csv, A30)으로 치환",
                 "; 자동 생성: python plc/check_ladder_design.py --apply <이 파일>. 직접 고치지 말고 설계서 · 배정표를 고친 뒤 다시 만듭니다.",
                 f"; # 이 남은 자리 {len(blank)}종은 번지 미정(A24). <A26> <A27> <A28> 줄은 설명(;)으로만 있습니다. GX Works2 입력 · 시뮬레이션 전(동작 미확인)."]
        inside = False
        for line in text.split("\n"):
            if line.startswith("### ") and not inside:
                head = line
            if line.startswith("```"):
                inside = not inside
                if inside and text.index(line) >= 0 and head.startswith("### ") and "표기" not in head:
                    lines += ["", "; ===== " + head[4:].replace("`", "") + " ====="]
                continue
            if inside and "표기" not in head:
                lines.append(PH.sub(sub, line))
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n")
        print(f"[치환] {out_path} 기록 ({len(lines)}줄, 미배정 자리 {len(blank)}종)")

    kinds = {k: len({p for p in ph_table if p[0] == k}) for k in "MDT"}
    print(f"설계서 실제 번지(종류)          : {len(used)}")
    print(f"  0-4 표에 있음                 : {len(in04)}")
    print(f"  번지 안(확정 전)에만 있음     : {len(in_map_only)}")
    print(f"  어디에도 없음                 : {len(unknown)}  {[fmt(*u) for u in unknown]}")
    print(f"  배정 초안(A30)에 있음         : {len(in_alloc)}")
    print(f"1500~19FF 블록 밖               : {len(outside)}  {[fmt(*u) for u in outside]}")
    print(f"자리 표시(종류, 표 기준)        : M# {kinds['M']} · D# {kinds['D']} · T# {kinds['T']}")
    print(f"  목록에 쓰였는데 표에 없음     : {len(missing)}  {[f'{k}#{n:02d}' for k, n in missing]}")
    print(f"  표에만 있고 목록에 안 쓰임    : {len(unused)}  {[f'{k}#{n:02d}' for k, n in unused]}")
    print(f"명령어 목록 회로 수             : {len(uniq)} (이름 중복 {len(dup)}  {dup})")
    print(f"이중 코일                       : {len(double)}  {double}")
    print(f"0-4 표 {len(table04)}개 가운데 설계서가 쓰는 것 : {len(in04)}"
          f"  (안 쓰는 것: {sorted(fmt(*u) for u in table04 - used)})")
    print(f"번지 안 신규 {len(io_map - table04)}개 가운데 설계서가 쓰는 것 : {len(in_map_only)}"
          f"  (안 쓰는 것: {sorted(fmt(*u) for u in io_map - table04 - used)})")
    print(f"명령어 목록에 직접 나온 번지    : {len(used_code)} (0-4 표 {len(used_code & table04)} · 번지 안 {len(used_code - table04 & io_map)} · 없음 {len(code_unknown)})")
    print(f"  0-4 표 번지 중 목록에 직접 안 나온 것: {sorted(fmt(*u) for u in table04 - used_code)}")
    print(f"  번지 안 신규 중 목록에 직접 안 나온 것: {sorted(fmt(*u) for u in io_map - table04 - used_code)}")
    n_alloc = {k: len([1 for (kk, _), v in alloc.items() if kk == k and v]) for k in "MDT"}
    print(f"배정 초안(A30) 번지 수          : M {n_alloc['M']} · D {n_alloc['D']} · T {n_alloc['T']}")
    print(f"  배정끼리 겹침                 : {len(clash)}  {clash}")
    print(f"  0-4 표 / 번지 안 / 13장 E1 제안 비트와 겹침 : {len(hit04)} / {len(hit_map)} / {len(hit_e1)}  {hit04 + hit_map + hit_e1}")
    print(f"  M · D · T 1500~1999 밖        : {len(alloc_out)}  {alloc_out}")
    print(f"  목록의 자리 표시 중 배정표에 줄 없음 / 번지 빈칸(A24) / 배정표에만 있음 : {len(no_row)} / {len(blank)} / {len(extra)}"
          f"  {[f'{k}#{n:02d}' for k, n in no_row + extra]}")
    bad = unknown or outside or missing or dup or double or code_unknown or clash or hit04 or hit_map or hit_e1 or alloc_out or no_row or extra
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
