"""
월요일 Computer Use 작업용 참고 그림 4장 (SVG + PNG)
  img/io_map_v6        Factory I/O 센서 · 액추에이터 번지 안 (fio_io_map_v6.csv)
  img/asrs_fio_v6      AS/RS: Factory I/O 랙(3열 × 6단 = 18칸) 2개로 24칸 만들기 + 칸 번호
  img/c7_wingp_screen  C7 WinGP 접속 시험 화면 작화 지시 (좌표 · 번지 · 장치 설정)
  img/monday_flow      월요일 순서 · 연결 구성 · F2에서 정할 것

실행: python computer_use/make_guides.py   (PNG는 헤드리스 Edge 로 만듦, 없으면 SVG만)
"""
import csv
import html
import io
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "img")
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
FONT = "Malgun Gothic, Pretendard, sans-serif"
BG, PANEL, LINE = "#1B2027", "#252B32", "#3A424B"
TXT, SUB, DIM = "#F8FAFC", "#CBD5E1", "#94A3B8"
ORANGE, BLUE, GREEN, RED, YELLOW, VIOLET = "#F59E0B", "#60A5FA", "#34D399", "#EF4444", "#FACC15", "#A78BFA"


class Svg:
    def __init__(self, w, h):
        self.w, self.h, self.o = w, h, []
        self.o.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
                      f'font-family="{FONT}">')
        self.o.append('<defs><pattern id="hatch" width="8" height="8" patternUnits="userSpaceOnUse" '
                      'patternTransform="rotate(45)"><rect width="8" height="8" fill="#2A3038"/>'
                      '<rect width="2" height="8" fill="#4B5563"/></pattern>'
                      '<marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
                      f'<path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker></defs>')
        self.rect(0, 0, w, h, BG)

    def rect(self, x, y, w, h, fill, stroke="none", sw=1, rx=0, extra=""):
        self.o.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" '
                      f'stroke="{stroke}" stroke-width="{sw}"{extra}/>')

    def text(self, x, y, s, size=12, color=TXT, weight=400, anchor="start", extra=""):
        self.o.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" fill="{color}" '
                      f'text-anchor="{anchor}"{extra}>{html.escape(str(s))}</text>')

    def line(self, x1, y1, x2, y2, color=SUB, sw=1.5, extra=""):
        self.o.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" '
                      f'stroke-width="{sw}"{extra}/>')

    def circle(self, cx, cy, r, fill, stroke="none", sw=1):
        self.o.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    def badge(self, x, y, s, color, size=10, pad=5):
        w = tw(s, size) + 2 * pad
        self.rect(x, y - size - 2, w, size + 7, color, rx=3, extra=' fill-opacity="0.18"')
        self.rect(x, y - size - 2, w, size + 7, "none", color, 1, rx=3)
        self.text(x + pad, y + 1, s, size, color, 700)
        return w

    def save(self, name):
        self.o.append("</svg>")
        os.makedirs(OUT, exist_ok=True)
        p = os.path.join(OUT, name + ".svg")
        with io.open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(self.o))
        png = os.path.join(OUT, name + ".png")
        if os.path.exists(EDGE):
            # 헤드리스 Edge 창은 내용 영역이 창 크기보다 작으므로, 넉넉한 창으로 찍고 SVG 크기로 잘라냄
            wrap = os.path.join(OUT, f"_{name}.html")
            with io.open(wrap, "w", encoding="utf-8") as f:
                f.write(f'<!doctype html><html><body style="margin:0;background:{BG}">'
                        f'<img src="{name}.svg" width="{self.w}" height="{self.h}" style="display:block"></body></html>')
            if os.path.exists(png):
                os.remove(png)
            subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                            f"--window-size={self.w + 60},{self.h + 160}", f"--screenshot={png}",
                            "file:///" + wrap.replace("\\", "/")], capture_output=True, timeout=120)
            os.remove(wrap)
            try:
                from PIL import Image
                im = Image.open(png)
                im.crop((0, 0, self.w, self.h)).save(png)
            except ImportError:
                pass
        print(f"[저장] {p}" + (f" · {png}" if os.path.exists(png) else " (PNG 없음)"))


