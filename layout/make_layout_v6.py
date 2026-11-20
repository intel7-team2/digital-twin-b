"""
Project B 상면(Top view) 레이아웃 생성기 — v6 (v5 + 정치 버퍼 삭제, 연속 재검사 라인)
- 좌표는 3d_layout.html 과 같은 미터 단위 (X = 동쪽/흐름 방향, Z = 남쪽 +, 북쪽 −)
- 출력: layout_v6.drawio (draw.io 에서 수정), layout_v6.svg (미리보기)
실행: python make_layout_v6.py
"""
import html
import os

S = 40          # px per meter
XMIN, XMAX = -17.0, 25.5
ZMIN, ZMAX = -7.4, 4.6
MX, MY = 30, 70  # margins (top margin holds the title)
W = int((XMAX - XMIN) * S + 2 * MX)
H = int((ZMAX - ZMIN) * S + MY + 40)


def px(x):
    return (x - XMIN) * S + MX


def pz(z):
    return (z - ZMIN) * S + MY


shapes = []   # (kind, data)


def rect(x0, z0, x1, z1, label, fill, stroke, font=11, bold=False, dashed=False):
    shapes.append(('rect', dict(x=px(x0), y=pz(z0), w=(x1 - x0) * S, h=(z1 - z0) * S,
                                label=label, fill=fill, stroke=stroke, font=font, bold=bold, dashed=dashed)))


def belt(points, color, label=None, width=0.5):
    shapes.append(('belt', dict(pts=[(px(x), pz(z)) for x, z in points], color=color,
                                w=width * S, label=label)))


def text(x, z, label, color='#1F2937', font=11, bold=False, w=4.0, anchor='middle'):
    shapes.append(('text', dict(x=px(x), y=pz(z), label=label, color=color, font=font, bold=bold, w=w * S, anchor=anchor)))


# Geometry for v4 (structure B): one aging rack (4S/6S, cranes A·B) + main tester + dedicated retest tester.
# The RETEST loop sits on the south side next to the NG line so no conveyor has to cross the main line.
RAIL_IN_Z, RAIL_OUT_Z = -1.3, 1.3
INSP_X = 4.5
GATE_X = 22.0
RETEST_X = 6.5                     # main line → RETEST branch (M1720, south)
RET_Z = 2.0                        # RETEST loop level
BUF_X0, BUF_N, BUF_PITCH = 7.2, 8, 0.5
BUF_X1 = BUF_X0 + (BUF_N - 1) * BUF_PITCH
RT_X = 12.6                        # retest tester
SORT1_X = 1.6                      # 1차 분리 (출고 라인이 북쪽으로 꺾이는 지점) Pop-up Wheel: hot → south isolation (M1661) / normal → straight (M1660)
SORT2_X = 14.5                     # 2차 분리 Pop-up Wheel: GOOD → north merge (M1731) / NG → south NG OUT (M1732)
NG_Z = 3.6
SORT1_Z = RAIL_OUT_Z
CHAMBER = (SORT1_X, 2.95)

BLUE, ORANGE, RED, GREEN, GREY = '#38BDF8', '#F59E0B', '#EF4444', '#10B981', '#94A3B8'

# ---------------------------------------------------------------- aging rack (4S / 6S zones)
ZONES = [
    ('4S 구역 1~3열 (Small box)', 3, 1.4, '#EFF6FF', '#93C5FD', '#1D4ED8'),
    ('6S 구역 4~6열 (Large box)', 3, 1.4, '#ECFDF5', '#6EE7B7', '#047857'),
]
RACK_X0 = -8.0
x = RACK_X0
bay_no = 1
for name, n, wid, fill, stroke, col in ZONES:
    start = x
    for _ in range(n):
        rect(x, -0.5, x + wid, 0.5, f'R{bay_no:02d}~\n(4단)', fill, stroke, 9)
        x += wid
        bay_no += 1
    text((start + x) / 2, 0.85, name, col, 9, True, w=x - start + 1)
