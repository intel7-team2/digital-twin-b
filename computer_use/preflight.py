"""
월요일 Computer Use 작업 전 점검 — 이 PC에서 Project B 작업에 필요한 것이 다 있는지 한 번에 봅니다.
읽기만 합니다(설정 · 파일을 바꾸지 않음). --opc 를 주면 MX OPC Server에 붙어 장치 · 태그 수를 셉니다
(MXOPC.exe가 꺼져 있으면 COM이 띄움).

실행: python computer_use/preflight.py [--opc] [--md 결과.md]
"""
import argparse
import ctypes
import glob
import os
import platform
import re
import socket
import struct
import subprocess
import sys
import winreg

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FIO = r"C:\Program Files (x86)\Real Games\Factory IO"
FIO_LOG = os.path.expandvars(r"%USERPROFILE%\AppData\LocalLow\Real Games\Factory IO\Player.log")
FIO_CFG = os.path.expandvars(r"%LOCALAPPDATA%\Real Games\Factory IO\config.cfg")
PATHS = {
    "GX Works2": r"C:\Program Files (x86)\MELSOFT\GPPW2\GD2.exe",
    "GX Works3": r"C:\Program Files (x86)\MELSOFT\GPPW3\GXW3.exe",
    "MX OPC Server": r"C:\MELSEC\MX OPC Server 6.10\MXOPC.exe",
    "MX OPC Configurator": r"C:\MELSEC\MX OPC Server 6.10\MXConfigurator.exe",
    "GP-Pro EX 4.08": r"C:\Program Files (x86)\Pro-face\GP-Pro EX 4.08\Designer.Frame.exe",
    "WinGP (PC 런타임)": r"C:\Pro-face\WinGP\PCRuntime.exe",
    "Factory I/O": os.path.join(FIO, "Factory IO.exe"),
}
REPO_FILES = [
    "measurement_engine.py", "plc_link.py", "hmi_mc_relay.py", "hmi_counter_monitor.py",
    "tools/mxopc_tags.py", "test_results/W_test.gxw", "test_results/MXOPC_C_env.mdb",
    "computer_use/fio_io_map_v6.csv", "computer_use/fio_scene.py", "computer_use/fio_modbus.py",
]

rows = []


def add(group, item, ok, detail=""):
    mark = {True: "OK", False: "NG", None: "주의"}[ok]
    rows.append((group, item, mark, detail))


def reg(path, name, hive=winreg.HKEY_LOCAL_MACHINE):
    try:
        with winreg.OpenKey(hive, path, 0, winreg.KEY_READ | winreg.KEY_WOW64_32KEY) as k:
            return winreg.QueryValueEx(k, name)[0]
    except OSError:
        return None


def running(exe):
    try:
        out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {exe}", "/NH"], capture_output=True, text=True,
                             encoding="cp949", errors="replace").stdout
        return exe.lower() in out.lower()
    except OSError:
        return False


def port_in_use(port):
    s = socket.socket()
    s.settimeout(0.3)
    try:
        return s.connect_ex(("127.0.0.1", port)) == 0
    finally:
        s.close()


def check_screen():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass
    u = ctypes.windll.user32
    w, h = u.GetSystemMetrics(0), u.GetSystemMetrics(1)
    try:
        dpi = u.GetDpiForSystem()
    except Exception:
        dpi = 96
    scale = round(dpi / 96 * 100)
    add("화면", "해상도 · 배율", True if scale == 100 else None, f"{w}×{h}, 배율 {scale}%"
        + ("" if scale == 100 else " — 100%가 아니면 스크린샷 좌표가 어긋나기 쉬움"))
    add("화면", "PC 이름", True, platform.node())


def check_python():
    bits = struct.calcsize("P") * 8
    add("Python", "실행 버전", True, f"{platform.python_version()} {bits}비트 ({sys.executable})")
    import importlib.util as u
    for m, need in (("pymcprotocol", "MC 직결(--link mc)"), ("pyModbusTCP", "fio_modbus.py"),
                    ("pymodbus", "--link modbus (선택)"), ("PIL", "그림 확인(선택)")):
        ok = u.find_spec(m) is not None
        add("Python", m, True if ok else (None if m in ("pymodbus", "PIL") else False), need + ("" if ok else " — 없음"))


