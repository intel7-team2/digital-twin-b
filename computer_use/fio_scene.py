"""
Factory I/O 씬 파일(.factoryio) 도구 — 화면 조작 없이 씬 XML을 읽고 고칩니다.

Factory I/O(Unity)는 Computer Use의 글자 입력을 받지 않습니다(11-19 시험).
그래서 글자를 넣어야 하는 일(태그 이름, Emitter 박스 종류, 드라이버 선택 · 번지 연결)은
씬을 저장한 뒤 이 도구로 파일을 고치고 다시 엽니다. 원본 씬은 고치지 않고 항상 새 파일로 씁니다.

  info  SCENE                          부품 · 태그 · 드라이버 연결 요약
  tests [--out DIR]                    F2 시험 씬 6개 만들기 (Factory I/O 기본 씬 복사본)
  force SCENE OUT NAME=VALUE ...       태그 강제값 (VALUE: on/off/숫자/release)
  rename SCENE OUT --csv FILE          태그 이름 바꾸기 (CSV 열: 현재 이름 또는 Key, 새 이름)
  emitter SCENE OUT --parts BoxS,BoxL [--bases Pallet]   Emitter 박스 · 받침 종류
  map-modbus SCENE OUT                 연결 안 된 태그를 Modbus TCP Server 빈 번지에 연결 + 드라이버 선택
  map-opc SCENE OUT --csv FILE [--server Mitsubishi.MXOPC.6]
                                       태그 → OPC 항목(예: CSIM.X1500) 연결 + 드라이버 선택

실행: python computer_use/fio_scene.py info "C:/.../scene.factoryio"
형식 근거: Factory I/O 2.5.10 설치 폴더의 기본 씬 XML, Assembly-CSharp.dll 의 DriverManager.Driver 값
(ModbusTCPServer = 32, OPCClientDA = 16384).
"""
import argparse
import csv
import datetime as dt
import html
import io
import os
import re
import sys
import xml.etree.ElementTree as ET

FIO_DIR = r"C:\Program Files (x86)\Real Games\Factory IO"
SCENES_DIR = os.path.join(FIO_DIR, "Scenes")
ZERO = "00000000-0000-0000-0000-000000000000"
DRIVER = {"none": 0, "modbus-server": 32, "modbus-client": 64, "opc": 16384}
DRIVER_NAME = {v: k for k, v in DRIVER.items()}
UNIT_M = 0.125          # 씬 좌표 1 = 0.125 m (기본 씬 컨베이어 간격으로 확인)

TAG_RE = re.compile(r'<(BinaryInput|BinaryOutput|IntInput|IntOutput|AnalogueInput|AnalogueOutput)\s+'
                    r'Name="([^"]*)"\s+Address="(-?\d+)"\s+Key="([0-9a-f-]{36})"([^>]*?)/>')
OBJ_RE = re.compile(r'<Object [^>]*>.*?</Object>', re.S)
PT_RE = re.compile(r'<(BitInput|BitOutput|FloatInput|FloatOutput|IntInput|IntOutput|NumericInput|NumericOutput)(\d+) '
                   r'PointIOKey="([0-9a-f-]{36})" />')
LIMIT = {"BitInput": 256, "BitOutput": 256, "NumericInput": 64, "NumericOutput": 64}


# ---------------------------------------------------------------- 읽기 · 쓰기
def load(path):
    with io.open(path, encoding="utf-8-sig", newline="") as f:
        return f.read()


def save(path, text, src=None):
    if src and os.path.abspath(path) == os.path.abspath(src):
        sys.exit("원본 씬에 덮어쓰지 않습니다. 다른 OUT 경로를 주세요.")
    if os.path.abspath(path).lower().startswith(os.path.abspath(SCENES_DIR).lower()):
        sys.exit("Factory I/O 설치 폴더에는 쓰지 않습니다.")
    ET.fromstring(text)                     # XML 형식 확인 (깨지면 여기서 멈춤)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with io.open(path, "w", encoding="utf-8-sig", newline="") as f:
        f.write(text)
    print(f"[저장] {path}")


