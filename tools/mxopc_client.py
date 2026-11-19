"""
MX OPC Server (OPC DA) 연결 도구 - Computer Use 테스트 C5 후속

OPC DA 는 32비트 COM 이므로 **32비트 Python + pywin32** 로 실행합니다.
  pymanager install 3.12-32
  python3.12-32 -m pip install pywin32

사용법 (Dtwin_pj 폴더에서)
  python3.12-32 tools/mxopc_client.py                          # 서버 상태 · 장치 · 태그 목록 앞부분
  python3.12-32 tools/mxopc_client.py --read CNT_GOOD CLAMP    # 태그 읽기
  python3.12-32 tools/mxopc_client.py --write CNT_GOOD 4321    # 쓰고 다시 읽기 (--restore 로 원래 값 복원)

  --device QSIM  (기본)    MX OPC Configurator 의 장치 이름
  --server Mitsubishi.MXOPC.6

주의
  - MX OPC 는 Configurator 에 **등록된 태그**만 다룰 수 있습니다. QSIM.D1700 같은 직접 번지는 0xC0040007(없는 태그 ID).
  - 사용하는 COM 래퍼: OPC.SiemensDAAuto (TIA/WinCC 설치에 포함된 OPC DA Automation 2.0, 32비트).
    OPC Foundation 의 OPC.Automation 이 있으면 --wrapper OPC.Automation 으로 바꿀 수 있습니다.
"""

import argparse
import struct
import sys

OPC_DS_DEVICE = 2
QUALITY_GOOD = 192


def connect(wrapper, server):
    if struct.calcsize("P") * 8 != 32:
        sys.exit("32비트 Python 으로 실행하세요 (예: python3.12-32). OPC DA Automation 래퍼가 32비트 전용입니다.")
    try:
        import win32com.client
    except ImportError:
        sys.exit("pywin32 가 필요합니다: python3.12-32 -m pip install pywin32")
    s = win32com.client.Dispatch(wrapper)
    s.Connect(server)
    return s


def list_tags(s, device, limit=10):
    b = s.CreateBrowser()
    b.ShowBranches()
    devices = [b.Item(i) for i in range(1, b.Count + 1)]
    print(f"[장치] {len(devices)}개: {', '.join(devices)}")
    if device not in devices:
        print(f"  '{device}' 장치가 없습니다.")
        return
    b.MoveDown(device)
    b.ShowLeafs()
    ids = [b.GetItemID(b.Item(i)) for i in range(1, b.Count + 1)]
    print(f"[{device} 태그] {len(ids)}개 (앞 {limit}개)")
    for i in ids[:limit]:
        print("   " + i)


def add_item(group, item_id, handle):
    try:
        return group.OPCItems.AddItem(item_id, handle)
    except Exception as e:  # pywintypes.com_error
        hr = getattr(e, "hresult", None) or (e.args[0] if e.args else 0)
        exc = getattr(e, "excepinfo", None) or (e.args[2] if len(e.args) > 2 else None)
        if exc and len(exc) > 5 and exc[5]:
            hr = exc[5]  # DISP_E_EXCEPTION 안의 실제 OPC 오류 코드
        print(f"   {item_id:<24} 등록 실패 0x{hr & 0xFFFFFFFF:08X} (0xC0040007 = 없는 태그 ID)")
        return None


def read(item):
    value, quality, ts = item.Read(OPC_DS_DEVICE)
    return value, quality, ts


def main():
    p = argparse.ArgumentParser(description="MX OPC Server (OPC DA) 연결 확인")
    p.add_argument("--server", default="Mitsubishi.MXOPC.6")
    p.add_argument("--wrapper", default="OPC.SiemensDAAuto")
    p.add_argument("--device", default="QSIM")
    p.add_argument("--read", nargs="*", default=[], metavar="TAG")
    p.add_argument("--write", nargs=2, metavar=("TAG", "VALUE"))
    p.add_argument("--restore", action="store_true", help="--write 후 원래 값으로 되돌림")
    args = p.parse_args()

    s = connect(args.wrapper, args.server)
    print(f"[연결] {args.server}  ServerState={s.ServerState} (1=RUNNING)  "
          f"{s.VendorInfo} {s.MajorVersion}.{s.MinorVersion}.{s.BuildNumber}  "
          f"Python {sys.version.split()[0]} {struct.calcsize('P') * 8}bit")
    try:
        if not args.read and not args.write:
            list_tags(s, args.device)
            return

        g = s.OPCGroups.Add("py_probe")
        g.IsActive = True
        handle = 1

        if args.read:
            print("[읽기]")
            for tag in args.read:
                it = add_item(g, f"{args.device}.{tag}", handle)
                handle += 1
                if it is None:
                    continue
                v, q, ts = read(it)
                ok = "Good" if q == QUALITY_GOOD else "not good"
                print(f"   {args.device + '.' + tag:<24} = {v}  quality={q}({ok})  {ts}")

        if args.write:
            tag, raw = args.write
            it = add_item(g, f"{args.device}.{tag}", handle)
            if it is None:
                return
            before, _, _ = read(it)
            value = int(raw) if raw.lstrip("-").isdigit() else raw
            it.Write(value)
            after, q, _ = read(it)
            print(f"[쓰기] {args.device}.{tag}: {before} → 씀 {value} → 다시 읽기 {after} (quality={q})")
            if args.restore:
                it.Write(before)
                back, q, _ = read(it)
                print(f"[복원] {args.device}.{tag} = {back} (quality={q})")
    finally:
        s.Disconnect()


if __name__ == "__main__":
    main()
