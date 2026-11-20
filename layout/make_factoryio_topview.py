"""
Project B 상면도 — Factory I/O 부품 기준 (v6 구조)
- 좌표는 make_layout_v6.py 와 같은 미터 단위 (X = 동쪽/흐름 방향, Z = 남쪽 +)
- 부품 모양은 Factory I/O 를 위에서 본 느낌으로 단순화한 개념도입니다 (실제 치수는 씬에서 확인)
- 출력: factoryio_topview_v6.svg (M1720 = Pop-up Wheel Sorter)
        factoryio_topview_v6_v2.svg (M1720 = Pusher, --pusher)
실행: python make_factoryio_topview.py [--pusher]
"""
import html
import os
import sys

PUSHER = '--pusher' in sys.argv   # v2: M1720 분기를 Pusher 로

S = 44                       # px per meter
XMIN, XMAX = -17.4, 25.8
ZMIN, ZMAX = -3.5, 4.8
MX, MY = 24, 74              # margins (top margin holds the title)
LEG_H = 292 if PUSHER else 230                  # legend band under the floor
W = int((XMAX - XMIN) * S + 2 * MX)
FLOOR_H = (ZMAX - ZMIN) * S
H = int(MY + FLOOR_H + LEG_H)

BW = 0.7                     # belt width (m)
R = 0.55                     # curve radius (m)

# v6 geometry (same as make_layout_v6.py)
RAIL_IN_Z, RAIL_OUT_Z = -1.3, 1.3
RACK_X0, BAY_W, BAYS = -8.0, 1.4, 6
RACK_X1 = RACK_X0 + BAY_W * BAYS
INSP_X, RETEST_X, RT_X = 4.5, 6.5, 12.6
SORT1_X, SORT1_Z = 1.6, RAIL_OUT_Z
SORT2_X, RET_Z, NG_Z = 14.5, 2.0, 3.6
GATE_X = 22.0

out = []


def P(x, z):
    return (x - XMIN) * S + MX, (z - ZMIN) * S + MY


def L(m):
    return m * S


def add(s):
    out.append(s)


def rect_m(x0, z0, x1, z1, fill, stroke='none', sw=1.0, rx=0, extra=''):
    a, b = P(min(x0, x1), min(z0, z1))
    add(f'<rect x="{a:.1f}" y="{b:.1f}" width="{L(abs(x1 - x0)):.1f}" height="{L(abs(z1 - z0)):.1f}" '
        f'rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{extra}/>')


def line_m(x0, z0, x1, z1, color, sw=1.0, extra=''):
    a, b = P(x0, z0)
    c, d = P(x1, z1)
    add(f'<line x1="{a:.1f}" y1="{b:.1f}" x2="{c:.1f}" y2="{d:.1f}" stroke="{color}" stroke-width="{sw}"{extra}/>')


def circle_m(x, z, r, fill, stroke='none', sw=1.0, extra=''):
    a, b = P(x, z)
    add(f'<circle cx="{a:.1f}" cy="{b:.1f}" r="{L(r):.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{extra}/>')


def text_px(x, y, s, size=10, color='#F8FAFC', weight=400, anchor='start', extra=''):
    add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" fill="{color}" '
        f'text-anchor="{anchor}"{extra}>{html.escape(s)}</text>')


def text_m(x, z, s, size=10, color='#F8FAFC', weight=400, anchor='middle', extra=''):
    a, b = P(x, z)
    text_px(a, b, s, size, color, weight, anchor, extra)


# ---------------------------------------------------------------- conveyors
def belt(x0, z0, x1, z1, kind='belt', w=BW):
    """Straight, axis-aligned conveyor from (x0,z0) to (x1,z1) in the flow direction."""
    horiz = abs(z1 - z0) < 1e-9
    h = w / 2
    if horiz:
        a0, a1 = min(x0, x1), max(x0, x1)
        rect_m(a0, z0 - h - 0.07, a1, z0 + h + 0.07, '#AEB7BF', '#5F6870', 1)
        rect_m(a0, z0 - h, a1, z0 + h, '#2C3136' if kind == 'belt' else '#454B51')
    else:
        a0, a1 = min(z0, z1), max(z0, z1)
        rect_m(x0 - h - 0.07, a0, x0 + h + 0.07, a1, '#AEB7BF', '#5F6870', 1)
        rect_m(x0 - h, a0, x0 + h, a1, '#2C3136' if kind == 'belt' else '#454B51')
    length = (a1 - a0)
    if kind == 'roller':
        n = int(length / 0.14)
        for i in range(n + 1):
            t = a0 + 0.07 + i * 0.14
            if t > a1 - 0.03:
                break
            if horiz:
                line_m(t, z0 - h + 0.03, t, z0 + h - 0.03, '#C9D1D8', L(0.05))
            else:
                line_m(x0 - h + 0.03, t, x0 + h - 0.03, t, '#C9D1D8', L(0.05))
    else:
        n = int(length / 0.3)
        for i in range(1, n + 1):
            t = a0 + i * 0.3
            if horiz:
                line_m(t, z0 - h, t, z0 + h, '#383E44', 1)
            else:
                line_m(x0 - h, t, x0 + h, t, '#383E44', 1)
        # flow chevrons
        dx = (1 if x1 > x0 else -1) if horiz else 0
        dz = 0 if horiz else (1 if z1 > z0 else -1)
        step = 1.6
        k = 0.8
        while k < length - 0.3:
            cx = x0 + dx * k
            cz = z0 + dz * k
            s = 0.16
            pts = [(cx - dx * s - dz * s, cz - dz * s - dx * s), (cx, cz), (cx - dx * s + dz * s, cz - dz * s + dx * s)]
            add('<polyline points="' + ' '.join('%.1f,%.1f' % P(*p) for p in pts) +
                '" fill="none" stroke="#8C959E" stroke-width="2" stroke-linecap="round" opacity="0.8"/>')
            k += step


