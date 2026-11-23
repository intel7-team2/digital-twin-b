"""
MX OPC 프로젝트(.mdb, Jet) 직접 고치기 — Configurator 화면 조작을 줄이기 위한 도구.
32비트 cscript + Jet OLEDB 로 실행합니다(이 PC 기본 설치로 됨). 쓰기 전에 항상 백업을 남깁니다.

  show        [--mdb P]                         장치 · 연결값 · 태그 수 · Simulate 상태
  simulate    on|off --device CSIM [--mdb P]    장치와 그 태그의 Simulate 켜기/끄기
  add-io      --device CSIM [--set io|v5|all]  태그 추가 (있는 이름은 건너뜀): io = fio_io_map_v6.csv 신규(안), v5 = tools/mxopc_tags.py TAGS
  copy-conn   --src B.mdb --src-device QSIM --device CSIM [--mdb P]
                                                다른 프로젝트 장치의 연결 설정(PRM_*)을 그대로 복사
                                                (예: B PC의 QSIM = GX Simulator 연결을 이 PC CSIM 에)

기본 --mdb 는 레지스트리의 MX OPC 실행 프로젝트(지금 test_results/MXOPC_C_env.mdb).
MX OPC Server · Configurator 가 켜져 있으면 쓰지 않습니다(파일 잠김 · 덮어씀 방지).
"""
import argparse
import csv
import datetime as dt
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import winreg

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CSCRIPT = r"C:\Windows\SysWOW64\cscript.exe"
BACKUP_DIR = os.path.join(ROOT, "test_results", "mdb_backup")
TAG_COLS = ("ID, ParentID, Name, Sequence, Description, Enable, StartingAddress, RegisterName, BasicDataType, "
            "AccessRights, Simulate, SimulationSignal, PollRateDefinition, DataLength, VectorNumElements")


def runtime_mdb():
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Mitsubishi\MXOPCServer\Configuration", 0,
                            winreg.KEY_READ | winreg.KEY_WOW64_32KEY) as k:
            return winreg.QueryValueEx(k, "FileName")[0]
    except OSError:
        return None


def running(*exes):
    out = subprocess.run(["tasklist", "/NH"], capture_output=True, text=True, encoding="cp949", errors="replace").stdout.lower()
    return [e for e in exes if e.lower() in out]


def run_vbs(body, mdb):
    vbs = ('Set cn = CreateObject("ADODB.Connection")\r\n'
           'cn.Open "Provider=Microsoft.Jet.OLEDB.4.0;Data Source=" & WScript.Arguments(0)\r\n' + body)
    fd, path = tempfile.mkstemp(suffix=".vbs")
    os.close(fd)
    with io.open(path, "w", encoding="utf-16") as f:     # 한글 설명 때문에 UTF-16(BOM)
        f.write(vbs)
    try:
        r = subprocess.run([CSCRIPT, "//nologo", path, mdb], capture_output=True)
        out = (r.stdout + r.stderr).decode("cp949", errors="replace").strip()
        if r.returncode != 0 or re.search(r"\.vbs\(\d+, \d+\)", out):     # cscript 는 실행 오류에도 0을 돌려줄 때가 있음
            sys.exit(f"cscript 오류 ({r.returncode}):\n{out}")
        return out
    finally:
        os.remove(path)


def guard_write(mdb):
    busy = running("MXOPC.exe", "MXConfigurator.exe")
    if busy:
        sys.exit(f"{', '.join(busy)} 실행 중 — 끄고 다시 실행하세요 (OPC 클라이언트 · Factory I/O · 중계 서버를 먼저 끄면 MXOPC.exe도 꺼짐).")
    os.makedirs(BACKUP_DIR, exist_ok=True)
    bak = os.path.join(BACKUP_DIR, f"{os.path.splitext(os.path.basename(mdb))[0]}_{dt.datetime.now():%Y%m%d_%H%M%S}.mdb")
    shutil.copy2(mdb, bak)
    print(f"[백업] {bak}")


def q(s):
    return str(s).replace("'", "''")


SHOW = r'''
Set rs = cn.Execute("SELECT ID, Name, Simulate, PRM_PcIf, PRM_PlcIf, PRM_CpuType, PRM_UnitType, PRM_ProtocolType, PRM_HostAddress, PRM_PortNumber, Description FROM MX_Channel_Devices")
Do While Not rs.EOF
  Set c = cn.Execute("SELECT COUNT(*) AS n, SUM(IIF(Simulate,1,0)) AS s FROM MX_DataTagsRoot WHERE ParentID=" & rs("ID"))
  WScript.Echo "장치 " & rs("Name") & " (ID " & rs("ID") & ") Simulate=" & rs("Simulate") & " | PcIf=" & rs("PRM_PcIf") & " PlcIf=" & rs("PRM_PlcIf") & " CpuType=" & rs("PRM_CpuType") & " UnitType=" & rs("PRM_UnitType") & " ProtocolType=" & rs("PRM_ProtocolType") & " Host=" & rs("PRM_HostAddress") & ":" & rs("PRM_PortNumber") & " | 태그 " & c("n") & "개 (태그 Simulate " & c("s") & "개) | " & rs("Description")
  rs.MoveNext
Loop
'''