def tags(text):
    """씬의 모든 태그: dict(name, io, kind, key, address, prefab, pos, forced, span)"""
    out = []
    for om in OBJ_RE.finditer(text):
        obj = om.group(0)
        pm = re.search(r'PrefabName="([^"]+)"', obj)
        pos = re.search(r'<Position X="([^"]+)" Y="([^"]+)" Z="([^"]+)"', obj)
        for tm in TAG_RE.finditer(obj):
            el, name, addr, key, rest = tm.groups()
            io_ = "Input" if el.endswith("Input") else "Output"
            kind = "Bool" if el.startswith("Binary") else ("Int" if el.startswith("Int") else "Float")
            f = re.search(r'UseForcedValue="(\w+)" ForcedValue="([^"]*)"', rest)
            out.append(dict(name=html.unescape(name), io=io_, kind=kind, key=key, address=int(addr),
                            prefab=pm.group(1) if pm else "?", pos=tuple(pos.groups()) if pos else None,
                            forced=(f.group(2) if f and f.group(1) == "True" else None),
                            span=(om.start() + tm.start(), om.start() + tm.end())))
    return out


def find_tag(all_tags, ident):
    hit = [t for t in all_tags if t["key"] == ident] or [t for t in all_tags if t["name"] == ident]
    if not hit:
        hit = [t for t in all_tags if t["name"].lower() == ident.lower()]
    return hit


def driver_block(text, name):
    m = re.search(rf'(\n\s*)<{name}>(.*?)</{name}>', text, re.S)
    return m


def modbus_points(text):
    m = driver_block(text, "ModbusTCPServer")
    if not m:
        return None
    body = m.group(2)
    cnt = dict((k, int(v)) for k, v in re.findall(r'(\w+)Count="(\d+)"', re.search(r'<PointIOCount ([^>]*)/>', body).group(1)))
    off = dict((k, int(v)) for k, v in re.findall(r'(\w+)Offset="(\d+)"', re.search(r'<PointIOOffset ([^>]*)/>', body).group(1)))
    props = dict(re.findall(r'(\w+)="([^"]*)"', re.search(r'<Properties ([^>]*)/>', body).group(1)))
    pts = [(k, int(i), key) for k, i, key in PT_RE.findall(body)]
    return dict(count=cnt, offset=off, props=props, points=pts, match=m)


def current_driver(text):
    m = re.search(r'<Drivers CurrentDriver="(\d+)"', text)
    return int(m.group(1)) if m else None


def set_driver(text, value):
    return re.sub(r'(<Drivers CurrentDriver=")\d+(")', rf'\g<1>{value}\g<2>', text, count=1)


def modbus_address_table(text):
    """태그 Key → (Modbus 영역, 0부터 주소). 클라이언트(Python) 쪽에서 본 영역."""
    mb = modbus_points(text)
    if not mb:
        return {}
    p = mb["props"]
    # Factory I/O Modbus Server 기본: 센서 비트 → Discrete Inputs, 액추에이터 비트 ← Coils,
    # 센서 숫자 → Input Registers, 액추에이터 숫자 ← Holding Registers (Properties 가 True면 반대)
    area = {
        "BitInput": "coil" if p.get("WriteCoils") == "True" else "di",
        "BitOutput": "di" if p.get("ReadInputDiscretes") == "True" else "coil",
        "NumericInput": "hr" if p.get("WriteHoldingRegisters") == "True" else "ir",
        "NumericOutput": "ir" if p.get("ReadInputRegisters") == "True" else "hr",
    }
    out = {}
    for kind, idx, key in mb["points"]:
        if key == ZERO or kind not in area or idx >= mb["count"].get(kind, 0):
            continue
        out[key] = (area[kind], mb["offset"].get(kind, 0) + idx, kind)
    return out


def touch_header(text, desc=None, mine=True):
    now = dt.datetime.now()
    hdr = re.search(r'<FactoryIO [^>]*>', text).group(0)
    new = hdr
    if mine:
        new = re.sub(r'Type="[^"]*"', 'Type="MySavedScene"', new)
    for k, v in (("Year", now.year), ("Month", now.month), ("Day", now.day), ("Hour", now.hour),
                 ("Minute", now.minute), ("Second", now.second)):
        new = re.sub(rf'{k}="\d+"', f'{k}="{v}"', new)
    text = text.replace(hdr, new, 1)
    if desc is not None:
        text = re.sub(r'<Description Data="[^"]*" />', f'<Description Data="{html.escape(desc, quote=True)}" />', text, count=1)
    return text


# ---------------------------------------------------------------- 고치기
def set_force(text, ident, value):
    all_t = tags(text)
    hit = find_tag(all_t, ident)
    if not hit:
        sys.exit(f"태그 없음: {ident}")
    for t in sorted(hit, key=lambda t: -t["span"][0]):
        s, e = t["span"]
        el = text[s:e]
        if value == "release":
            new = re.sub(r'UseForcedValue="\w+"', 'UseForcedValue="False"', el)
        else:
            v = {"on": "True", "off": "False", "true": "True", "false": "False"}.get(str(value).lower(), str(value))
            new = re.sub(r'UseForcedValue="\w+" ForcedValue="[^"]*"', f'UseForcedValue="True" ForcedValue="{v}"', el)
        text = text[:s] + new + text[e:]
    return text, len(hit)