RACK_X1 = x
text((RACK_X0 + RACK_X1) / 2, -2.6, f'에이징 AS/RS {bay_no - 1}열 × 4단 = {(bay_no - 1) * 4}칸 (칸 크기 동일 · 구역별 12칸) · 보관 중 온도 감시(가상)', '#1D4ED8', 11, True, w=12)
PICK_IN = RACK_X0 - 0.8
DROP_OUT = RACK_X1 + 0.4

# ---------------------------------------------------------------- conveyors
belt([(-16, 0), (-10, 0), (-10, RAIL_IN_Z), (PICK_IN, RAIL_IN_Z)], BLUE, '투입 컨베이어')
belt([(DROP_OUT, RAIL_OUT_Z), (1.6, RAIL_OUT_Z), (1.6, 0), (GATE_X, 0)], BLUE, '메인 라인')
belt([(RETEST_X, 0.3), (RETEST_X, RET_Z), (SORT2_X, RET_Z), (SORT2_X, 0.3)], ORANGE, None)
belt([(SORT2_X, RET_Z + 0.4), (SORT2_X, NG_Z), (GATE_X, NG_Z)], RED, None)
text(18.0, 3.1, 'NG 라인 (2차 분리 ↓ · 메인 NG + 재검사 NG)', '#B91C1C', 9, w=6)
belt([(SORT1_X, SORT1_Z + 0.3), (SORT1_X, CHAMBER[1] - 0.65)], '#B91C1C', None, 0.35)

# ---------------------------------------------------------------- STEP 01
rect(-16.9, -1.1, -14.7, 1.1, 'Project C 인계\n4S = 작은 박스\n6S = 큰 박스', '#F1F5F9', GREY, 9)
rect(-13.6, 0.4, -12.8, 1.0, '비전\n(D1519)', '#E0F2FE', BLUE, 9)
rect(-12.0, -1.0, -11.0, -0.4, 'RFID ①\nD1510~17', '#E0F2FE', BLUE, 9, True)
text(-12.4, 1.5, 'STEP 01 스토퍼 · 종류 판별 → 구역 지정', '#0369A1', 9, w=6)

# ---------------------------------------------------------------- rack rails / isolation
rect(RACK_X0 - 1.2, RAIL_IN_Z - 0.15, RACK_X1 + 0.3, RAIL_IN_Z + 0.15, '', '#BFDBFE', '#2563EB')
text((RACK_X0 + RACK_X1) / 2, RAIL_IN_Z - 0.55, '입고면 · 크레인 A (M1600) — 종류별 구역 입고', '#1D4ED8', 9, w=10)
rect(RACK_X0 - 1.4, RAIL_OUT_Z - 0.15, DROP_OUT + 0.3, RAIL_OUT_Z + 0.15, '', '#BAE6FD', '#0284C7')
text((RACK_X0 + RACK_X1) / 2, RAIL_OUT_Z + 0.55, '출고면 · 크레인 B (M1601) — 모든 팩 동쪽 출구 (발열 우선 → EDD)', '#0369A1', 9, w=11)
rect(CHAMBER[0] - 0.65, CHAMBER[1] - 0.65, CHAMBER[0] + 0.65, CHAMBER[1] + 0.65,
     'M1690\n발열 격리\nX1902/D1902\nDB ISO', '#FEE2E2', RED, 9, True, True)
rect(SORT1_X - 0.35, SORT1_Z - 0.35, SORT1_X + 0.35, SORT1_Z + 0.35, 'PW', '#D1FAE5', GREEN, 8, True)
rect(SORT1_X + 0.5, SORT1_Z - 0.3, SORT1_X + 2.0, SORT1_Z + 0.3, '1차 분리\nM1660 / M1661', '#ECFDF5', GREEN, 8, True)
text(SORT1_X - 0.9, 2.05, '발열 ↓', '#B91C1C', 9, True, w=2)