def cmd_show(mdb):
    print(f"# {mdb}")
    print(run_vbs(SHOW, mdb))


def device_id_vbs(device):
    return (f'Set d = cn.Execute("SELECT ID FROM MX_Channel_Devices WHERE Name=\'{q(device)}\'")\r\n'
            'If d.EOF Then\r\n  WScript.Echo "장치 없음"\r\n  WScript.Quit 2\r\nEnd If\r\n'
            'did = d("ID")\r\n')


def cmd_simulate(mdb, device, on):
    guard_write(mdb)
    v = "True" if on else "False"
    body = device_id_vbs(device) + (
        f'cn.Execute "UPDATE MX_Channel_Devices SET Simulate={v} WHERE ID=" & did\r\n'
        f'cn.Execute "UPDATE MX_DataTagsRoot SET Simulate={v} WHERE ParentID=" & did\r\n'
        'WScript.Echo "완료"\r\n')
    print(run_vbs(body, mdb))
    cmd_show(mdb)


def io_rows():
    rows = list(csv.DictReader(io.open(os.path.join(HERE, "fio_io_map_v6.csv"), encoding="utf-8-sig")))
    return [r for r in rows if r["구분"].startswith("신규")]


def tag_rows(which):
    """(번지, 워드 여부, 설명) 목록. which = io(fio_io_map 신규) · v5(tools/mxopc_tags.py TAGS) · all"""
    out = []
    if which in ("v5", "all"):
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        import mxopc_tags
        out += [(d, k == "W", desc) for d, k, desc in mxopc_tags.TAGS]
    if which in ("io", "all"):
        out += [(r["번지"], r["형식"] == "W", f'{r["Factory I/O 부품(안)"]} · {r["설명"]}') for r in io_rows()]
    return out


def cmd_add_io(mdb, device, which="io"):
    rows = tag_rows(which)
    guard_write(mdb)
    lines = [device_id_vbs(device),
             'Set m = cn.Execute("SELECT MAX(ID) AS i FROM MX_DataTagsRoot")\r\n',
             'nid = m("i")\r\nIf IsNull(nid) Then nid = 1\r\n',
             'Set m = cn.Execute("SELECT MAX(Sequence) AS s FROM MX_DataTagsRoot WHERE ParentID=" & did)\r\n',
             'seq = m("s")\r\nIf IsNull(seq) Then seq = 0\r\n',
             'n = 0\r\nskip = 0\r\nOn Error Resume Next\r\n']
    for dev, word, desc in rows:
        kind = dev[0]
        num = int(dev[1:], 16) if kind in "XY" else int(dev[1:])
        btype, sig = (2, 9) if word else (1, 6)
        desc = q(desc)[:250]
        lines.append(
            f'Set c = cn.Execute("SELECT COUNT(*) AS k FROM MX_DataTagsRoot WHERE ParentID=" & did & " AND Name=\'{dev}\'")\r\n'
            'If c("k") = 0 Then\r\n'
            '  nid = nid + 1\r\n  seq = seq + 1\r\n'
            f'  cn.Execute "INSERT INTO MX_DataTagsRoot ({TAG_COLS}) VALUES (" & nid & ", " & did & ", \'{dev}\', " & seq & ", \'{desc}\', True, {num}, \'{kind}\', {btype}, 3, False, {sig}, 1, 1, 1)"\r\n'
            '  If Err.Number <> 0 Then\r\n'
            f'    WScript.Echo "ERR {dev} " & Err.Description\r\n'
            '    Err.Clear\r\n'
            '  Else\r\n    n = n + 1\r\n  End If\r\n'
            'Else\r\n  skip = skip + 1\r\nEnd If\r\n')
    # X · Y 는 16진 번지: AddressBase = 1 이어야 읽힘 (0이면 품질 12 · 0x80004005, 11-23 확인. 기존 X/Y 태그도 1)
    lines.append('On Error GoTo 0\r\n'
                 'cn.Execute "UPDATE MX_DataTagsRoot SET AddressBase=1 WHERE ParentID=" & did & '
                 '" AND RegisterName IN (\'X\',\'Y\') AND Name LIKE \'[XY]1[5-9]__\'"\r\n'
                 # 워드 태그: AddressDatatype = 1(워드 단위) · AdvancedDataType = 65538. 0이면 비트 단위 접근이라
                 # 쓰기에서 아래 4비트가 빠짐(1234 → 1232, 11-23 확인). 기존 D 태그도 1 · 65538
                 'cn.Execute "UPDATE MX_DataTagsRoot SET AddressDatatype=1, AdvancedDataType=65538 WHERE ParentID=" & did & '
                 '" AND RegisterName=\'D\' AND BasicDataType=2 AND Name LIKE \'D1[5-9]__\'"\r\n')
    lines.append('WScript.Echo "추가 " & n & "개 · 이미 있음 " & skip & "개"\r\n')
    print(run_vbs("".join(lines), mdb))
    cmd_show(mdb)


