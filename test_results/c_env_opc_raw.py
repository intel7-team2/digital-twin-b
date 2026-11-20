"""래퍼 없이 OPC DA 2.0 커스텀 인터페이스로 MX OPC Server 에 붙는 시험 (ctypes만, 설치 없음).
사용: py -3.12 opc_raw.py [장치] [태그 ...]          (읽기 전용)
      py -3.12 opc_raw.py <장치> --write <태그> <값>  (읽기 → 쓰기 → 다시 읽기 → 원래 값 복원)
"""
import ctypes as C, struct, sys, uuid
from ctypes import wintypes as W

ole32, oleaut32 = C.oledll.ole32, C.oledll.oleaut32
ole32.CoTaskMemFree.restype = None
ole32.CoTaskMemFree.argtypes = [C.c_void_p]

class GUID(C.Structure):
    _fields_ = [("b", C.c_ubyte * 16)]
    def __init__(self, s): super().__init__(); C.memmove(self.b, uuid.UUID(s).bytes_le, 16)

CLSID_MXOPC = GUID("926587F4-4886-4e00-9883-43B7EF39E4B1")
IID_IOPCServer = GUID("39c13a4d-011e-11d0-9675-0020afd8adb3")
IID_IOPCBrowse = GUID("39c13a4f-011e-11d0-9675-0020afd8adb3")
IID_IOPCItemMgt = GUID("39c13a54-011e-11d0-9675-0020afd8adb3")
IID_IOPCSyncIO = GUID("39c13a52-011e-11d0-9675-0020afd8adb3")
IID_IUnknown = GUID("00000000-0000-0000-C000-000000000046")

def vcall(obj, idx, restype, *argtypes):
    vtbl = C.cast(obj, C.POINTER(C.POINTER(C.c_void_p)))[0]
    return C.WINFUNCTYPE(restype, C.c_void_p, *argtypes)(vtbl[idx])

def hr_ok(hr, what):
    if hr < 0 or hr > 1:   # S_FALSE(1) 허용
        raise OSError(f"{what} 실패 HRESULT=0x{hr & 0xFFFFFFFF:08X}")
    return hr

def release(o):
    if o: vcall(o, 2, C.c_ulong)(o)

def qi(o, iid):
    p = C.c_void_p(); hr_ok(vcall(o, 0, C.c_long, C.POINTER(GUID), C.POINTER(C.c_void_p))(o, C.byref(iid), C.byref(p)), "QueryInterface"); return p

class FILETIME(C.Structure): _fields_ = [("lo", W.DWORD), ("hi", W.DWORD)]
class STATUS(C.Structure):
    _fields_ = [("ft1", FILETIME), ("ft2", FILETIME), ("ft3", FILETIME), ("state", W.DWORD), ("groups", W.DWORD),
                ("bw", W.DWORD), ("maj", W.WORD), ("min", W.WORD), ("build", W.WORD), ("res", W.WORD), ("vendor", C.c_wchar_p)]
class VARIANT(C.Structure):
    _fields_ = [("vt", W.WORD), ("r1", W.WORD), ("r2", W.WORD), ("r3", W.WORD), ("v", C.c_ubyte * 16)]
class ITEMDEF(C.Structure):
    _fields_ = [("path", C.c_wchar_p), ("id", C.c_wchar_p), ("active", W.BOOL), ("hClient", W.DWORD),
                ("blobsz", W.DWORD), ("blob", C.c_void_p), ("vt", W.WORD), ("res", W.WORD)]
class ITEMRESULT(C.Structure):
    _fields_ = [("hServer", W.DWORD), ("vt", W.WORD), ("res", W.WORD), ("rights", W.DWORD), ("blobsz", W.DWORD), ("blob", C.c_void_p)]
class ITEMSTATE(C.Structure):
    _fields_ = [("hClient", W.DWORD), ("ts", FILETIME), ("q", W.WORD), ("res", W.WORD), ("val", VARIANT)]