# ---------------------------------------------------------------- main tester
rect(INSP_X - 0.6, -0.6, INSP_X + 0.6, 0.6, 'STEP 03\n메인 검사\nOCV·IR·온도\nM1700', '#FEF3C7', ORANGE, 8, True)
rect(INSP_X - 0.55, -1.25, INSP_X + 0.15, -0.75, 'RFID ②\nD1520~27', '#E0F2FE', BLUE, 8, True)
text(INSP_X, -1.7, '1차 측정 → D1700~03', '#92400E', 9, w=4)
rect(RETEST_X - 0.35, 0.35, RETEST_X + 0.35, 0.75, 'M1720', '#FEF3C7', ORANGE, 8, True)

# ---------------------------------------------------------------- retest loop (south)
# v6: no rest buffer — continuous retest line, packs queue in front of the retest tester only while it is busy
text(RETEST_X + 0.5, RET_Z + 0.8, '재검사 라인 (RETEST + 메인 NG) · 정치 없이 연속 · D1800', '#B45309', 9, True, w=9, anchor='start')
text(RETEST_X + 0.5, RET_Z - 0.55, '→ 재검사기 앞 줄 서기 · 분기점까지 차면 M1800', '#B45309', 8, w=9, anchor='start')
rect(RT_X - 0.6, RET_Z - 0.6, RT_X + 0.6, RET_Z + 0.6, '재검사\nOCV·IR·온도\nM1730\nD1730~33', '#FEF3C7', ORANGE, 8, True)
rect(RT_X - 0.35, RET_Z - 1.15, RT_X + 0.35, RET_Z - 0.7, 'RFID ③\nD1530~37', '#E0F2FE', BLUE, 7, True)
rect(SORT2_X - 0.35, RET_Z - 0.35, SORT2_X + 0.35, RET_Z + 0.35, 'PW', '#D1FAE5', GREEN, 8, True)
text(SORT2_X + 0.55, RET_Z + 0.05, '2차 분리 (Pop-up Wheel): ↑ M1731 GOOD 합류 / ↓ M1732 NG OUT', '#047857', 9, True, w=7, anchor='start')
text(SORT2_X + 0.6, -0.65, '↓ 재검사 GOOD 합류 (X1903 간격 확인)', '#B45309', 9, w=6)
text(9.5, -1.35, '메인 라인: GOOD → GOOD OUT / RETEST·NG → M1720 (M1710 라인 없음)', '#047857', 9, True, w=9)

# ---------------------------------------------------------------- gates
rect(GATE_X, -0.5, GATE_X + 2.6, 0.5, 'GOOD OUT\nX1900 → D1900', '#D1FAE5', GREEN, 10, True)
rect(GATE_X, NG_Z - 0.5, GATE_X + 2.6, NG_Z + 0.5, 'NG OUT\nX1901 → D1901', '#FEE2E2', RED, 10, True)
text(GATE_X + 1.3, -1.2, 'STEP 05 게이트 · HMI (M1920 리셋)', '#047857', 10, True, w=6)

rect(15.6, -7.0, 25.2, -3.3,
     'v6 (v5 + 정치 버퍼 삭제)\n'
     '· 랙 1개 · 크레인 2대 (A 입고 / B 출고)\n'
     '· 검사기 2대: 메인(RFID②) · 재검사(RFID③), 둘 다 OCV·IR·온도\n'
     '· 1차 분리: 발열 팩 ↓ 격리 (DB ISO) / 정상 → 메인 검사\n'
     '· 2차 분리: 재검사 후 GOOD ↑ 합류 / NG ↓ NG OUT\n'
     '· 메인 NG도 재검사 라인 → 재검사기 통과 (계측 생략) → NG OUT\n'
     '· 삭제: 정치 버퍼 8칸(v6) · M1710 라인 · M1650 · 루프백 · BYPASS\n'
     '· 랙 6열 × 4단 = 24칸, 칸 크기 동일 (4S 1~3열 · 6S 4~6열)\n'
     '· 카운터 D1900 GOOD · D1901 NG · D1902 격리 · D1903 합계 · D1904 수율',
     '#F8FAFC', '#64748B', 10, False, True)