def check_fio():
    add("Factory I/O", "설치", os.path.exists(PATHS["Factory I/O"]), PATHS["Factory I/O"])
    if os.path.exists(FIO_LOG):
        log = open(FIO_LOG, encoding="utf-8", errors="replace").read()
        ver = re.findall(r"Version:\s*([\d.]+)", log)
        lic = re.findall(r"License is (\w+)", log)
        opt = re.findall(r"Options: [^\n]*;([A-Za-z &]+)\s*$", log, re.M)
        exp = re.findall(r"Expiration Date: ([^\n]+)", log)
        add("Factory I/O", "버전 (최근 실행 로그)", True, ver[-1] if ver else "로그에 없음")
        if lic:
            add("Factory I/O", "라이선스 (최근 실행)", lic[-1] == "valid",
                f"License is {lic[-1]}" + (f", 만료 {exp[-1]}" if exp else "") + (f", 에디션 {opt[-1]}" if opt else "")
                + ("" if lic[-1] == "valid" else " — 라이선스 갱신 전에는 씬을 실행할 수 없음"))
        else:
            add("Factory I/O", "라이선스", None, "로그에서 못 찾음 — Factory I/O를 한 번 켠 뒤 다시 점검")
    add("Factory I/O", "실행 중", None if running("Factory IO.exe") else True,
        "실행 중 (씬 열기 전 상태 확인)" if running("Factory IO.exe") else "꺼져 있음")
    if os.path.exists(FIO_CFG):
        cfg = open(FIO_CFG, encoding="utf-8-sig", errors="replace").read()
        def g(k):
            m = re.search(rf"^{re.escape(k)}\s*=\s*(.+)$", cfg, re.M)
            v = m.group(1).strip() if m else "?"
            return v[2:-1] if v.startswith("r'") and v.endswith("'") else v
        ad, auto = g("drivers.modbustcp_server.network_adapter"), g("drivers.modbustcp_server.auto_connect")
        add("Factory I/O", "Modbus Server 어댑터", True,
            f"{ad} → fio_modbus.py --host {'127.0.0.1' if 'Loopback' in ad else '(이 어댑터의 IP)'}")
        add("Factory I/O", "Modbus Server 자동 연결", True if auto == "True" else None,
            auto + ("" if auto == "True" else " — 드라이버 창에서 CONNECT를 한 번 눌러야 함"))
        add("Factory I/O", "My Scenes 폴더", None, g("scene.my_scenes_path") + " (시험 씬은 load: 경로로 엶)")
    tests = sorted(glob.glob(os.path.join(ROOT, "factoryio_test", "F2*.factoryio")))
    add("Factory I/O", "F2 시험 씬", True if len(tests) >= 6 else None,
        f"{len(tests)}개" + ("" if tests else " — python computer_use/fio_scene.py tests"))


def check_mxopc(do_connect):
    for k in ("MX OPC Server", "MX OPC Configurator"):
        add("MX OPC", k, os.path.exists(PATHS[k]), PATHS[k])
    fn = reg(r"SOFTWARE\Mitsubishi\MXOPCServer\Configuration", "FileName")
    add("MX OPC", "실행 프로젝트(레지스트리)", bool(fn and os.path.exists(fn)),
        f"{fn} " + ("(있음)" if fn and os.path.exists(fn) else "(파일 없음 — 서버 생성이 E_FAIL)"))
    if do_connect:
        sys.path.insert(0, ROOT)
        try:
            import plc_link
            link = plc_link.OpcDirectLink("Mitsubishi.MXOPC.6", "CSIM", plc_link.OPC_DS_CACHE)
            vals = {d: link.read(d) for d in ("D1900", "M1920", "X1900")}
            add("MX OPC", "OPC 접속(64비트 직접, 장치 CSIM 캐시 읽기)", True,
                "연결 · 읽기 정상 " + ", ".join(f"{k}={v}" for k, v in vals.items()))
            link.close()
        except SystemExit as e:
            add("MX OPC", "OPC 접속(64비트 직접)", False, str(e))
        except Exception as e:  # noqa: BLE001
            add("MX OPC", "OPC 접속(64비트 직접)", False, f"{type(e).__name__}: {e}")


def check_apps():
    for k in ("GX Works2", "GX Works3", "GP-Pro EX 4.08", "WinGP (PC 런타임)"):
        add("프로그램", k, os.path.exists(PATHS[k]), PATHS[k])
    add("프로그램", "MX Component", None, "있어도 쓰지 않음(D20)" if os.path.isdir(r"C:\MELSEC\Act") else "없음 (D20: 필요 없음)")


def check_ports():
    add("포트", "5000 (hmi_mc_relay.py)", None if port_in_use(5000) else True,
        "다른 프로그램이 사용 중" if port_in_use(5000) else "비어 있음")
    add("포트", "502 (Factory I/O Modbus Server)", True,
        "열려 있음 (Factory I/O 드라이버 연결됨)" if port_in_use(502) else "닫힘 (Factory I/O 드라이버 연결 전)")


def check_repo():
    miss = [f for f in REPO_FILES if not os.path.exists(os.path.join(ROOT, f))]
    add("저장소", "필수 파일", not miss, "모두 있음" if not miss else "없음: " + ", ".join(miss))
    try:
        br = subprocess.run(["git", "-C", ROOT, "branch", "--show-current"], capture_output=True, text=True).stdout.strip()
        add("저장소", "Git 브랜치", True, br or "(분리 상태)")
    except OSError:
        add("저장소", "Git 브랜치", None, "git 없음")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--opc", action="store_true", help="MX OPC Server에 실제로 붙어 봄")
    ap.add_argument("--md", help="결과를 마크다운 표로 저장")
    a = ap.parse_args()
    for fn in (check_screen, check_python, check_fio, lambda: check_mxopc(a.opc), check_apps, check_ports, check_repo):
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            add("점검", getattr(fn, "__name__", "?"), False, f"{type(e).__name__}: {e}")
    add("Computer Use", "Claude 앱 설정", None, "이 스크립트로는 확인 불가 — 설정 → Computer use 켜기(사람)")
    w = max(len(r[1]) for r in rows)
    for g, item, mark, detail in rows:
        print(f"[{mark:2s}] {g:11s} {item:{w}s}  {detail}")
    bad = sum(1 for r in rows if r[2] == "NG")
    print(f"\nNG {bad}개 · 주의 {sum(1 for r in rows if r[2] == '주의')}개")
    if a.md:
        with open(a.md, "w", encoding="utf-8") as f:
            f.write("| 구분 | 항목 | 결과 | 내용 |\n|---|---|---|---|\n")
            for g, item, mark, detail in rows:
                f.write(f"| {g} | {item} | {mark} | {detail.replace('|', '/')} |\n")
        print(f"[저장] {a.md}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