def tw(s, size):
    """대략적인 글자 폭 (맑은 고딕): 한글 1.0em, 그 밖 0.56em"""
    return sum(size * (1.0 if ord(c) > 0x2E80 else 0.56) for c in str(s))


def title(svg, t, sub):
    svg.text(24, 38, t, 22, TXT, 700)
    svg.text(24, 62, sub, 12.5, DIM)


# ================================================================ 1. 번지 안
def io_map():
    rows = list(csv.DictReader(io.open(os.path.join(HERE, "fio_io_map_v6.csv"), encoding="utf-8-sig")))
    zones = []
    for r in rows:
        if not zones or zones[-1][0] != r["구역"]:
            zones.append((r["구역"], []))
        zones[-1][1].append(r)
    cols = [[], [], []]
    target = (len(rows) + len(zones) * 2) / 3
    ci, n = 0, 0
    for z in zones:                          # 구역을 세 칸에 나눠 담기 (구역이 길면 중간에서 이어짐)
        items = [("zone", z[0])] + [("row", r) for r in z[1]]
        for it in items:
            if n >= target and ci < 2 and it[0] == "row" and len(cols[ci]) > 3:
                ci, n = ci + 1, 0
                cols[ci].append(("zone", z[0] + " (이어서)"))
                n += 1.6
            cols[ci].append(it)
            n += 1.6 if it[0] == "zone" else 1
    RH, top = 19, 112
    h = top + int(max(sum(28 if k == "zone" else RH for k, _ in c) for c in cols)) + 92
    W = 1920
    svg = Svg(W, h)
    new = [r for r in rows if r["구분"].startswith("신규")]
    cnt = {k: sum(1 for r in new if r["번지"].startswith(k)) for k in "XYDM"}
    title(svg, "Project B — Factory I/O 센서 · 액추에이터 번지 안 (4-16 · v6)",
          f"1500~19FF 블록 (X·Y 16진 · M·D 10진) · 기존 번지 {len(rows) - len(new)}개는 그대로, 신규 {len(new)}개(X {cnt['X']} · Y {cnt['Y']} · D {cnt['D']})는 "
          "제안 — 월요일 F2~F4 확인 뒤 0-4 디바이스 표 · v7.html · mxopc_tags.py 에 반영")
    x0s = [24, 24 + 632, 24 + 1264]
    cw = 616
    for ci, col in enumerate(cols):
        x0, y = x0s[ci], top
        svg.rect(x0 - 8, top - 30, cw + 8, h - top - 62, PANEL, LINE, 1, rx=6)
        svg.text(x0 + 4, top - 12, "번지", 11, DIM, 700)
        svg.text(x0 + 62, top - 12, "방향", 11, DIM, 700)
        svg.text(x0 + 118, top - 12, "Factory I/O 부품 · 태그", 11, DIM, 700)
        svg.text(x0 + 370, top - 12, "설명", 11, DIM, 700)
        for kind, it in col:
            if kind == "zone":
                y += 8
                svg.rect(x0 - 2, y - 2, cw - 4, 20, "#30363F", rx=3)
                svg.text(x0 + 4, y + 13, it, 12.5, ORANGE, 700)
                y += 20
                continue
            r = it
            yy = y + 14
            isnew = r["구분"].startswith("신규")
            changed = "변경" in r["구분"]
            dcol = ORANGE if isnew else (YELLOW if changed else SUB)
            svg.text(x0 + 4, yy, r["번지"], 12, dcol, 700, extra=' font-family="Consolas, monospace"')
            d = r["방향"]
            if d.startswith("FIO"):
                svg.badge(x0 + 62, yy - 1, "입력", BLUE, 9.5, 4)
            elif d.startswith("PLC→"):
                svg.badge(x0 + 62, yy - 1, "출력", GREEN, 9.5, 4)
            else:
                svg.badge(x0 + 62, yy - 1, "내부", DIM, 9.5, 4)
            part = r["Factory I/O 부품(안)"]
            tag = r["Factory I/O 태그"]
            pt = f"{part} · {tag}" if tag and tag != "–" else part
            while tw(pt, 11) > 245:
                pt = pt[:-2] + "…"
            svg.text(x0 + 118, yy, pt, 11, TXT if isnew else SUB)
            desc = r["설명"]
            while tw(desc, 10.5) > cw - 372:
                desc = desc[:-2] + "…"
            svg.text(x0 + 370, yy, desc, 10.5, DIM)
            svg.line(x0, y + RH, x0 + cw - 12, y + RH, "#2E353E", 1)
            y += RH
    ly = h - 44
    bx = 24
    bx += svg.badge(bx, ly, "입력 = Factory I/O → PLC (센서)", BLUE, 11) + 10
    bx += svg.badge(bx, ly, "출력 = PLC → Factory I/O (액추에이터)", GREEN, 11) + 10
    svg.text(bx + 6, ly, "주황 번지 = 신규(안) · 노랑 = 뜻 바뀜(D1519) · 회색 = 기존 표에 있음", 11.5, SUB)
    svg.text(24, ly + 24, "근거: Factory I/O 2.5.10 설명서(설치 폴더 Documentation) · 기본 씬 태그 구성. Emitter · Remover는 씬에서 강제 ON(번지 없음). "
             "크레인은 Numerical 설정, Pop-up Wheel은 left/right/forward 3비트. 출처 표: computer_use/fio_io_map_v6.csv", 11, DIM)
    svg.save("io_map_v6")