def corner(cx, cz, d1, d2, r=R, w=BW):
    """Curved Belt Conveyor (90°) at corner point (cx,cz): incoming dir d1, outgoing dir d2."""
    sx, sz = cx - d1[0] * r, cz - d1[1] * r
    ex, ez = cx + d2[0] * r, cz + d2[1] * r
    ox, oz = sx + d2[0] * r, sz + d2[1] * r
    cross = (sx - ox) * (ez - oz) - (sz - oz) * (ex - ox)
    sweep = 1 if cross > 0 else 0

    def sector(rr_out, rr_in, fill, stroke='none', sw=1):
        def pt(px_, pz_, rr):
            return P(ox + (px_ - ox) / r * rr, oz + (pz_ - oz) / r * rr)
        a = pt(sx, sz, rr_out)
        b = pt(ex, ez, rr_out)
        c = pt(ex, ez, rr_in)
        d = pt(sx, sz, rr_in)
        add(f'<path d="M{a[0]:.1f},{a[1]:.1f} A{L(rr_out):.1f},{L(rr_out):.1f} 0 0 {sweep} {b[0]:.1f},{b[1]:.1f} '
            f'L{c[0]:.1f},{c[1]:.1f} A{L(rr_in):.1f},{L(rr_in):.1f} 0 0 {1 - sweep} {d[0]:.1f},{d[1]:.1f} Z" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    sector(r + w / 2 + 0.07, max(r - w / 2 - 0.07, 0.02), '#AEB7BF', '#5F6870')
    sector(r + w / 2, max(r - w / 2, 0.04), '#2C3136')


def popup_sorter(x, z, arrows, label=None):
    """Pop-up Wheel Sorter tile; arrows = list of (dx, dz, color)."""
    h = BW / 2 + 0.07
    rect_m(x - h, z - h, x + h, z + h, '#AEB7BF', '#5F6870', 1)
    rect_m(x - BW / 2, z - BW / 2, x + BW / 2, z + BW / 2, '#30363C')
    for i in (-1, 0, 1):
        for j in (-1, 0, 1):
            circle_m(x + i * 0.2, z + j * 0.2, 0.055, '#9AA3AB', '#1F2429', 0.8)
    for dx, dz, col in arrows:
        a = P(x + dx * 0.12, z + dz * 0.12)
        b = P(x + dx * 0.62, z + dz * 0.62)
        add(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="{col}" stroke-width="3" '
            f'marker-end="url(#ah-{col[1:]})"/>')


def pusher(x, z, k=1.0):
    """Pusher on the north side of an east-flowing belt, pushing south (+z). k = scale (legend icon)."""
    rect_m(x - 0.42 * k, z - 1.38 * k, x + 0.42 * k, z - 0.62 * k, '#1D4ED8', '#93C5FD', 1.5, 3)
    rect_m(x - 0.13 * k, z - 1.28 * k, x + 0.13 * k, z - 0.72 * k, '#94A3B8', '#334155', 1, 2)
    for dx in (-0.24, 0.24):
        line_m(x + dx * k, z - 0.62 * k, x + dx * k, z - 0.5 * k, '#CBD5E1', 2.5)
    rect_m(x - 0.38 * k, z - 0.52 * k, x + 0.38 * k, z - 0.42 * k, '#E5E7EB', '#374151', 1)
    rect_m(x - 0.38 * k, z + 0.3 * k, x + 0.38 * k, z + 0.4 * k, 'none', '#F59E0B', 1.5, 0, ' stroke-dasharray="3 2"')
    a = P(x, z - 0.3 * k)
    b = P(x, z + 0.22 * k)
    add(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="#F59E0B" stroke-width="{3 if k >= 1 else 2}" '
        f'marker-end="url(#ah-F59E0B)"/>')


def stop_blade(x, z, vertical_belt=False):
    h = BW / 2 + 0.12
    if vertical_belt:
        rect_m(x - h, z - 0.05, x + h, z + 0.05, '#F2C200', '#7A6100', 1)
    else:
        rect_m(x - 0.05, z - h, x + 0.05, z + h, '#F2C200', '#7A6100', 1)


def diffuse(x, z, side=-1, vertical_belt=False):
    """Diffuse Sensor on one side of the belt with its beam across."""
    if not vertical_belt:
        sz = z + side * (BW / 2 + 0.2)
        rect_m(x - 0.09, sz - 0.07, x + 0.09, sz + 0.07, '#1E3A8A', '#93C5FD', 1, 2)
        line_m(x, sz - side * 0.07, x, z - side * (BW / 2), '#FF4D4D', 1.6, ' stroke-dasharray="3 2" opacity="0.9"')
        circle_m(x, sz, 0.03, '#34D399')
    else:
        sx = x + side * (BW / 2 + 0.2)
        rect_m(sx - 0.07, z - 0.09, sx + 0.07, z + 0.09, '#1E3A8A', '#93C5FD', 1, 2)
        line_m(sx - side * 0.07, z, x - side * (BW / 2), z, '#FF4D4D', 1.6, ' stroke-dasharray="3 2" opacity="0.9"')
        circle_m(sx, z, 0.03, '#34D399')


def rfid(x, z, side=-1):
    sz = z + side * (BW / 2 + 0.2)
    rect_m(x - 0.18, sz - 0.1, x + 0.18, sz + 0.1, '#64748B', '#CBD5E1', 1, 2)
    rect_m(x - 0.14, sz - side * 0.1 - 0.025, x + 0.14, sz - side * 0.1 + 0.025, '#3B82F6')
    for k in (0.12, 0.2):
        a = P(x - k, sz - side * 0.12)
        b = P(x + k, sz - side * 0.12)
        add(f'<path d="M{a[0]:.1f},{a[1]:.1f} Q{(a[0] + b[0]) / 2:.1f},{a[1] - side * L(k):.1f} {b[0]:.1f},{b[1]:.1f}" '
            f'fill="none" stroke="#60A5FA" stroke-width="1.2" opacity="0.8"/>')


def vision(x, z, side=1):
    sz = z + side * (BW / 2 + 0.25)
    rect_m(x - 0.32, z - BW / 2, x + 0.32, z + BW / 2, '#22D3EE', 'none', 0, 0, ' opacity="0.18"')
    rect_m(x - 0.06, sz, x + 0.06, z, '#475569')  # arm
    rect_m(x - 0.14, z - 0.1, x + 0.14, z + 0.1, '#0F172A', '#22D3EE', 1.2, 2)
    circle_m(x, z, 0.05, '#22D3EE')
    rect_m(x - 0.12, sz - 0.12, x + 0.12, sz + 0.12, '#334155', '#94A3B8', 1, 2)  # post


def box(x, z, large=False, tag=None, hot=False, rot=False):
    wx, wz = (0.62, 0.5) if large else (0.4, 0.4)
    if rot:
        wx, wz = wz, wx
    if hot:
        circle_m(x, z, 0.5, 'url(#hot)')
    rect_m(x - wx / 2, z - wz / 2, x + wx / 2, z + wz / 2, '#C99A5B', '#7C5530', 1, 1.5)
    if wx >= wz:
        rect_m(x - wx / 2, z - 0.035, x + wx / 2, z + 0.035, '#E3C48F')
    else:
        rect_m(x - 0.035, z - wz / 2, x + 0.035, z + wz / 2, '#E3C48F')
    if tag:
        rect_m(x + wx / 2 - 0.2, z + wz / 2 - 0.13, x + wx / 2 - 0.03, z + wz / 2 - 0.03, '#F8FAFC')


def pallet(x, z, w=0.9, d=0.75):
    rect_m(x - w / 2, z - d / 2, x + w / 2, z + d / 2, '#B88A55', '#6B4A26', 1, 1)
    for k in (-0.3, 0, 0.3):
        line_m(x - w / 2 + 0.03, z + k * d, x + w / 2 - 0.03, z + k * d, '#8A6238', 1.2)


def emitter(x, z, s=0.85):
    rect_m(x - s / 2, z - s / 2, x + s / 2, z + s / 2, '#3B82F6', '#93C5FD', 1.5, 3, ' fill-opacity="0.32"')
    rect_m(x - 0.2, z - 0.2, x + 0.2, z + 0.2, 'none', '#BFDBFE', 1, 1, ' stroke-dasharray="3 2"')


def remover(x, z, s=0.85):
    rect_m(x - s / 2, z - s / 2, x + s / 2, z + s / 2, '#EF4444', '#FCA5A5', 1.5, 3, ' fill-opacity="0.32"')
    line_m(x - 0.18, z - 0.18, x + 0.18, z + 0.18, '#FECACA', 1.5)
    line_m(x - 0.18, z + 0.18, x + 0.18, z - 0.18, '#FECACA', 1.5)


def stack_light(x, z):
    circle_m(x, z, 0.16, '#1F2937', '#9CA3AF', 1)
    for i, c in enumerate(('#EF4444', '#F59E0B', '#22C55E')):
        circle_m(x - 0.09 + i * 0.09, z, 0.04, c)


def siren(x, z):
    circle_m(x, z, 0.14, '#F97316', '#FDBA74', 1)
    for rr in (0.22, 0.3):
        circle_m(x, z, rr, 'none', '#FDBA74', 1, ' opacity="0.5" stroke-dasharray="2 3"')


def crane(rail_z, x0, x1, car_x, fork_dir, name):
    for dz in (-0.3, 0.3):
        line_m(x0, rail_z + dz, x1, rail_z + dz, '#8D969E', 2.5)
    for xx in (x0, x1):
        rect_m(xx - 0.08, rail_z - 0.38, xx + 0.08, rail_z + 0.38, '#475569')
    # carriage + mast + forks
    rect_m(car_x - 0.5, rail_z - 0.42, car_x + 0.5, rail_z + 0.42, '#F5B700', '#7A5B00', 1.5, 3)
    for i in range(5):
        line_m(car_x - 0.5 + i * 0.25, rail_z - 0.42, car_x - 0.5 + i * 0.25 + 0.12, rail_z - 0.3, '#111827', 2)
    rect_m(car_x - 0.18, rail_z - 0.18, car_x + 0.18, rail_z + 0.18, '#374151', '#111827', 1)
    for fx in (-0.25, 0.25):
        z_a = rail_z + fork_dir * 0.42
        z_b = rail_z + fork_dir * 0.85
        rect_m(car_x + fx - 0.05, min(z_a, z_b), car_x + fx + 0.05, max(z_a, z_b), '#9CA3AF', '#4B5563', 1)
    text_m(car_x, rail_z + 0.06, name, 9, '#111827', 800)


def tag(tx, tz, lines, obj=None, color='#38BDF8'):
    """Dark label tag with leader line. tx,tz = top-left in meters."""
    a, b = P(tx, tz)
    fs = [10.5] + [9.5] * (len(lines) - 1)

    def tw(s, f):
        return sum(f * (1.0 if ord(ch) > 0x2E80 else 0.6) for ch in s)
    w = max(tw(s, f) for s, f in zip(lines, fs)) + 16
    h = 8 + sum(f * 1.32 for f in fs)
    if obj:
        ox, oy = P(*obj)
        cx = min(max(ox, a), a + w)
        cy = min(max(oy, b), b + h)
        add(f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{ox:.1f}" y2="{oy:.1f}" stroke="#E5E7EB" stroke-width="1" opacity="0.75"/>')
        add(f'<circle cx="{ox:.1f}" cy="{oy:.1f}" r="2.6" fill="#E5E7EB"/>')
    add(f'<rect x="{a:.1f}" y="{b:.1f}" width="{w:.1f}" height="{h:.1f}" rx="4" fill="#0B1220" fill-opacity="0.88" '
        f'stroke="{color}" stroke-width="1.2"/>')
    add(f'<rect x="{a:.1f}" y="{b:.1f}" width="4" height="{h:.1f}" rx="2" fill="{color}"/>')
    y = b + 4
    for i, (s, f) in enumerate(zip(lines, fs)):
        y += f * 1.32
        text_px(a + 10, y - 3, s, f, '#F8FAFC' if i == 0 else '#CBD5E1', 700 if i == 0 else 400)


# ================================================================ SVG start
add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
    'font-family="Malgun Gothic, Pretendard, sans-serif">')
defs = ['<defs>',
        '<radialGradient id="hot"><stop offset="0" stop-color="#EF4444" stop-opacity="0.75"/>'
        '<stop offset="1" stop-color="#EF4444" stop-opacity="0"/></radialGradient>',
        '<pattern id="lock" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
        '<rect width="8" height="8" fill="#EF4444" fill-opacity="0.18"/><rect width="3" height="8" fill="#EF4444" fill-opacity="0.55"/></pattern>',
        '<pattern id="hazard" width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
        '<rect width="14" height="14" fill="#F5C400"/><rect width="7" height="14" fill="#111827"/></pattern>']
for col in ('22C55E', 'EF4444', 'F59E0B', '38BDF8'):
    defs.append(f'<marker id="ah-{col}" markerWidth="6" markerHeight="6" refX="2" refY="3" orient="auto">'
                f'<path d="M0,0 L6,3 L0,6 z" fill="#{col}"/></marker>')
defs.append('</defs>')
add(''.join(defs))
add(f'<rect width="{W}" height="{H}" fill="#1B1F24"/>')

# title
text_px(MX, 30, 'Project B 상면도 — Factory I/O 부품 기준 (v6)' + (' · v2: M1720 Pusher' if PUSHER else ''), 18, '#F8FAFC', 800)
text_px(MX, 52, '투입 Emitter → RFID ①·Vision → Stacker Crane A → Rack 24칸 → Stacker Crane B → 1차 분리(Pop-up Wheel) '
        f'→ 메인 검사 → M1720{"(Pusher)" if PUSHER else ""} → 재검사 라인(연속) → 재검사기 → 2차 분리 → GOOD OUT / NG OUT', 11, '#94A3B8')

# floor (Factory I/O style concrete tiles, 1 m grid)
fx, fy = P(XMIN, ZMIN)
add(f'<rect x="{fx:.1f}" y="{fy:.1f}" width="{L(XMAX - XMIN):.1f}" height="{L(ZMAX - ZMIN):.1f}" fill="#5B6168" rx="6"/>')
x = int(XMIN) + 1
while x < XMAX:
    line_m(x, ZMIN, x, ZMAX, '#676D74' if x % 4 else '#72787F', 1)
    x += 1
z = int(ZMIN)
while z < ZMAX:
    if z > ZMIN:
        line_m(XMIN, z, XMAX, z, '#676D74' if z % 4 else '#72787F', 1)
    z += 1

# hazard floor marking around the crane / rack area
for zz in (RAIL_IN_Z - 0.62, RAIL_OUT_Z + 0.5):
    rect_m(RACK_X0 - 0.9, zz, RACK_X1 + 0.2, zz + 0.12, 'url(#hazard)', 'none', 0, 0, ' opacity="0.85"')

# ---------------------------------------------------------------- STEP 01 infeed
emitter(-16.5, 0)
belt(-16.07, 0, -11.05, 0)
corner(-10.5, 0, (1, 0), (0, -1))
belt(-10.5, -0.55, -10.5, -0.75)
corner(-10.5, RAIL_IN_Z, (0, -1), (1, 0))
belt(-9.95, RAIL_IN_Z, -9.6, RAIL_IN_Z)
belt(-9.6, RAIL_IN_Z, -9.05, RAIL_IN_Z, 'roller')
vision(-13.2, 0, side=1)
stop_blade(-11.6, 0)
rfid(-12.0, 0, side=-1)
diffuse(-12.5, 0, side=-1)
box(-15.0, 0, large=False, tag=True)
box(-13.9, 0, large=True, tag=True)
box(-11.95, 0, large=False, tag=True)

# ---------------------------------------------------------------- rack + cranes
crane(RAIL_IN_Z, RACK_X0 - 1.0, RACK_X1 + 0.2, -5.0, +1, 'A')
crane(RAIL_OUT_Z, RACK_X0 - 1.0, RACK_X1 + 0.2, -1.4, -1, 'B')
rect_m(RACK_X0, -0.5, RACK_X1, 0.5, '#3A4047', '#1E293B', 1)
stored = [(True, False), (False, None), (True, False), (True, True), (True, True), (False, None)]
for i in range(BAYS):
    bx0 = RACK_X0 + i * BAY_W
    cx = bx0 + BAY_W / 2
    if i == 1:
        rect_m(bx0 + 0.05, -0.45, bx0 + BAY_W - 0.05, 0.45, 'url(#lock)')
    full, large = stored[i]
    if full:
        pallet(cx, 0, 1.0, 0.8)
        box(cx, 0, large=large, tag=True, hot=(i == 4))
    text_m(cx, -0.58, f'R{i + 1:02d}', 8, '#E2E8F0', 700)
for i in range(BAYS + 1):
    ux = RACK_X0 + i * BAY_W
    for uz in (-0.5, 0.5):
        rect_m(ux - 0.07, uz - 0.07, ux + 0.07, uz + 0.07, '#1E5AA8', '#0F2E57', 1)
line_m(RACK_X0, -0.5, RACK_X1, -0.5, '#E8731A', 2.5)
line_m(RACK_X0, 0.5, RACK_X1, 0.5, '#E8731A', 2.5)
mid = RACK_X0 + BAY_W * 3
line_m(mid, -0.55, mid, 0.55, '#F8FAFC', 1.5, ' stroke-dasharray="4 3"')
text_m(RACK_X0 + BAY_W * 1.5, 0.74, '4S 구역 R01~R03 (Small box)', 8.5, '#BFDBFE', 700)
text_m(RACK_X0 + BAY_W * 4.5, 0.74, '6S 구역 R04~R06 (Large box)', 8.5, '#A7F3D0', 700)

# ---------------------------------------------------------------- outfeed → 1차 분리
belt(RACK_X1 + 0.3, RAIL_OUT_Z, SORT1_X - 0.42, RAIL_OUT_Z, 'roller')
popup_sorter(SORT1_X, SORT1_Z, [(0, -1, '#22C55E'), (0, 1, '#EF4444')])
belt(SORT1_X, SORT1_Z - 0.42, SORT1_X, 0.55)
corner(SORT1_X, 0, (0, -1), (1, 0))
# isolation (M1690)
belt(SORT1_X, SORT1_Z + 0.42, SORT1_X, 2.45)
iso_x0, iso_z0, iso_x1, iso_z1 = SORT1_X - 0.75, 2.45, SORT1_X + 0.75, 3.75
rect_m(iso_x0, iso_z0, iso_x1, iso_z1, '#7F1D1D', '#FCA5A5', 2, 4, ' fill-opacity="0.35" stroke-dasharray="6 3"')
remover(SORT1_X, 3.1)
diffuse(SORT1_X, 2.2, side=1, vertical_belt=True)
box(SORT1_X, 1.95, large=False, tag=True, hot=True)
stack_light(SORT1_X - 1.15, 2.65)
siren(SORT1_X - 1.15, 3.3)

# ---------------------------------------------------------------- main line
if PUSHER:
    belt(SORT1_X + R, 0, GATE_X, 0)
else:
    belt(SORT1_X + R, 0, RETEST_X - 0.42, 0)
    popup_sorter(RETEST_X, 0, [(1, 0, '#22C55E'), (0, 1, '#F59E0B')])
    belt(RETEST_X + 0.42, 0, GATE_X, 0)
# main tester (gantry over the belt)
rect_m(INSP_X - 0.55, -1.15, INSP_X + 0.55, -0.48, '#F59E0B', '#78350F', 1.5, 3)
rect_m(INSP_X - 0.12, -0.48, INSP_X + 0.12, 0.05, '#9CA3AF', '#374151', 1)
circle_m(INSP_X, 0.05, 0.09, '#F59E0B', '#78350F', 1)
text_m(INSP_X, -0.72, 'M1700', 9, '#1F2937', 800)
stop_blade(INSP_X + 0.42, 0)
rfid(INSP_X - 0.35, 0, side=1)
diffuse(INSP_X - 0.9, 0, side=1)
stack_light(INSP_X + 0.85, -0.85)
box(3.0, 0, large=False, tag=True)
box(INSP_X, 0, large=True, tag=True)
box(9.2, 0, large=False, tag=True)
if PUSHER:
    pusher(RETEST_X, 0)
    diffuse(RETEST_X - 0.62, 0, side=-1)
    box(RETEST_X, 0, large=False, tag=True)
box(17.6, 0, large=True, tag=True)
# GOOD OUT
diffuse(GATE_X - 0.6, 0, side=-1)
remover(GATE_X + 0.45, 0, 0.9)

# ---------------------------------------------------------------- retest line (continuous, no rest buffer)
belt(RETEST_X, 0.42, RETEST_X, RET_Z - R)
corner(RETEST_X, RET_Z, (0, 1), (1, 0))
belt(RETEST_X + R, RET_Z, SORT2_X - 0.42, RET_Z)
rect_m(RT_X - 0.55, RET_Z + 0.48, RT_X + 0.55, RET_Z + 1.15, '#F59E0B', '#78350F', 1.5, 3)
rect_m(RT_X - 0.12, RET_Z - 0.05, RT_X + 0.12, RET_Z + 0.48, '#9CA3AF', '#374151', 1)
circle_m(RT_X, RET_Z - 0.05, 0.09, '#F59E0B', '#78350F', 1)
text_m(RT_X, RET_Z + 0.92, 'M1730', 9, '#1F2937', 800)
stop_blade(RT_X + 0.42, RET_Z)
rfid(RT_X - 0.35, RET_Z, side=-1)
box(9.6, RET_Z, large=True, tag=True)
box(11.2, RET_Z, large=False, tag=True)
box(11.75, RET_Z, large=False, tag=True)
box(RT_X, RET_Z, large=True, tag=True)
# 2차 분리
popup_sorter(SORT2_X, RET_Z, [(0, -1, '#22C55E'), (0, 1, '#EF4444')])
belt(SORT2_X, RET_Z - 0.42, SORT2_X, 0.43)
diffuse(SORT2_X, 0.95, side=-1, vertical_belt=True)
belt(SORT2_X, RET_Z + 0.42, SORT2_X, NG_Z - R)
corner(SORT2_X, NG_Z, (0, 1), (1, 0))
belt(SORT2_X + R, NG_Z, GATE_X, NG_Z)
box(18.4, NG_Z, large=False, tag=True)
diffuse(GATE_X - 0.6, NG_Z, side=-1)
remover(GATE_X + 0.45, NG_Z, 0.9)

# ---------------------------------------------------------------- operator panel (보조)
px0, pz0, px1, pz1 = 22.2, -3.25, 25.55, -1.25
rect_m(px0, pz0, px1, pz1, '#374151', '#9CA3AF', 1.5, 5)
text_m(px0 + 0.12, pz0 + 0.32, '조작반 (보조 · HMI는 Pro-face)', 8.5, '#F8FAFC', 700, 'start')
for i, (c, lab) in enumerate((('#22C55E', '시작'), ('#EF4444', '정지'), ('#F59E0B', 'M1920'))):
    circle_m(px0 + 0.42 + i * 0.75, pz0 + 0.78, 0.17, c, '#111827', 1.5)
    text_m(px0 + 0.42 + i * 0.75, pz0 + 1.18, lab, 8, '#E5E7EB')
circle_m(px1 - 0.45, pz0 + 0.8, 0.27, '#F5C400', '#111827', 1)
circle_m(px1 - 0.45, pz0 + 0.8, 0.17, '#DC2626', '#7F1D1D', 1.5)
text_m(px1 - 0.45, pz0 + 1.25, 'E-Stop', 8, '#E5E7EB')
for i, (lab, val) in enumerate((('D1900', '0128'), ('D1901', '0011'), ('D1902', '0002'), ('D1904', '91.4'))):
    dx = px0 + 0.12 + i * 0.82
    rect_m(dx, pz0 + 1.38, dx + 0.74, pz0 + 1.82, '#050505', '#6B7280', 1, 2)
    text_m(dx + 0.37, pz0 + 1.7, val, 11, '#FF3B30', 700, extra=' font-family="Consolas, monospace"')
    text_m(dx + 0.37, pz0 + 1.97, lab, 7.5, '#CBD5E1')

# ---------------------------------------------------------------- tags
tag(-17.2, -3.3, ['Emitter · Small / Large box', 'Project C 인계 · 4S = Small · 6S = Large'], (-16.5, -0.4), '#60A5FA')
tag(-12.75, -3.3, ['RFID Reader ① · Stop Blade', 'D1510~17 등록 · Diffuse Sensor'], (-12.0, -0.6), '#60A5FA')
tag(-16.2, 1.25, ['Vision Sensor · D1519', '4S / 6S 종류 판별 → 구역 지정'], (-13.2, 0.55), '#22D3EE')
tag(-8.5, -3.3, ['Stacker Crane A · M1600', '입고면 · 종류별 구역 입고'], (-5.0, -1.7), '#F5B700')
tag(-4.6, -3.3, ['Rack 6열 × 4단 = 24칸 + Pallet', '칸 크기 동일 · 보관 중 온도 감시(가상)'], (-2.7, -0.5), '#94A3B8')
tag(-11.6, 2.25, ['Stacker Crane B · M1601', '출고면 · 발열 우선 → EDD · 동쪽 출구'], (-1.4, 1.75), '#F5B700')
tag(-7.0, 3.35, ['R02 = LOCK 칸 (빗금)', '발열 반출 후 점검 · R05 = 발열 팩(가상 온도)'], (-6.6, 0.45), '#EF4444')
tag(2.3, 0.62, ['Pop-up Wheel Sorter', '1차 분리 M1660↑ / M1661↓'], (SORT1_X + 0.42, SORT1_Z), '#22C55E')
tag(2.75, 2.55, ['Remover · M1690 발열 격리', 'Diffuse X1902 → D1902 · DB ISO', 'Stack Light · Alarm Siren'], (SORT1_X + 0.4, 3.1), '#EF4444')
tag(1.0, -3.3, ['메인 검사기 · Stop Blade · RFID ②', 'M1700 · D1520~27 · OCV·IR·온도(가상)'], (INSP_X, -1.15), '#F59E0B')
tag(7.0, -1.6, ['Belt Conveyor · 메인 라인', 'GOOD 직진 → GOOD OUT (M1710 라인 없음)'], (10.5, -0.42), '#94A3B8')
if PUSHER:
    tag(6.95, 0.55, ['Pusher · M1720', 'RETEST·NG ↓ 밀어 넣기'], (RETEST_X + 0.4, 0.2), '#F59E0B')
else:
    tag(6.95, 0.55, ['Pop-up Wheel · M1720', 'RETEST·NG ↓ 재검사'], (RETEST_X + 0.4, 0.2), '#F59E0B')
tag(7.0, 2.6, ['재검사 라인 (연속 · 정치 없음)', '분기점까지 차면 M1800 · D1800'], (9.0, RET_Z + 0.4), '#F59E0B')
tag(10.45, 0.52, ['재검사기 · RFID ③', 'Stop Blade · M1730', 'D1530~37 · 메인 NG 계측 생략'], (RT_X - 0.35, RET_Z - 0.5), '#F59E0B')
tag(15.15, 1.45, ['Pop-up Wheel Sorter · 2차 분리', 'M1731 ↑ GOOD 합류 / M1732 ↓ NG'], (SORT2_X + 0.42, RET_Z), '#22C55E')
tag(15.15, 0.5, ['Diffuse Sensor X1903 · 합류 간격'], (SORT2_X + 0.38, 0.95), '#38BDF8')
tag(17.6, -1.6, ['Remover · GOOD OUT', 'Diffuse X1900 → D1900'], (GATE_X + 0.45, -0.45), '#22C55E')
tag(15.4, 4.0, ['Remover · NG OUT (NG 1라인)', 'Diffuse X1901 → D1901 · 원인 = DB ng_cause'], (GATE_X + 0.45, NG_Z + 0.45), '#EF4444')

# ---------------------------------------------------------------- legend
ly = MY + FLOOR_H + 22
text_px(MX, ly, '사용 부품 (Factory I/O 팔레트 이름)', 13, '#F8FAFC', 800)
items = [
    ('Small box', '4S 팩 (2×2)', lambda x, z: box(x, z)),
    ('Large box', '6S 팩 (2×3)', lambda x, z: box(x, z, large=True)),
    ('Pallet', '랙 보관 단위', lambda x, z: pallet(x, z, 0.7, 0.55)),
    ('Belt Conveyor', '메인 · 재검사 · NG 라인', lambda x, z: belt(x - 0.45, z, x + 0.45, z)),
    ('Curved Belt Conveyor', '90° 꺾임', lambda x, z: corner(x - 0.1, z + 0.2, (1, 0), (0, -1), 0.4, 0.45)),
    ('Roller Conveyor', '크레인 입 · 출고 구간', lambda x, z: belt(x - 0.45, z, x + 0.45, z, 'roller')),
    ('Pop-up Wheel Sorter', '1차 · 2차 분리' if PUSHER else '1차 · 2차 분리 · M1720', lambda x, z: popup_sorter(x, z, [(1, 0, '#22C55E')])),
    ('Stop Blade', '검사 위치 정지', lambda x, z: (belt(x - 0.4, z, x + 0.4, z), stop_blade(x, z))),
    ('Diffuse Sensor', 'X1900~X1903 통과 감지', lambda x, z: (belt(x - 0.4, z, x + 0.4, z), diffuse(x, z, -1))),
    ('RFID Reader', 'PACK ID ① ② ③', lambda x, z: (belt(x - 0.4, z, x + 0.4, z), rfid(x, z, -1))),
    ('Vision Sensor', '종류 판별 D1519', lambda x, z: (belt(x - 0.4, z, x + 0.4, z), vision(x, z, 1))),
    ('Stacker Crane', '크레인 A · B', lambda x, z: crane(z, x - 0.6, x + 0.6, x, 1, '')),
    ('Rack', '6열 × 4단', lambda x, z: (rect_m(x - 0.5, z - 0.3, x + 0.5, z + 0.3, '#3A4047', '#1E293B'),
                                    line_m(x - 0.5, z - 0.3, x + 0.5, z - 0.3, '#E8731A', 2.5),
                                    line_m(x - 0.5, z + 0.3, x + 0.5, z + 0.3, '#E8731A', 2.5))),
    ('Emitter', '투입 (Project C 인계)', lambda x, z: emitter(x, z, 0.6)),
    ('Remover', 'GOOD · NG · 격리 배출', lambda x, z: remover(x, z, 0.6)),
    ('Stack Light', '상태 표시', lambda x, z: stack_light(x, z)),
    ('Alarm Siren', 'M1690 발열 경보', lambda x, z: siren(x, z)),
    ('Push Button · E-Stop', '조작반 (보조)', lambda x, z: (circle_m(x - 0.2, z, 0.14, '#22C55E', '#111827'),
                                                       circle_m(x + 0.22, z, 0.2, '#F5C400', '#111827'),
                                                       circle_m(x + 0.22, z, 0.12, '#DC2626'))),
    ('Digital Display', '카운터 D1900~D1904', lambda x, z: (rect_m(x - 0.38, z - 0.2, x + 0.38, z + 0.2, '#050505', '#6B7280'),
                                                         text_m(x, z + 0.1, '0128', 10, '#FF3B30', 700, extra=' font-family="Consolas, monospace"'))),
    ('LOCK 칸 표시', '발열 반출 후 점검', lambda x, z: rect_m(x - 0.45, z - 0.3, x + 0.45, z + 0.3, 'url(#lock)', '#EF4444')),
    ('발열 팩', '가상 온도 > 38.0 °C', lambda x, z: box(x, z, hot=True)),
]
if PUSHER:
    items.insert(7, ('Pusher', 'M1720 재검사 라인 분기', lambda x, z: pusher(x, z + 0.3, 0.45)))
cols = 7
cw = (W - 2 * MX) / cols
for i, (name, desc, fn) in enumerate(items):
    r, c = divmod(i, cols)
    bx = MX + c * cw
    by = ly + 22 + r * 62
    icx = (bx + 34 - MX) / S + XMIN
    icz = (by + 22 - MY) / S + ZMIN
    add(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{cw - 8:.1f}" height="54" rx="5" fill="#252B32" stroke="#3A424B"/>')
    fn(icx, icz)
    text_px(bx + 70, by + 22, name, 11, '#F8FAFC', 700)
    text_px(bx + 70, by + 39, desc, 9.5, '#94A3B8')

text_px(W - MX, 30, '배치 개념도 (Factory I/O 화면 아님) · 1칸 = 1 m · 부품 실제 치수 · Vision 출력값 · 랙 칸 수는 씬에서 확인 필요',
        9.5, '#94A3B8', 400, 'end')
add('</svg>')

here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, 'factoryio_topview_v6_v2.svg' if PUSHER else 'factoryio_topview_v6.svg'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
print('written', W, H)