def set_emitter(text, parts, bases):
    n = 0

    def rep(m):
        nonlocal n
        n += 1
        b = "".join(f' {x}="True"' for x in bases)
        p = "".join(f' {x}="True"' for x in parts)
        return f'{m.group(1)}<Bases{b} />{m.group(2)}<Parts{p} />{m.group(3)}'
    text = re.sub(r'(<Emitter [^>]*>\s*)<Bases[^>]*/>(\s*)<Parts[^>]*/>(\s*</Emitter>)', rep, text)
    return text, n


def rename(text, pairs):
    all_t = tags(text)
    done = 0
    for old, new in pairs:
        hit = find_tag(all_t, old)
        if not hit:
            print(f"  [건너뜀] 태그 없음: {old}")
            continue
        for t in sorted(hit, key=lambda t: -t["span"][0]):
            s, e = t["span"]
            el = re.sub(r'Name="[^"]*"', lambda _: f'Name="{html.escape(new, quote=True)}"', text[s:e], count=1)
            text = text[:s] + el + text[e:]
            done += 1
        all_t = tags(text)
    return text, done


def map_modbus(text, only=None, include_forced=False):
    """연결 안 된 태그를 빈 칸에 연결. only: 이름에 이 글자가 든 태그만. 강제값 태그(Emitter · Remover 등)는 기본 제외."""
    mb = modbus_points(text)
    if not mb:
        sys.exit("ModbusTCPServer 블록이 없습니다 (Factory I/O 2.5 씬이 아님).")
    slots = {k: {} for k in LIMIT}
    for kind, idx, key in mb["points"]:
        if kind in slots and idx < mb["count"].get(kind, 0):
            slots[kind][idx] = key
    used = {k for d in slots.values() for k in d.values() if k != ZERO}
    added = []
    for t in tags(text):
        if t["key"] in used:
            continue
        if only and not any(o.lower() in t["name"].lower() for o in only):
            continue
        if t["forced"] is not None and not include_forced:
            continue
        kind = ("Bit" if t["kind"] == "Bool" else "Numeric") + ("Input" if t["io"] == "Input" else "Output")
        d = slots[kind]
        free = [i for i in sorted(d) if d[i] == ZERO]
        i = free[0] if free else (max(d) + 1 if d else 0)
        if i >= LIMIT[kind]:
            sys.exit(f"{kind} 한도({LIMIT[kind]}) 초과")
        d[i] = t["key"]
        used.add(t["key"])
        added.append((t["name"], kind, i))
    cnt = dict(mb["count"])
    for k, d in slots.items():
        cnt[k] = max(cnt.get(k, 0), (max(d) + 1) if d else 0)
    ind = mb["match"].group(1)
    inner = ind + "  "
    order = ["BitInput", "BitOutput", "FloatInput", "FloatOutput", "IntInput", "IntOutput", "NumericInput", "NumericOutput"]
    body = mb["match"].group(2)
    cnt_line = re.search(r'<PointIOCount [^>]*/>', body).group(0)
    new_cnt = cnt_line
    for k in order:
        new_cnt = re.sub(rf'{k}Count="\d+"', f'{k}Count="{cnt.get(k, 0)}"', new_cnt)
    off_line = re.search(r'<PointIOOffset [^>]*/>', body).group(0)
    props = re.search(r'<Properties [^>]*/>', body).group(0)
    lines = [new_cnt, off_line]
    for k in ["BitInput", "BitOutput", "NumericInput", "NumericOutput"]:
        for i in range(cnt.get(k, 0)):
            lines.append(f'<{k}{i} PointIOKey="{slots[k].get(i, ZERO)}" />')
    for k, i, key in mb["points"]:                      # Float/Int 칸은 그대로 둠
        if k not in LIMIT:
            lines.append(f'<{k}{i} PointIOKey="{key}" />')
    lines.append(props)
    block = f'{ind}<ModbusTCPServer>' + "".join(inner + x for x in lines) + f'{ind}</ModbusTCPServer>'
    s, e = mb["match"].span()
    text = text[:s] + block + text[e:]
    return set_driver(text, DRIVER["modbus-server"]), added


