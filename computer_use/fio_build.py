"""Factory I/O 씬 조립 도우미 (make_fio_scene_v6.py · 시험 씬이 같이 씀).

부품 원본(템플릿)
- Factory I/O 기본 씬(설치 폴더 Scenes) : 벨트 · 롤러 · 스토퍼 · 센서 · 크레인 · 랙 · 조작반 등
- 부품 견본 씬 factoryio_test/_parts_v6.factoryio : 기본 씬에 없는 RFID Reader · Curved Belt/Roller ·
  Roller Stop · Alarm Siren · Stack Light · Emitter(Controller-Defined) — 11-23 Factory I/O 화면에서 놓고 저장한 것

좌표 1u = 0.125 m, 정수만(소수가 있으면 Factory I/O 가 씬을 못 엶).
"""
from __future__ import annotations

import copy
import math
import uuid
from pathlib import Path
from xml.etree import ElementTree as ET

FIO = Path(r"C:/Program Files (x86)/Real Games/Factory IO")
SCENES = FIO / "Scenes"
HERE = Path(__file__).resolve().parent
PARTS = HERE.parent / "factoryio_test" / "_parts_v6.factoryio"
IO_TAGS = ("BinaryInput", "BinaryOutput", "IntInput", "IntOutput",
           "AnalogueInput", "AnalogueOutput", "FloatInput", "FloatOutput")
FWD = {"+x": (1, 0), "-x": (-1, 0), "+z": (0, 1), "-z": (0, -1)}
_cache: dict[str, ET.Element] = {}


def load_scene(path: Path) -> ET.Element:
    return ET.fromstring(Path(path).read_text(encoding="utf-8-sig"))


def _root(scene: str) -> ET.Element:
    if scene not in _cache:
        _cache[scene] = load_scene(PARTS if scene == "_parts" else SCENES / f"{scene}.factoryio")
    return _cache[scene]


def template(prefab: str, scene: str = "_parts", name: str | None = None, nth: int = 0) -> ET.Element:
    found = [o for o in _root(scene).findall("Object") if o.find("Proxy").get("PrefabName") == prefab
             and (name is None or any(e.get("Name") == name for e in o.iter()))]
    if not found:
        raise SystemExit(f"template not found: {prefab} {name} in {scene}")
    return copy.deepcopy(found[nth])


def ios(o: ET.Element) -> list[ET.Element]:
    return [e for e in o.iter() if e.tag in IO_TAGS]


def right_of(fwd):
    fx, fz = FWD[fwd] if isinstance(fwd, str) else fwd
    th = math.atan2(fx, fz)
    return round(math.cos(th)), round(-math.sin(th))


class Scene:
    def __init__(self):
        self.objects: list[ET.Element] = []

    def place(self, o, pos, fwd):
        fx, fz = FWD[fwd] if isinstance(fwd, str) else fwd
        th = math.atan2(fx, fz)
        p = o.find("Proxy")
        p.set("Key", str(uuid.uuid4()))
        x, y, z = (int(round(v)) for v in pos)
        p.find("Position").attrib.update(X=str(x), Y=str(y), Z=str(z))
        s, c = math.sin(th / 2), math.cos(th / 2)
        r = lambda v: "0" if abs(v) < 1e-9 else f"{v:.7g}"
        p.find("Rotation").attrib.update(X="0", Y=r(s), Z="0", W=r(c))
        p.find("Forward").attrib.update(X=r(math.sin(th)), Y="0", Z=r(math.cos(th)))
        p.find("Up").attrib.update(X="0", Y="1", Z="0")
        p.find("Right").attrib.update(X=r(math.cos(th)), Y="0", Z=r(-math.sin(th)))
        p.find("FineRotation").text = "0"
        p.find("FinePosition").text = "0"

    def add(self, o, pos, fwd, names=None, force=None):
        """names: I/O 순서대로 새 이름(None 은 그대로). force: {index: 값} 씬 안 강제값."""
        self.place(o, pos, fwd)
        for e in o.iter():
            if e.get("Key") and e.tag != "Proxy":
                e.set("Key", str(uuid.uuid4()))
        lst = ios(o)
        for i, e in enumerate(lst):
            if names and i < len(names) and names[i]:
                e.set("Name", names[i])
            e.set("UseForcedValue", "False")
            e.set("ForcedValue", "False" if e.tag.startswith("Binary") else "0")
        for i, v in (force or {}).items():
            lst[i].set("UseForcedValue", "True")
            lst[i].set("ForcedValue", v)
        self.objects.append(o)
        return o

    def io_by_name(self):
        out = {}
        for o in self.objects:
            for e in ios(o):
                out.setdefault(e.get("Name"), []).append(e)
        return out

    def write(self, out: Path, views, current=1, desc="", opc_items=None, base="Automated Warehouse"):
        """views: [(이름, 카메라 xyz, 피벗 xyz)], opc_items: [(씬 I/O 이름, OPC 항목 ID, 'Boolean'|'Int')]"""
        counter: dict[str, int] = {}
        for o in self.objects:
            for e in ios(o):
                e.set("Address", str(counter.get(e.tag, 0)))
                counter[e.tag] = counter.get(e.tag, 0) + 1
        wh = _root(base)
        scene = ET.Element("FactoryIO", wh.attrib)
        for child in wh:
            if child.tag == "Object":
                continue
            if child.tag == "Camera":
                cam = ET.SubElement(scene, "Camera")
                for name, c, pv in list(views) + [("Current",) + tuple(views[current - 1][1:])]:
                    cp = ET.SubElement(cam, "CameraPosition", Name=name, Type="OrbitCamera")
                    d = ET.SubElement(cp, "Data")
                    ET.SubElement(d, "CameraPosition", X=str(c[0]), Y=str(c[1]), Z=str(c[2]))
                    ET.SubElement(d, "PivotPosition", X=str(pv[0]), Y=str(pv[1]), Z=str(pv[2]))
                scene.extend(self.objects)
                continue
            scene.append(copy.deepcopy(child))
        scene.set("Type", "MySavedScene")
        d = scene.find("Description")
        if d is not None:
            d.set("Data", desc)
        drivers = scene.find("Drivers")
        if opc_items:
            empty = "00000000-0000-0000-0000-000000000000"
            byname = self.io_by_name()
            drivers.set("CurrentDriver", "16384")
            da = drivers.find("OPCClientDA")
            da.clear()
            items = []
            for io_name, item, typ in opc_items:
                if io_name not in byname:
                    raise SystemExit(f"씬에 없는 I/O: {io_name}")
                for e in byname[io_name]:
                    is_in = e.tag.endswith("Input")
                    items.append(dict(InputPointIOKey=e.get("Key") if is_in else empty,
                                      OutputPointIOKey=empty if is_in else e.get("Key"),
                                      ItemName=item, ItemDisplayName=item.split(".", 1)[-1], ItemDataType=typ))
            ET.SubElement(da, "Server", Url="Mitsubishi.MXOPC.6", Name="Mitsubishi.MXOPC.6",
                          ItemCount=str(len(items)), MaxItemCount=str(max(256, len(items))),
                          StartsWithFilter="", ContainsFilter="")
            for i, it in enumerate(items):
                ET.SubElement(da, f"Item{i}", it)
        out = Path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        ET.indent(scene, "  ")
        out.write_text(ET.tostring(scene, encoding="unicode"), encoding="utf-8-sig")
        return out