def var_value(v):
    b = bytes(v.v)
    if v.vt == 2: return struct.unpack_from("<h", b)[0]
    if v.vt in (3, 22): return struct.unpack_from("<i", b)[0]
    if v.vt == 18: return struct.unpack_from("<H", b)[0]
    if v.vt in (19, 23): return struct.unpack_from("<I", b)[0]
    if v.vt == 11: return struct.unpack_from("<h", b)[0] != 0
    if v.vt == 4: return struct.unpack_from("<f", b)[0]
    if v.vt == 5: return struct.unpack_from("<d", b)[0]
    if v.vt == 8:
        p = struct.unpack_from("<Q" if C.sizeof(C.c_void_p) == 8 else "<I", b)[0]
        return C.wstring_at(p) if p else ""
    return f"(vt={v.vt}) {b[:8].hex()}"

def var_make(vt, value):
    v = VARIANT(); v.vt = vt
    if vt == 11: struct.pack_into("<h", v.v, 0, -1 if value else 0)
    elif vt in (2,): struct.pack_into("<h", v.v, 0, int(value))
    elif vt in (18,): struct.pack_into("<H", v.v, 0, int(value) & 0xFFFF)
    elif vt in (3,): struct.pack_into("<i", v.v, 0, int(value))
    elif vt in (19,): struct.pack_into("<I", v.v, 0, int(value))
    elif vt == 4: struct.pack_into("<f", v.v, 0, float(value))
    else: raise ValueError(f"vt {vt} 쓰기 미지원")
    return v

def enum_strings(e):
    out = []
    if not e: return out
    nxt = vcall(e, 3, C.c_long, W.ULONG, C.POINTER(C.c_void_p), C.POINTER(W.ULONG))
    while True:
        p = C.c_void_p(); n = W.ULONG()
        hr = nxt(e, 1, C.byref(p), C.byref(n))
        if n.value == 0: break
        out.append(C.wstring_at(p.value)); ole32.CoTaskMemFree(p)
        if hr != 0: break
    release(e); return out