def map_opc(text, rows, server):
    all_t = tags(text)
    items = []
    for ident, item in rows:
        hit = find_tag(all_t, ident)
        if not hit:
            print(f"  [건너뜀] 태그 없음: {ident}")
            continue
        t = hit[0]
        inp = t["key"] if t["io"] == "Input" else ZERO
        outp = t["key"] if t["io"] == "Output" else ZERO
        disp = item.rsplit(".", 1)[-1]
        items.append((inp, outp, item, disp, t["name"]))
    m = driver_block(text, "OPCClientDA")
    if not m:
        sys.exit("OPCClientDA 블록이 없습니다.")
    ind = m.group(1)
    inner = ind + "  "
    lines = [f'<Server Url="opcda://localhost/{server}" Name="{server}" ItemCount="{len(items)}" '
             f'MaxItemCount="{max(200, len(items))}" StartsWithFilter="" ContainsFilter="" />']
    for i, (inp, outp, item, disp, _) in enumerate(items):
        lines.append(f'<Item{i} InputPointIOKey="{inp}" OutputPointIOKey="{outp}" '
                     f'ItemName="{html.escape(item, quote=True)}" ItemDisplayName="{html.escape(disp, quote=True)}" />')
    block = f'{ind}<OPCClientDA>' + "".join(inner + x for x in lines) + f'{ind}</OPCClientDA>'
    s, e = m.span()
    text = text[:s] + block + text[e:]
    return set_driver(text, DRIVER["opc"]), items


# ---------------------------------------------------------------- F2 시험 씬
TESTS = [
    # 이름, 원본 씬, 설명, 받침, 박스, 강제 ON 태그
    ("F2a_asrs_pallet_SL", "Automated Warehouse",
     "Project B F2a: Pallet + Small/Large box -> rack (crane by Modbus)", ["Pallet"], ["BoxS", "BoxL"],
     ["Entry Conveyor", "Exit Conveyor"]),
    ("F2b_asrs_box_only_SL", "Automated Warehouse",
     "Project B F2b: Small/Large box WITHOUT pallet -> rack (crane by Modbus)", [], ["BoxS", "BoxL"],
     ["Entry Conveyor", "Exit Conveyor"]),
    ("F2c_popup_SL", "Sorting by Weight",
     "Project B F2c: Pop-up Wheel Sorter with Small/Large box (+RFID readers on Monday)", [], ["BoxS", "BoxL"],
     ["Entry conveyor", "Load scale", "Left conveyor", "Right conveyor", "Front conveyor"]),
    ("F2d_popup_pallet_L", "Sorting by Weight",
     "Project B F2d: Pop-up Wheel Sorter with Pallet + Large box", ["Pallet"], ["BoxL"],
     ["Entry conveyor", "Load scale", "Left conveyor", "Right conveyor", "Front conveyor"]),
    ("F2e_vision_pusher_SL", "Separating Station",
     "Project B F2e: Vision value for Small/Large box + Pusher", [], ["BoxS", "BoxL"],
     ["Entry conveyor 1", "Entry conveyor 2", "Conveyor 1", "Conveyor 2"]),
    ("F2f_stopblade_SL", "Sorting Station",
     "Project B F2f: Stop Blade + Vision with Small/Large box", [], ["BoxS", "BoxL"],
     ["Entry conveyor", "Exit conveyor"]),
]


def make_tests(out_dir):
    made = []
    for name, src, desc, bases, parts, force_on in TESTS:
        path = os.path.join(SCENES_DIR, src + ".factoryio")
        if not os.path.exists(path):
            print(f"  [건너뜀] 기본 씬 없음: {path}")
            continue
        text = load(path)
        text, n = set_emitter(text, parts, bases)
        if n == 0:
            sys.exit(f"{src}: Emitter 설정을 찾지 못함")
        for tname in force_on:
            text, k = set_force(text, tname, "on")
        text = set_driver(text, DRIVER["modbus-server"])
        text = touch_header(text, desc)
        out = os.path.join(out_dir, name + ".factoryio")
        save(out, text)
        made.append(out)
    return made