def cmd_copy_conn(mdb, device, src, src_device):
    guard_write(mdb)
    # 원본 장치의 PRM_ · BAK_ 값을 읽어 UPDATE 문으로 만든다
    read = (f'Set s = CreateObject("ADODB.Connection")\r\n'
            f's.Open "Provider=Microsoft.Jet.OLEDB.4.0;Data Source={src}"\r\n'
            f'Set rs = s.Execute("SELECT * FROM MX_Channel_Devices WHERE Name=\'{q(src_device)}\'")\r\n'
            'If rs.EOF Then\r\n  WScript.Echo "원본 장치 없음"\r\n  WScript.Quit 2\r\nEnd If\r\n'
            'For Each f In rs.Fields\r\n'
            '  If Left(f.Name, 4) = "PRM_" Or Left(f.Name, 4) = "BAK_" Or f.Name = "DeviceType" Then\r\n'
            '    v = f.Value\r\n'
            '    If IsNull(v) Then\r\n      WScript.Echo f.Name & "|N|"\r\n'
            '    Else\r\n      WScript.Echo f.Name & "|" & f.Type & "|" & v\r\n    End If\r\n'
            '  End If\r\nNext\r\n')
    out = run_vbs(read, src)
    sets = []
    for line in out.splitlines():
        name, typ, *val = line.split("|")
        val = "|".join(val)
        if typ == "N":
            sets.append(f"{name}=NULL")
        elif typ in ("11",):                       # adBoolean
            sets.append(f"{name}={'True' if val in ('True', '참', '-1') else 'False'}")
        elif typ in ("2", "3", "4", "5", "17", "131"):
            sets.append(f"{name}={val}")
        else:
            sets.append(f"{name}='{q(val)}'")
    if not sets:
        sys.exit("원본 연결값을 읽지 못함")
    body = device_id_vbs(device)
    for i in range(0, len(sets), 25):           # Jet 은 한 UPDATE 에 필드가 많으면 "Too many fields defined"
        sql = ("UPDATE MX_Channel_Devices SET " + ", ".join(sets[i:i + 25]) + " WHERE ID=").replace('"', '""')
        body += f'cn.Execute "{sql}" & did\r\n'
    body += f'WScript.Echo "연결값 {len(sets)}개 복사"\r\n'
    print(run_vbs(body, mdb))
    cmd_show(mdb)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mdb", default=None)
    sp = ap.add_subparsers(dest="action", required=True)
    sp.add_parser("show")
    a = sp.add_parser("simulate"); a.add_argument("state", choices=("on", "off")); a.add_argument("--device", default="CSIM")
    a = sp.add_parser("add-io"); a.add_argument("--device", default="CSIM")
    a.add_argument("--set", choices=("io", "v5", "all"), default="io", help="io = fio_io_map 신규 · v5 = mxopc_tags.py TAGS · all = 둘 다")
    a = sp.add_parser("copy-conn"); a.add_argument("--src", required=True); a.add_argument("--src-device", required=True)
    a.add_argument("--device", default="CSIM")
    args = ap.parse_args()
    mdb = os.path.abspath(args.mdb or runtime_mdb() or "")
    if not os.path.exists(mdb):
        sys.exit(f"MX OPC 프로젝트 파일 없음: {mdb}")
    if not os.path.exists(CSCRIPT):
        sys.exit("32비트 cscript 가 없습니다.")
    if args.action == "show":
        cmd_show(mdb)
    elif args.action == "simulate":
        cmd_simulate(mdb, args.device, args.state == "on")
    elif args.action == "add-io":
        cmd_add_io(mdb, args.device, args.set)
    elif args.action == "copy-conn":
        cmd_copy_conn(mdb, args.device, os.path.abspath(args.src), args.src_device)


if __name__ == "__main__":
    main()
