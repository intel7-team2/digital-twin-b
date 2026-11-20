import sys, time, ctypes as C
from ctypes import wintypes as W
sys.path.insert(0, sys.argv[1]); sys.path.insert(0, sys.argv[2] + "/tools")
import c_env_opc_raw as o
from mxopc_tags import TAGS
o.ole32.CoInitializeEx(None, 0)
unk = C.c_void_p(); o.ole32.CoCreateInstance(C.byref(o.CLSID_MXOPC), None, 4, C.byref(o.IID_IUnknown), C.byref(unk))
srv = o.qi(unk, o.IID_IOPCServer); br = o.qi(srv, o.IID_IOPCBrowse)
browse = o.vcall(br, 5, C.c_long, W.DWORD, C.c_wchar_p, W.WORD, W.DWORD, C.POINTER(C.c_void_p))
o.vcall(br, 4, C.c_long, W.DWORD, C.c_wchar_p)(br, 3, "CSIM")
e = C.c_void_p(); browse(br, 2, "", 0, 0, C.byref(e)); leaves = set(o.enum_strings(e))
want = [t[0] for t in TAGS]
print(f"브라우즈 태그 {len(leaves)}개 · TAGS {len(want)}개 · 빠진 것 {sorted(set(want)-leaves)} · 남는 것 {sorted(leaves-set(want))}")
items = [f"CSIM.{d}" for d in want]
hgrp = W.DWORD(); rate = W.DWORD(); mgt = C.c_void_p()
o.hr_ok(o.vcall(srv, 3, C.c_long, C.c_wchar_p, W.BOOL, W.DWORD, W.DWORD, C.c_void_p, C.c_void_p, W.DWORD, C.POINTER(W.DWORD), C.POINTER(W.DWORD), C.POINTER(o.GUID), C.POINTER(C.c_void_p))(
    srv, "verify", True, 1000, 1, None, None, 0x409, C.byref(hgrp), C.byref(rate), C.byref(o.IID_IOPCItemMgt), C.byref(mgt)), "AddGroup")
defs = (o.ITEMDEF * len(items))(*[o.ITEMDEF(None, t, True, i + 1, 0, None, 0, 0) for i, t in enumerate(items)])
pres = C.POINTER(o.ITEMRESULT)(); perr = C.POINTER(C.c_long)()
o.vcall(mgt, 3, C.c_long, W.DWORD, C.POINTER(o.ITEMDEF), C.POINTER(C.POINTER(o.ITEMRESULT)), C.POINTER(C.POINTER(C.c_long)))(mgt, len(items), defs, C.byref(pres), C.byref(perr))
ok = [(items[i], pres[i].hServer, pres[i].vt) for i in range(len(items)) if perr[i] == 0]
print(f"AddItems 성공 {len(ok)}/{len(items)}")
vts = {}
for t, h, vt in ok: vts.setdefault(vt, 0); vts[vt] += 1
print("정식 형식(vt):", vts, "(11=Boolean, 18=UI2)")
time.sleep(3)
sio = o.qi(mgt, o.IID_IOPCSyncIO)
read = o.vcall(sio, 3, C.c_long, W.DWORD, W.DWORD, C.POINTER(W.DWORD), C.POINTER(C.POINTER(o.ITEMSTATE)), C.POINTER(C.POINTER(C.c_long)))
hs = (W.DWORD * len(ok))(*[h for _, h, _ in ok]); st = C.POINTER(o.ITEMSTATE)(); er = C.POINTER(C.c_long)()
read(sio, 1, len(ok), hs, C.byref(st), C.byref(er))
good = sum(1 for i in range(len(ok)) if st[i].q == 192 and er[i] == 0)
print(f"캐시 읽기 품질 Good {good}/{len(ok)} · 예: " + ", ".join(f"{ok[i][0]}={o.var_value(st[i].val)}" for i in (0, 20, 60, 99) if i < len(ok)))