text(XMIN + 0.3, ZMIN - 1.2, 'Project B 상면 레이아웃 — v6 (정치 버퍼 없는 연속 재검사 라인 · 1차/2차 분리) · 1칸 = 1 m', '#0F172A', 15, True, w=24, anchor='start')
text(XMIN + 0.3, ZMIN - 0.55, '흐름: 투입 → RFID①·비전 → 랙 4S/6S 숙성(온도 감시) → 크레인 B 동쪽 출구 → 1차 분리(발열 ↓ 격리) → RFID② 메인 검사 → GOOD / RETEST·NG → 재검사 라인(연속) → RFID③ 재검사기 → 2차 분리(GOOD ↑ 합류 / NG ↓)', '#475569', 10, w=34, anchor='start')


# ---------------------------------------------------------------- SVG
def svg():
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
           'font-family="Malgun Gothic, Pretendard, sans-serif">',
           f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>']
    # 1 m grid
    x = XMIN
    while x <= XMAX + 1e-9:
        out.append(f'<line x1="{px(x):.1f}" y1="{pz(ZMIN):.1f}" x2="{px(x):.1f}" y2="{pz(ZMAX):.1f}" stroke="#F1F5F9"/>')
        x += 1
    z = ZMIN
    while z <= ZMAX + 1e-9:
        out.append(f'<line x1="{px(XMIN):.1f}" y1="{pz(z):.1f}" x2="{px(XMAX):.1f}" y2="{pz(z):.1f}" stroke="#F1F5F9"/>')
        z += 1
    out.append('<defs><marker id="ar" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto">'
               '<path d="M0,0 L6,3 L0,6 z" fill="#334155"/></marker></defs>')
    for kind, d in shapes:
        if kind == 'belt':
            pts = ' '.join(f'{a:.1f},{b:.1f}' for a, b in d['pts'])
            out.append(f'<polyline points="{pts}" fill="none" stroke="#CBD5E1" stroke-width="{d["w"]:.1f}" stroke-linejoin="round"/>')
            out.append(f'<polyline points="{pts}" fill="none" stroke="{d["color"]}" stroke-width="2.5" stroke-dasharray="8 6" marker-end="url(#ar)"/>')
    for kind, d in shapes:
        if kind == 'rect':
            dash = ' stroke-dasharray="6 4"' if d['dashed'] else ''
            out.append(f'<rect x="{d["x"]:.1f}" y="{d["y"]:.1f}" width="{d["w"]:.1f}" height="{d["h"]:.1f}" rx="4" '
                       f'fill="{d["fill"]}" stroke="{d["stroke"]}" stroke-width="1.5"{dash}/>')
            lines = d['label'].split('\n') if d['label'] else []
            cy = d['y'] + d['h'] / 2 - (len(lines) - 1) * d['font'] * 0.6
            for i, ln in enumerate(lines):
                out.append(f'<text x="{d["x"] + d["w"] / 2:.1f}" y="{cy + i * d["font"] * 1.2 + d["font"] * 0.35:.1f}" '
                           f'text-anchor="middle" font-size="{d["font"]}" font-weight="{700 if d["bold"] else 400}" '
                           f'fill="#0F172A">{html.escape(ln)}</text>')
        elif kind == 'text':
            out.append(f'<text x="{d["x"]:.1f}" y="{d["y"]:.1f}" text-anchor="{d["anchor"]}" font-size="{d["font"]}" '
                       f'font-weight="{700 if d["bold"] else 400}" fill="{d["color"]}">{html.escape(d["label"])}</text>')
    for kind, d in shapes:
        if kind == 'belt' and d['label']:
            segs = list(zip(d['pts'], d['pts'][1:]))
            (a, b), (c, e) = max(segs, key=lambda q: abs(q[0][0] - q[1][0]) + abs(q[0][1] - q[1][1]))
            out.append(f'<text x="{(a + c) / 2:.1f}" y="{(b + e) / 2 - d["w"] / 2 - 4:.1f}" text-anchor="middle" '
                       f'font-size="9" fill="#475569">{html.escape(d["label"])}</text>')
    out.append('</svg>')
    return '\n'.join(out)