# ================================================================ 2. AS/RS
def asrs():
    W, H = 1920, 1010
    svg = Svg(W, H)
    title(svg, "AS/RS — Factory I/O 랙으로 24칸(6열 × 4단) 만들기 · 크레인 A 입고 / 크레인 B 출고",
          "Factory I/O 랙 1개 = 3열 × 6단 = 18칸(설명서), 크레인 목표 칸 1~54. 랙 2개를 이어 6열로 두고 아래 4단만 씀. "
          "치수는 기본 씬 Automated Warehouse 기준(1칸 = 0.125 m) — 월요일 F2a에서 확인")
    # --- 위에서 본 배치 (축척 1 m = 46 px)
    S, ox, oy = 50, 64, 340
    svg.rect(24, 92, 900, 560, PANEL, LINE, 1, rx=6)
    svg.text(40, 118, "① 위에서 본 배치 (서 → 동 = 흐름 방향)", 14, TXT, 700)

    def X(m):
        return ox + m * S

    rack_x0, rack_len, depth = 3.75, 6.75, 1.25
    # 레일 (A 북쪽 · B 남쪽), 각 10.5 m: A = [0, 10.5], B = [3.75, 14.25]
    for name, z, x0, color, io_x, io_lbl in (("크레인 A 레일 (입고면)", -1.6, 0.0, BLUE, 0.9, "입고점 (로딩 컨베이어)"),
                                           ("크레인 B 레일 (출고면)", 1.6, 3.75, GREEN, 13.65, "출고점 (로딩 컨베이어)")):
        y = oy + z * S
        svg.rect(X(x0), y - 6, 10.5 * S, 12, "#3A3F46", "#6B7280", 1, rx=2)
        svg.text(X(x0 + 3.0) if z < 0 else X(x0) + 6, y - 12 if z < 0 else y + 26, f"{name} · 10.5 m", 12, color, 700)
        # 크레인
        cx = X(x0 + (2.0 if z < 0 else 8.5))
        svg.rect(cx - 16, y - 16, 32, 32, ORANGE, "#111827", 2, rx=3)
        svg.text(cx, y + 5, "A" if z < 0 else "B", 14, "#111827", 700, "middle")
        # 로딩 컨베이어 (레일 끝, 랙 반대쪽)
        lx = X(io_x)
        ly = y - 1.15 * S if z < 0 else y + 0.35 * S
        svg.rect(lx - 0.56 * S, ly, 1.125 * S, 0.8 * S, "#454B51", "#9AA3AB", 1, rx=2)
        if z < 0:
            svg.text(lx + 0.56 * S + 8, ly + 0.4 * S + 4, io_lbl, 11, SUB)
        else:
            svg.text(lx, ly + 0.8 * S + 15, io_lbl, 11, SUB, 400, "middle")
    # 랙 2개
    for i in range(2):
        rx = X(rack_x0 + i * 3.375)
        svg.rect(rx, oy - depth / 2 * S, 3.375 * S, depth * S, "#1F2937", "#9CA3AF", 1.5)
        for c in range(3):
            col = i * 3 + c
            fill = "#1E3A5F" if col < 3 else "#14432F"
            svg.rect(rx + c * 1.125 * S + 3, oy - depth / 2 * S + 3, 1.125 * S - 6, depth * S - 6, fill, "#4B5563", 1)
            svg.text(rx + (c + 0.5) * 1.125 * S, oy + 5, f"{col + 1}열", 12, BLUE if col < 3 else GREEN, 700, "middle")
        svg.text(rx + 3.375 * S / 2, oy + depth / 2 * S + 17, f"Rack {i + 1} (3열 × 6단)", 11, DIM, 400, "middle")
    # 흐름 화살표
    svg.line(X(-0.75), oy - 1.6 * S - 0.75 * S, X(0.3), oy - 1.6 * S - 0.75 * S, SUB, 2, ' marker-end="url(#arr)"')
    svg.text(X(-0.75), oy - 1.6 * S - 0.75 * S - 8, "입고 라인", 11, SUB)
    svg.line(X(14.25), oy + 1.6 * S + 0.75 * S, X(15.6), oy + 1.6 * S + 0.75 * S, SUB, 2, ' marker-end="url(#arr)"')
    svg.text(X(14.2), oy + 1.6 * S + 0.75 * S + 20, "→ 1차 분리", 11, SUB)
    # 치수
    dy = oy - depth / 2 * S - 12
    svg.line(X(rack_x0), dy, X(rack_x0 + rack_len), dy, DIM, 1)
    svg.line(X(rack_x0), dy - 5, X(rack_x0), dy + 5, DIM, 1)
    svg.line(X(rack_x0 + rack_len), dy - 5, X(rack_x0 + rack_len), dy + 5, DIM, 1)
    svg.text(X(rack_x0 + rack_len / 2), dy - 6, "랙 2개 6.75 m (1열 1.125 m)", 11, DIM, 400, "middle")
    notes = ["· 설명서: 랙은 레일 끝 한쪽에 맞춰야 크레인이 칸에 정확히 섬 → A는 동쪽 끝, B는 서쪽 끝에 랙을 맞춤",
             "· 랙은 앞뒤 양쪽에서 넣고 뺄 수 있음(단일 깊이) → 같은 랙을 A(북쪽)·B(남쪽)가 같이 씀 = 관통형",
             "· 크레인은 팔레트를 들어 옮김(기본 씬은 Pallet + Box). 박스만으로 되는지는 F2b에서 확인(A28)",
             "· 숫자 치수는 추정: 1칸 0.125 m, 랙 27칸 = 3.375 m, 레일 10.5 m(설명서), 로딩 컨베이어 1.125 m"]
    for i, n in enumerate(notes):
        svg.text(40, 560 + i * 20, n, 11.5, SUB)
    # --- 정면도: 6열 × 6단, 아래 4단 사용
    fx, fy, cw_, ch_ = 980, 160, 140, 62
    svg.rect(950, 92, 946, 560, PANEL, LINE, 1, rx=6)
    svg.text(966, 118, "② 랙 정면 (크레인 A 쪽에서 봄) · R번호 = (단 − 1) × 6 + 열", 14, TXT, 700)
    for lv in range(6, 0, -1):
        y = fy + (6 - lv) * ch_
        svg.text(fx - 8, y + ch_ / 2 + 5, f"{lv}단", 12, DIM, 700, "end")
        for c in range(1, 7):
            x = fx + 18 + (c - 1) * cw_ + (12 if c > 3 else 0)
            if lv > 4:
                svg.rect(x, y + 3, cw_ - 6, ch_ - 6, "url(#hatch)", "#4B5563", 1, rx=3)
                if c == 1:
                    svg.text(x + 8, y + 22, "5~6단 사용 안 함", 11, DIM)
                continue
            r = (lv - 1) * 6 + c
            is4 = c <= 3
            svg.rect(x, y + 3, cw_ - 6, ch_ - 6, "#1E3A5F" if is4 else "#14432F", BLUE if is4 else GREEN, 1.2, rx=3)
            svg.text(x + 10, y + 26, f"R{r:02d}", 15, TXT, 700)
            svg.text(x + 10, y + 46, f"LOCK D{1609 + r}", 10.5, SUB, 400, extra=' font-family="Consolas, monospace"')
            svg.text(x + cw_ - 14, y + 26, "4S" if is4 else "6S", 11, BLUE if is4 else GREEN, 700, "end")
    for c in range(1, 7):
        x = fx + 18 + (c - 1) * cw_ + (12 if c > 3 else 0)
        svg.text(x + (cw_ - 6) / 2, fy + 6 * ch_ + 20, f"{c}열", 12, BLUE if c <= 3 else GREEN, 700, "middle")
    svg.text(fx + 18 + 1.5 * cw_, fy + 6 * ch_ + 40, "Rack 1 · 4S 구역 (Small box)", 12, BLUE, 700, "middle")
    svg.text(fx + 30 + 4.5 * cw_, fy + 6 * ch_ + 40, "Rack 2 · 6S 구역 (Large box)", 12, GREEN, 700, "middle")
    svg.text(966, 640, "칸 번호 · LOCK 경과 시간(D1610~D1633) 순서는 v7.html 2D 시뮬레이터(idx = 행 × 6 + 열)와 같음. "
             "HMI 격자는 1단을 아래에 그림.", 11, DIM)
    # --- 목표 칸 확인 표
    ty = 676
    svg.rect(24, ty, 1872, 310, PANEL, LINE, 1, rx=6)
    svg.text(40, ty + 28, "③ 크레인 목표 칸(1~54) ↔ R번호 — 설명서에 번호 매기는 순서가 없어 월요일 F2a에서 정합니다", 14, TXT, 700)
    steps = [("1", "크레인 A에 목표 1 → 멈춘 칸을 기록 (몇 번째 랙 · 열 · 단)", "fio_modbus.py crane --target 1"),
             ("2", "목표 2 · 3 · 4 → 번호가 열 방향(→)으로 느는지, 단 방향(↑)으로 느는지", "--target 2 / 3 / 4"),
             ("3", "목표 18 · 19 → 랙 1 끝과 랙 2 시작이 맞는지 (랙당 18칸)", "--target 18 / 19"),
             ("4", "목표 55 → 대기 위치. 0 = 그 자리 정지", "--target 55"),
             ("5", "크레인 B로 같은 시험 (반대쪽에서 보므로 열 순서가 거꾸로일 수 있음)", "--prefix \"Crane B\""),
             ("6", "결과로 R번호 → 목표 칸 변환표를 채우고 래더(D1600 → D1601 · D1602)에 반영", "4-15 래더 설계서")]
    for i, (n, s, cmd) in enumerate(steps):
        y = ty + 62 + i * 36
        svg.circle(54, y - 4, 11, ORANGE)
        svg.text(54, y + 1, n, 12, "#111827", 700, "middle")
        svg.text(76, y, s, 13, SUB)
        svg.text(1180, y, cmd, 12, GREEN, 400, extra=' font-family="Consolas, monospace"')
    svg.text(40, ty + 290, "가정(확인 전): 목표 칸 = (랙 − 1) × 18 + (단 − 1) × 3 + 랙 안 열 → R01 = 1, R02 = 2, R03 = 3, R04 = 19, R07 = 4 … 결과가 다르면 이 줄을 고칩니다.",
             12, YELLOW)
    svg.save("asrs_fio_v6")