# ---------------------------------------------------------------- 출력
def cmd_info(path):
    text = load(path)
    hdr = re.search(r'<FactoryIO ([^>]*)>', text).group(1)
    print(f"# {os.path.basename(path)}")
    print("  " + " ".join(x for x in re.findall(r'\w+="[^"]*"', hdr) if not x.startswith(("Hour", "Minute", "Second"))))
    cd = current_driver(text)
    print(f"  선택 드라이버: {cd} ({DRIVER_NAME.get(cd, '기타')})")
    em = re.findall(r'<Emitter [^>]*>\s*<Bases([^>]*)/>\s*<Parts([^>]*)/>', text)
    for b, p in em:
        print(f"  Emitter 받침:{b.strip() or ' 없음'} / 박스:{p.strip()}")
    mbt = modbus_address_table(text)
    opc = {}
    m = driver_block(text, "OPCClientDA")
    if m:
        for inp, outp, item in re.findall(r'InputPointIOKey="([^"]+)" OutputPointIOKey="([^"]+)" ItemName="([^"]*)"', m.group(2)):
            for k in (inp, outp):
                if k != ZERO:
                    opc[k] = html.unescape(item)
    print(f"  {'부품':30s} {'태그':34s} {'입출력':6s} {'형식':5s} {'강제':6s} {'Modbus':12s} OPC")
    for t in tags(text):
        mb = mbt.get(t["key"])
        mbs = f"{mb[0]}:{mb[1]}" if mb else "-"
        print(f"  {t['prefab'][:30]:30s} {t['name'][:34]:34s} {t['io']:6s} {t['kind']:5s} {str(t['forced'] or ''):6s} "
              f"{mbs:12s} {opc.get(t['key'], '')}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("info"); a.add_argument("scene")
    a = sp.add_parser("tests"); a.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "factoryio_test"))
    a = sp.add_parser("force"); a.add_argument("scene"); a.add_argument("out"); a.add_argument("pairs", nargs="+")
    a = sp.add_parser("rename"); a.add_argument("scene"); a.add_argument("out"); a.add_argument("--csv", required=True)
    a = sp.add_parser("emitter"); a.add_argument("scene"); a.add_argument("out")
    a.add_argument("--parts", default="BoxS,BoxL"); a.add_argument("--bases", default="")
    a = sp.add_parser("map-modbus"); a.add_argument("scene"); a.add_argument("out")
    a.add_argument("--only", nargs="*", help="이름에 이 글자가 든 태그만 (예: RFID)")
    a.add_argument("--include-forced", action="store_true")
    a = sp.add_parser("map-opc"); a.add_argument("scene"); a.add_argument("out"); a.add_argument("--csv", required=True)
    a.add_argument("--server", default="Mitsubishi.MXOPC.6")
    args = ap.parse_args()

    if args.cmd == "info":
        cmd_info(args.scene)
    elif args.cmd == "tests":
        made = make_tests(os.path.abspath(args.out))
        print(f"시험 씬 {len(made)}개. 열기: \"{FIO_DIR}\\Factory IO.exe\" \"load:<경로>\"")
    elif args.cmd == "force":
        text = load(args.scene)
        for p in args.pairs:
            k, v = p.split("=", 1)
            text, n = set_force(text, k, v)
            print(f"  {k} = {v} ({n}개)")
        save(args.out, touch_header(text), args.scene)
    elif args.cmd == "emitter":
        text, n = set_emitter(load(args.scene), [x for x in args.parts.split(",") if x], [x for x in args.bases.split(",") if x])
        print(f"  Emitter {n}개 변경")
        save(args.out, touch_header(text), args.scene)
    elif args.cmd == "rename":
        with io.open(args.csv, encoding="utf-8-sig", newline="") as f:
            pairs = [(r[0].strip(), r[1].strip()) for r in csv.reader(f) if len(r) >= 2 and r[0].strip() and not r[0].startswith("#")]
        text, n = rename(load(args.scene), pairs)
        print(f"  이름 변경 {n}개")
        save(args.out, touch_header(text), args.scene)
    elif args.cmd == "map-modbus":
        text, added = map_modbus(load(args.scene), args.only, args.include_forced)
        table = modbus_address_table(text)
        names = {t["name"]: t["key"] for t in tags(text)}
        for name, kind, i in added:
            area, addr, _ = table.get(names.get(name), ("?", "?", ""))
            print(f"  + {name:40s} → {kind}{i}  (Python: {area}:{addr})")
        print(f"  새로 연결 {len(added)}개, 드라이버 = Modbus TCP Server")
        save(args.out, touch_header(text), args.scene)
    elif args.cmd == "map-opc":
        with io.open(args.csv, encoding="utf-8-sig", newline="") as f:
            rows = [(r[0].strip(), r[1].strip()) for r in csv.reader(f) if len(r) >= 2 and r[0].strip() and not r[0].startswith("#")]
        text, items = map_opc(load(args.scene), rows, args.server)
        print(f"  OPC 항목 {len(items)}개, 드라이버 = OPC Client DA ({args.server})")
        save(args.out, touch_header(text), args.scene)


if __name__ == "__main__":
    main()