def main():
    args = sys.argv[1:]
    write = None
    if "--write" in args:
        i = args.index("--write"); write = (args[i + 1], args[i + 2]); args = args[:i]
    dev = args[0] if args else None
    tags = args[1:]
    ole32.CoInitializeEx(None, 0)
    print(f"[Python] {struct.calcsize('P') * 8}비트 · 래퍼 없음(ctypes, OPC DA 커스텀 인터페이스)")
    unk = C.c_void_p()
    ole32.CoCreateInstance(C.byref(CLSID_MXOPC), None, 4, C.byref(IID_IUnknown), C.byref(unk))   # CLSCTX_LOCAL_SERVER
    srv = qi(unk, IID_IOPCServer); release(unk)
    ps = C.POINTER(STATUS)()
    hr_ok(vcall(srv, 6, C.c_long, C.POINTER(C.POINTER(STATUS)))(srv, C.byref(ps)), "GetStatus")
    s = ps.contents
    print(f"[서버] Mitsubishi.MXOPC.6 ServerState={s.state} (1=RUNNING) 버전 {s.maj}.{s.min}.{s.build} · {s.vendor}")

    br = qi(srv, IID_IOPCBrowse)
    org = W.DWORD(); vcall(br, 3, C.c_long, C.POINTER(W.DWORD))(br, C.byref(org))
    browse = vcall(br, 5, C.c_long, W.DWORD, C.c_wchar_p, W.WORD, W.DWORD, C.POINTER(C.c_void_p))
    chpos = vcall(br, 4, C.c_long, W.DWORD, C.c_wchar_p)
    getid = vcall(br, 6, C.c_long, C.c_wchar_p, C.POINTER(C.c_wchar_p))
    e = C.c_void_p(); browse(br, 1, "", 0, 0, C.byref(e))
    devs = enum_strings(e)
    print(f"[장치] {len(devs)}개 (주소 공간 {'계층' if org.value == 1 else '평면'}): {devs}")
    if dev is None and devs: dev = devs[0]
    if dev:
        chpos(br, 3, dev)    # OPC_BROWSE_TO
        e = C.c_void_p(); browse(br, 2, "", 0, 0, C.byref(e))
        leaves = enum_strings(e)
        ids = []
        for n in leaves[:10]:
            p = C.c_wchar_p(); getid(br, n, C.byref(p)); ids.append(p.value)
        print(f"[{dev} 태그] {len(leaves)}개 · 앞 10개: {ids}")
        d17 = [x for x in leaves if x.upper() in ("D1700", "D1710", "M1920", "D1900")]
        print(f"[{dev}] 1500~19FF 디바이스 이름 태그(D1700·D1710·M1920·D1900) 등록: {d17 or '없음'}")
        if not tags and not write: tags = [f"{dev}.{x}" for x in leaves[:3]]
    release(br)
    items = [t if "." in t else f"{dev}.{t}" for t in tags]
    if write: items = [write[0] if "." in write[0] else f"{dev}.{write[0]}"]
    if not items: return
    hgrp = W.DWORD(); rate = W.DWORD(); mgt = C.c_void_p()
    add_group = vcall(srv, 3, C.c_long, C.c_wchar_p, W.BOOL, W.DWORD, W.DWORD, C.c_void_p, C.c_void_p, W.DWORD,
                      C.POINTER(W.DWORD), C.POINTER(W.DWORD), C.POINTER(GUID), C.POINTER(C.c_void_p))
    hr_ok(add_group(srv, "claude_test", True, 1000, 1, None, None, 0x409, C.byref(hgrp), C.byref(rate), C.byref(IID_IOPCItemMgt), C.byref(mgt)), "AddGroup")
    defs = (ITEMDEF * len(items))(*[ITEMDEF(None, t, True, i + 1, 0, None, 0, 0) for i, t in enumerate(items)])
    pres = C.POINTER(ITEMRESULT)(); perr = C.POINTER(C.c_long)()
    vcall(mgt, 3, C.c_long, W.DWORD, C.POINTER(ITEMDEF), C.POINTER(C.POINTER(ITEMRESULT)), C.POINTER(C.POINTER(C.c_long)))(
        mgt, len(items), defs, C.byref(pres), C.byref(perr))
    good = []
    for i, t in enumerate(items):
        if perr[i] != 0: print(f"  {t}: AddItems 오류 0x{perr[i] & 0xFFFFFFFF:08X}")
        else: good.append((t, pres[i].hServer, pres[i].vt))
    sio = qi(mgt, IID_IOPCSyncIO)
    read = vcall(sio, 3, C.c_long, W.DWORD, W.DWORD, C.POINTER(W.DWORD), C.POINTER(C.POINTER(ITEMSTATE)), C.POINTER(C.POINTER(C.c_long)))
    wr = vcall(sio, 4, C.c_long, W.DWORD, C.POINTER(W.DWORD), C.POINTER(VARIANT), C.POINTER(C.POINTER(C.c_long)))
    def do_read(lst):
        hs = (W.DWORD * len(lst))(*[h for _, h, _ in lst]); st = C.POINTER(ITEMSTATE)(); er = C.POINTER(C.c_long)()
        read(sio, 1, len(lst), hs, C.byref(st), C.byref(er))   # OPC_DS_DEVICE
        out = []
        for i, (t, _, _) in enumerate(lst):
            out.append((t, f"{var_value(st[i].val)} vt={st[i].val.vt}", st[i].q, er[i] & 0xFFFFFFFF))
        return out
    import time; time.sleep(2.5)
    if good:
        for t, v, q, e in do_read(good):
            print(f"  읽기 {t} = {v!r} · 품질 {q} (192=Good) · 결과 0x{e:08X}")
    if write and good:
        t, h, vt = good[0]
        old = do_read(good)[0]; old = (old[0], int(str(old[1]).split()[0]) if str(old[1]).split()[0].isdigit() else old[1], old[2], old[3])
        if old[2] != 192: print("  품질이 Good 이 아니라 쓰기 시험 생략"); return
        def do_write(val):
            hs = (W.DWORD * 1)(h); vs = (VARIANT * 1)(var_make(vt, val)); er = C.POINTER(C.c_long)()
            wr(sio, 1, hs, vs, C.byref(er)); return er[0] & 0xFFFFFFFF
        e1 = do_write(write[1]); time.sleep(2.5); now = do_read(good)[0]
        print(f"  쓰기 {t} ← {write[1]} (0x{e1:08X}) → 다시 읽기 {now[1]!r}")
        e2 = do_write(old[1]); time.sleep(2.5); back = do_read(good)[0]
        print(f"  복원 {t} ← {old[1]!r} (0x{e2:08X}) → 다시 읽기 {back[1]!r}")

if __name__ == "__main__":
    main()