# ================================================================ 3. C7 화면
def c7():
    W, H = 1920, 900
    svg = Svg(W, H)
    title(svg, "C7 — WinGP ↔ 중계 서버(hmi_mc_relay.py) 접속 시험 화면 작화 지시 (GP-Pro EX 4.08)",
          "10장 C7. 화면 크기 1024 × 768 기준 좌표(px). 번지는 실물 PLC용 화면과 같음 — Project C 환경에서는 IP만 실물 PLC로 바꿈 (D20)")
    sx, sy, k = 40, 96, 0.92            # 화면 미리보기 (1024 × 768 → 0.92배)

    def P(x, y):
        return sx + x * k, sy + y * k

    svg.rect(sx - 6, sy - 6, 1024 * k + 12, 768 * k + 12, "#0B0F14", "#6B7280", 2, rx=8)
    svg.rect(sx, sy, 1024 * k, 768 * k, "#10151C")
    x, y = P(20, 20)
    svg.text(x, y + 18, "C7 접속 시험 · 중계 서버 127.0.0.1:5000", 20 * k, TXT, 700)
    objs = [("D1900", "GOOD", 40), ("D1901", "NG", 230), ("D1902", "발열 격리", 420), ("D1903", "합계", 610), ("D1904", "수율 0.1%", 800)]
    for dev, lbl, ox in objs:
        x, y = P(ox, 110)
        svg.text(x + 4, y - 8, f"{lbl}", 15 * k, SUB, 700)
        x, y = P(ox, 120)
        svg.rect(x, y, 170 * k, 90 * k, "#000000", "#9CA3AF", 1.5, rx=4)
        svg.text(x + 160 * k, y + 60 * k, "00000", 34 * k, RED, 700, "end", ' font-family="Consolas, monospace"')
        svg.text(x + 2, y + 90 * k + 16, f"{dev} 숫자 표시", 11, ORANGE, 700)
        svg.text(x + 2, y + 90 * k + 31, f"({ox}, 120) 170 × 90", 10.5, ORANGE)
    x, y = P(40, 300)
    svg.circle(x + 50 * k, y + 50 * k, 48 * k, "#14532D", "#9CA3AF", 2)
    svg.text(x + 50 * k, y + 56 * k, "X1900", 14 * k, TXT, 700, "middle")
    svg.text(x, y + 100 * k + 16, "X1900 비트 램프", 11, ORANGE, 700)
    svg.text(x, y + 100 * k + 31, "(40, 300) 100 × 100", 10.5, ORANGE)
    x, y = P(200, 300)
    svg.rect(x, y, 220 * k, 100 * k, "#1D4ED8", "#93C5FD", 2, rx=8)
    svg.text(x + 110 * k, y + 58 * k, "카운터 리셋 M1920", 17 * k, TXT, 700, "middle")
    svg.text(x, y + 100 * k + 16, "M1920 비트 스위치 (모멘터리)", 11, ORANGE, 700)
    svg.text(x, y + 100 * k + 31, "(200, 300) 220 × 100", 10.5, ORANGE)
    x, y = P(40, 470)
    for i, s in enumerate(["확인 1: D1900이 1초마다 1씩 늘고 D1903(합계)도 같이 바뀜 (--demo)",
                           "확인 2: X1900 램프가 깜박임",
                           "확인 3: 리셋 버튼을 누르면 중계 콘솔에 '쓰기 M1920 … = [1]', 카운터 0",
                           "글자 · 좌표는 대략이어도 됨. 번지만 정확히 넣을 것"]):
        svg.text(x, y + i * 26 * k + 20, s, 14 * k, SUB if i < 3 else DIM)
    # 오른쪽: 설정 표
    rx0, ry0 = 1020, 96
    svg.rect(rx0, ry0 - 6, 876, 720, PANEL, LINE, 1, rx=6)
    svg.text(rx0 + 18, ry0 + 22, "GP-Pro EX 새 프로젝트 설정", 16, TXT, 700)
    rows = [("프로젝트 파일", "test_results/C7_hmi.prx (새 이름, 원본 아님)"),
            ("표시기 종류", "WinGP (PC 런타임) — 해상도 1024 × 768"),
            ("장치/PLC 제조사", "Mitsubishi Electric Corporation"),
            ("장치/PLC 시리즈", "Q Series QnU CPU Ethernet  (드라이버 MIT_QNUE)"),
            ("CPU", "Q03UDE (시뮬레이션 기종, 실물은 Q03UDV → 12장 P4)"),
            ("IP 주소", "127.0.0.1 (중계 서버가 같은 PC) · 2단계도 같음"),
            ("포트", "5000"),
            ("프로토콜", "TCP (UDP는 선택 시험)"),
            ("데이터 코드", "Binary (바이너리)"),
            ("화면 1", "위 그림: 숫자 표시 5 · 램프 1 · 스위치 1"),
            ("전송 · 실행", "프로젝트 → WinGP로 전송 → PCRuntime.exe 실행. 키 없으면 체험판, 시작 시각 기록"),
            ("중계 서버 (먼저 실행)", "1단계: python hmi_mc_relay.py --backend memory --demo --verbose"),
            ("", "2단계: python hmi_mc_relay.py --backend opc --opc-device CSIM --verbose"),
            ("방화벽 창", "개인 네트워크 허용 (사람이 누름)"),
            ("스크린샷", "C7_장치설정.png · C7_WinGP.png · C7_중계콘솔.png → test_results/")]
    for i, (a, b) in enumerate(rows):
        y = ry0 + 60 + i * 41
        svg.line(rx0 + 14, y + 14, rx0 + 860, y + 14, "#2E353E", 1)
        svg.text(rx0 + 18, y, a, 13, ORANGE if a else DIM, 700)
        svg.text(rx0 + 230, y, b, 13, TXT if a else SUB, 400,
                 ' font-family="Consolas, Malgun Gothic, monospace"' if b.startswith("python") else "")
    svg.text(40, H - 40, "2단계(MX OPC · GX Simulator2까지)는 MX OPC 장치 CSIM 의 Transfer Setup을 GX Simulator2로 바꾸고 Simulate를 끈 뒤 진행 "
             "(월요일 작업 3). 중계 서버는 C059(미지원 명령) 번호를 콘솔에 남김.", 12, DIM)
    svg.save("c7_wingp_screen")