# ---------------------------------------------------------------- draw.io
def drawio():
    cells = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']
    n = 2

    def nid():
        nonlocal n
        n += 1
        return f'c{n}'

    esc = lambda s: html.escape(s, quote=True).replace('\n', '&#xa;')
    for kind, d in shapes:
        if kind == 'belt':
            pts = d['pts']
            inner = ''.join(f'<mxPoint x="{a:.1f}" y="{b:.1f}"/>' for a, b in pts[1:-1])
            style = (f'endArrow=block;endFill=1;html=1;rounded=0;strokeWidth={max(6, d["w"] * 0.6):.0f};'
                     f'strokeColor={d["color"]};opacity=70;fontSize=9;')
            cells.append(f'<mxCell id="{nid()}" value="{esc(d["label"] or "")}" style="{style}" edge="1" parent="1">'
                         f'<mxGeometry relative="1" as="geometry">'
                         f'<mxPoint x="{pts[0][0]:.1f}" y="{pts[0][1]:.1f}" as="sourcePoint"/>'
                         f'<mxPoint x="{pts[-1][0]:.1f}" y="{pts[-1][1]:.1f}" as="targetPoint"/>'
                         f'<Array as="points">{inner}</Array></mxGeometry></mxCell>')
    for kind, d in shapes:
        if kind == 'rect':
            style = (f'rounded=1;arcSize=8;whiteSpace=wrap;html=1;fillColor={d["fill"]};strokeColor={d["stroke"]};'
                     f'fontSize={d["font"]};fontStyle={1 if d["bold"] else 0};' + ('dashed=1;' if d['dashed'] else ''))
            cells.append(f'<mxCell id="{nid()}" value="{esc(d["label"])}" style="{style}" vertex="1" parent="1">'
                         f'<mxGeometry x="{d["x"]:.1f}" y="{d["y"]:.1f}" width="{d["w"]:.1f}" height="{d["h"]:.1f}" as="geometry"/></mxCell>')
        elif kind == 'text':
            align = 'left' if d['anchor'] == 'start' else 'center'
            x = d['x'] if align == 'left' else d['x'] - d['w'] / 2
            style = (f'text;html=1;align={align};verticalAlign=middle;fontSize={d["font"]};'
                     f'fontStyle={1 if d["bold"] else 0};fontColor={d["color"]};')
            cells.append(f'<mxCell id="{nid()}" value="{esc(d["label"])}" style="{style}" vertex="1" parent="1">'
                         f'<mxGeometry x="{x:.1f}" y="{d["y"] - 12:.1f}" width="{d["w"]:.1f}" height="20" as="geometry"/></mxCell>')
    model = (f'<mxGraphModel dx="{W}" dy="{H}" grid="1" gridSize="{S // 4}" guides="1" tooltips="1" connect="1" arrows="1" '
             f'fold="1" page="1" pageScale="1" pageWidth="{W}" pageHeight="{H}" math="0" shadow="0">'
             f'<root>{"".join(cells)}</root></mxGraphModel>')
    return f'<mxfile host="Electron"><diagram id="top" name="상면 레이아웃 v4">{model}</diagram></mxfile>'


here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, 'layout_v6.svg'), 'w', encoding='utf-8') as f:
    f.write(svg())
with open(os.path.join(here, 'layout_v6.drawio'), 'w', encoding='utf-8') as f:
    f.write(drawio())
print('written', W, H)
