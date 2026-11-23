"""MC 직결 시험 (PLC 없이): pymcprotocol(공개 라이브러리) ↔ hmi_mc_relay.py(memory 백엔드)
1부: 기본 읽기/쓰기 교차 확인
2부: measurement_engine serve 를 MC 링크로 돌려 핸드셰이크 3개(D1710 · D1740 · D1650) 왕복
사용: py -3.12 mc_test.py <repo> <db> [port]
"""
import os, sys, threading, time, types
REPO, DB = sys.argv[1], sys.argv[2]
PORT = int(sys.argv[3]) if len(sys.argv) > 3 else 5000
sys.path.insert(0, REPO)
import pymcprotocol
import hmi_mc_relay as relay

res = []
def check(name, ok, detail=""):
    res.append((name, ok)); print(f"[{'OK' if ok else 'NG'}] {name} {detail}")

# 중계 서버 (memory, TCP만) 시작
be = relay.MemoryBackend(demo=False)
r = relay.Relay(be) if hasattr(relay, "Relay") else None
srv = None
for nm in dir(relay):
    pass
def start_server():
    cls = [getattr(relay, n) for n in dir(relay) if isinstance(getattr(relay, n), type) and hasattr(getattr(relay, n), "frame")][0]
    rl = cls(be, verbose=False)
    return relay.start(rl, bind="127.0.0.1", port=PORT, udp=False)
start_server(); time.sleep(0.5)

def client():
    c = pymcprotocol.Type3E(plctype="Q"); c.setaccessopt(commtype="binary")
    c.connect("127.0.0.1", PORT); return c

# ---------------- 1부
c = client()
try:
    cpu = c.read_cputype(); check("CPU 형명 읽기(0101)", "Q03UDE" in cpu[0], str(cpu))
except Exception as e: check("CPU 형명 읽기(0101)", False, repr(e))
c.batchwrite_wordunits("D1700", [1, 289, 652, 280]); v = c.batchread_wordunits("D1700", 4)
check("D1700~D1703 일괄 쓰기/읽기", v == [1, 289, 652, 280], str(v))
c.batchwrite_wordunits("D1900", [812, 152, 12]); v = c.batchread_wordunits("D1900", 3)
check("D1900~D1902 카운터", v == [812, 152, 12], str(v))
c.batchwrite_wordunits("D1710", [-1]); v = c.batchread_wordunits("D1710", 1)
check("음수 워드(-1)", v == [-1], str(v))
c.batchwrite_bitunits("M1920", [1]); v = c.batchread_bitunits("M1920", 1)
check("M1920 비트 쓰기/읽기", v == [1] and be.read(["M1920"]) == [1], str(v))
c.batchwrite_bitunits("X1903", [1]); v = c.batchread_bitunits("X1903", 1)
check("X1903(16진 번호) 비트", v == [1] and be.read(["X1903"]) == [1], f"{v} mem={be.mem.get('X1903')}")
w, d = c.randomread(word_devices=["D1700", "D1902"], dword_devices=[])
check("랜덤 읽기(0403)", w == [1, 12], str(w))
c.randomwrite(word_devices=["D1950", "D1951"], word_values=[7, 8], dword_devices=[], dword_values=[])
check("랜덤 쓰기(1402)", be.read(["D1950", "D1951"]) == [7, 8], str(be.read(["D1950", "D1951"])))
c.batchwrite_bitunits("M1920", [0]); c.batchwrite_wordunits("D1700", [0, 0, 0, 0]); c.batchwrite_wordunits("D1710", [0])
c.close()

# ---------------- 2부: serve 를 MC 링크로
class McLink:
    label = "MC 3E(pymcprotocol)"
    def __init__(self, host, port):
        self.c = pymcprotocol.Type3E(plctype="Q"); self.c.setaccessopt(commtype="binary"); self.c.connect(host, port)
        self.lk = threading.Lock()
    def read_words(self, start, count=1):
        with self.lk: return self.c.batchread_wordunits(start, count)
    def write_words(self, start, values):
        with self.lk: self.c.batchwrite_wordunits(start, list(values))
    def write_bit(self, dev, state):
        with self.lk: self.c.batchwrite_bitunits(dev, [1 if state else 0])
    def close(self): self.c.close()

import plc_link, measurement_engine as me
plc_link.open_link = lambda args: McLink("127.0.0.1", PORT)
me.open_db(DB).close()
import subprocess
subprocess.run([sys.executable, os.path.join(REPO, "measurement_engine.py"), "handoff", "--start", "101", "--count", "3", "--db", DB],
               check=True, capture_output=True)
args = types.SimpleNamespace(db=DB, interval=0.05, mode="id", link="mc")
threading.Thread(target=me.cmd_serve, args=(args,), daemon=True).start()
time.sleep(0.5)

plc = client()   # PLC 역할
def wait(dev, val, t=5):
    end = time.time() + t
    while time.time() < end:
        if plc.batchread_wordunits(dev, 1)[0] == val: return True
        time.sleep(0.05)
    return False

def station(req, result, pack, rc, cells, name):
    plc.batchwrite_wordunits(f"D{req+1}", [pack, rc, 0, cells])
    t0 = time.time(); plc.batchwrite_wordunits(f"D{req}", [1])
    ok = wait(f"D{req+3}", 1); dt = (time.time() - t0) * 1000
    out = plc.batchread_wordunits(f"D{result}", 4)
    plc.batchwrite_wordunits(f"D{req}", [0]); ok2 = wait(f"D{req+3}", 0)
    exp = me.judge(me.measure(pack, rc, "id", cells), rc, cells)
    check(f"{name} 핸드셰이크 D{req}", ok and ok2 and out[0] == exp, f"PACK {pack} 결과 {out} 기대 판정 {exp} 응답 {dt:.0f}ms")

station(1710, 1700, 101, 0, me.pack_info(me.open_db(DB), 101)[0], "메인 검사")
station(1740, 1730, 102, 1, me.pack_info(me.open_db(DB), 102)[0], "재검사")
plc.batchwrite_wordunits("D1651", [103, 412, 0]); plc.batchwrite_wordunits("D1650", [1])
ok = wait("D1653", 1); plc.batchwrite_wordunits("D1650", [0]); ok2 = wait("D1653", 0)
conn = me.open_db(DB)
row = conn.execute("SELECT * FROM results WHERE pack_id=103").fetchall()
check("발열 격리 핸드셰이크 D1650", ok and ok2 and len(row) >= 1, f"DB rows={len(row)}")
n = conn.execute("SELECT COUNT(*) FROM results WHERE pack_id IN (101,102)").fetchone()[0]
check("검사 결과 DB 기록", n >= 2, f"rows={n}")
plc.close()
print(f"\n합계 {sum(o for _, o in res)}/{len(res)} 통과")