# ================================================================ 4. 월요일 흐름
def flow():
    W, H = 1920, 1080
    svg = Svg(W, H)
    title(svg, "월요일(11-23) Project B — Computer Use 작업 순서와 연결 구성",
          "화면 조작(Computer Use)은 GX Works2 · MX OPC Configurator · GP-Pro EX/WinGP · Factory I/O, 명령은 Claude Code가 직접 실행. "
          "실물 PLC 없음 — GX Simulator2만 씀")
    # 연결 구성
    svg.rect(24, 88, 1100, 380, PANEL, LINE, 1, rx=6)
    svg.text(40, 114, "① 연결 구성 (D17 · D20 · D21)", 14, TXT, 700)

    def node(x, y, w, h, t, s, color):
        svg.rect(x, y, w, h, "#1F2630", color, 2, rx=8)
        svg.text(x + w / 2, y + 26, t, 14, TXT, 700, "middle")
        svg.text(x + w / 2, y + 46, s, 11, DIM, 400, "middle")

    node(48, 228, 220, 64, "GX Simulator2", "GX Works2 W_test.gxw · 래더", VIOLET)
    node(380, 228, 240, 64, "MX OPC Server 6.10", "장치 CSIM → GX Simulator2", BLUE)
    node(760, 132, 330, 64, "Factory I/O (OPC Client DA)", "v6 씬 · 태그 = 디바이스 이름", GREEN)
    node(760, 228, 330, 64, "Python serve · HMI 모니터", "measurement_engine.py · plc_link", YELLOW)
    node(760, 324, 330, 64, "hmi_mc_relay.py (MC 3E, 5000)", "↔ WinGP (Pro-face) 화면", ORANGE)
    svg.line(268, 260, 378, 260, SUB, 2, ' marker-end="url(#arr)"')
    for yy in (164, 260, 356):
        svg.line(620, 260, 758, yy, SUB, 1.6, ' marker-end="url(#arr)"')
    node(48, 360, 300, 64, "Factory I/O (Modbus TCP Server)", "F2~F4 시험 씬 전용 · 127.0.0.1:502", "#6B7280")
    node(380, 360, 240, 64, "fio_modbus.py", "크레인 · RFID · 센서 값", "#6B7280")
    svg.line(348, 392, 378, 392, SUB, 1.6, ' marker-end="url(#arr)"')
    svg.text(48, 448, "Factory I/O 드라이버는 한 번에 하나뿐 → 시험(F2~F4)은 Modbus, 공정 씬(v6)은 OPC", 11.5, DIM)
    # F2에서 정할 것
    svg.rect(1140, 88, 756, 380, PANEL, LINE, 1, rx=6)
    svg.text(1156, 114, "② 설명서로 미리 찾은 것 → F2에서 확인하고 정함", 14, TXT, 700)
    finds = [(RED, "비전 센서는 박스를 못 알아봄", "원료 · 뚜껑 · 받침만 인식(설명서). D1519 박스 크기는 높이 센서 X1511로 (A26)"),
             (ORANGE, "랙 1개 = 3열 × 6단 = 18칸", "랙 2개 · 아래 4단 = 24칸. 목표 칸 번호 순서는 F2a에서 (그림 asrs_fio_v6)"),
             (ORANGE, "크레인은 팔레트 단위", "박스만 넣고 빼지는지 F2b. 안 되면 팔레트 + 박스로 라인 전체를 갈지 (A28)"),
             (YELLOW, "RFID는 태그 1개만 읽음", "팔레트와 박스 둘 다 태그가 있으면 Status 2. 리더 높이로 피하는지 F3"),
             (GREEN, "Emitter를 PLC가 고름", "Part 비트 1 = Small · 4 = Large → D1508 (C 인계 셀 수로)"),
             (GREEN, "씬 파일로 드라이버 연결", "Modbus = 32 · OPC = 16384. fio_scene.py 로 태그 연결 · 이름 바꾸기")]
    for i, (c, a, b) in enumerate(finds):
        y = 150 + i * 52
        svg.rect(1156, y - 14, 6, 38, c, rx=2)
        svg.text(1174, y, a, 13.5, TXT, 700)
        svg.text(1174, y + 19, b, 11.5, SUB)
    # 순서
    svg.rect(24, 486, 1872, 566, PANEL, LINE, 1, rx=6)
    svg.text(40, 512, "③ 월요일 순서 (위에서부터, 막히면 그 단계 결과를 '확인 불가 + 이유'로 적고 다음으로)", 14, TXT, 700)
    steps = [
        ("0", "사람", "Claude 앱에서 Computer use 켜기 · Factory I/O 라이선스 · 작업 PC 결정", "설정 → Computer use / 라이선스 코드", "준비물 표"),
        ("1", "명령", "점검: python computer_use/preflight.py --opc", "NG 0개면 진행", "5분"),
        ("2", "화면", "C7 1단계: 중계 서버(memory) + GP-Pro EX 화면 → WinGP 접속", "c7_wingp_screen 그림대로", "40분"),
        ("3", "화면", "MX OPC Configurator: CSIM Transfer Setup = GX Simulator2, Simulate 끄기", "쓰기 · 복원 시험", "20분"),
        ("4", "화면", "GX Works2: W_test.gxw 열기 → 시뮬레이션 시작(RUN)", "X1900 ON 3회 → D1900 = 3", "15분"),
        ("5", "명령", "serve 핸드셰이크 3개(D1710 · D1740 · D1650) OPC로 · C7 2단계", "DB 기록 · WinGP 값 일치", "30분"),
        ("6", "화면", "F2: 시험 씬 6개를 차례로 열고(load:) 박스 · 랙 · 분기 · 비전 확인", "fio_modbus.py 로 크레인 · 센서", "60분"),
        ("7", "화면", "F3 · F4: RFID Reader 3개 끌어 놓기 → 저장 → map-modbus → rfid-check", "Status · 시리얼 · 22200/40000", "40분"),
        ("8", "명령", "결과를 11장 표 · 15장에 숫자와 함께 기록, A26~A28 정리, 스크린샷 test_results/", "실기 · 시뮬레이션 구분", "20분"),
    ]
    hx = [40, 92, 160, 1010, 1520]
    for j, hname in enumerate(["#", "누가", "할 일", "완료 기준 / 참고", "예상"]):
        svg.text(hx[j], 544, hname, 11, DIM, 700)
    for i, (n, who, s, ok, t) in enumerate(steps):
        y = 572 + i * 52
        svg.rect(32, y - 22, 1856, 44, "#1F2630" if i % 2 == 0 else PANEL, rx=4)
        svg.circle(52, y - 1, 13, ORANGE if who == "화면" else (GREEN if who == "명령" else RED))
        svg.text(52, y + 4, n, 13, "#111827", 700, "middle")
        svg.badge(92, y + 4, who, ORANGE if who == "화면" else (GREEN if who == "명령" else RED), 11, 6)
        svg.text(160, y + 4, s, 13.5, TXT)
        svg.text(1010, y + 4, ok, 12.5, SUB)
        svg.text(1520, y + 4, t, 12.5, DIM)
    svg.save("monday_flow")


if __name__ == "__main__":
    io_map()
    asrs()
    c7()
    flow()
