"""
Project B · HMI 중계 서버 (MC 프로토콜 3E 바이너리) — HMI 연결 1안 (D20)

실물 PLC · MX Component 없이 Pro-face HMI(WinGP)를 GX Simulator2 에 붙이기 위한 중계 서버입니다.
WinGP 쪽에서는 미쓰비시 Q 시리즈 PLC(이더넷)처럼 보이고, 실제 값은 MX OPC Server 로 GX Simulator2 와 주고받습니다.

  WinGP (Pro-face, "Q Series QnU CPU Ethernet" 드라이버, IP = 이 PC)
     │  MC 프로토콜 3E 프레임 · 바이너리 · TCP/UDP
  hmi_mc_relay.py  ── backend opc: plc_link.OpcLink (MX OPC Server, 직접 연결 · 64/32비트 Python, D21)
     │              └ backend memory: 이 프로그램 안의 메모리 (WinGP 접속 시험용, PLC 없이)
  GX Simulator2 (PLC 래더)

화면은 실물 PLC 용과 같은 드라이버 · 같은 번지(D1900 …)로 만들고, Project C 환경에서는 접속 IP 만 실물 PLC 로 바꿉니다.

사용법
  python hmi_mc_relay.py --backend memory --demo            # PLC 없이: 메모리 + 카운터가 저절로 늘어남 (WinGP 접속 시험)
  python hmi_mc_relay.py --backend opc                      # MX OPC Server(장치 QSIM) 경유로 GX Simulator2 에 중계 (64비트도 됨)
  옵션: --port 5000 (TCP·UDP 같은 번호) --bind 0.0.0.0 --no-udp --opc-device QSIM --verbose

처리하는 명령 (3E 바이너리, Q/L 시리즈 형식: 디바이스 번호 3바이트 + 디바이스 코드 1바이트)
  0401 일괄 읽기 (00 워드 단위 / 01 비트 단위)     1401 일괄 쓰기 (00 / 01)
  0403 랜덤 읽기 (워드 · 더블워드)                  1402 랜덤 쓰기 (00 워드 · 더블워드 / 01 비트)
  0406 블록 일괄 읽기                               1406 블록 일괄 쓰기
  0101 CPU 형명 읽기 (Q03UDE 로 응답)               0619 루프백 테스트
  그 밖의 명령은 종료 코드 C059(명령 미지원)로 답하고 로그에 남깁니다 → WinGP 시험(10장 C7)에서 무엇이 오는지 확인.
디바이스: D · W · R · ZR · SD(워드), M · X · Y · L · B · SM(비트). OPC 백엔드는 MX OPC 에 등록된 태그(tools/mxopc_tags.py)만 읽고 쓸 수 있습니다.
"""

import argparse
import socketserver
import struct
import threading
import time

# 디바이스 코드 (3E 바이너리, Q/L 시리즈)
WORD_CODES = {0xA8: "D", 0xB4: "W", 0xAF: "R", 0xB0: "ZR", 0xA9: "SD"}
BIT_CODES = {0x90: "M", 0x9C: "X", 0x9D: "Y", 0x92: "L", 0xA0: "B", 0x91: "SM"}
HEX_KINDS = ("X", "Y", "B", "W")

END_OK = 0x0000
END_CMD = 0xC059       # 명령 · 서브커맨드 미지원
END_DEVICE = 0xC056    # 디바이스 범위 · 지정 오류
END_FORMAT = 0xC061    # 요청 데이터 길이 오류
END_BACKEND = 0xC05C   # 요청 내용 오류 (백엔드 읽기 · 쓰기 실패에 사용)

CPU_NAME = b"Q03UDECPU       "   # 16바이트. GX Works2 1.77F 시뮬레이션 기종(11장 W1)
CPU_CODE = 0x0268


def dev_name(kind, number):
    return f"{kind}{number:X}" if kind in HEX_KINDS else f"{kind}{number}"


class RelayError(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code


# ------------------------------------------------------------------ 백엔드
class MemoryBackend:
    """PLC 없이 WinGP 접속을 시험하는 메모리. --demo 면 게이트 카운터가 저절로 늘어남."""

    label = "memory"

    def __init__(self, demo=False):
        self.mem = {}
        self.lock = threading.Lock()
        if demo:
            self.mem.update({"D1900": 812, "D1901": 152, "D1902": 12})
            self._recalc()
            threading.Thread(target=self._demo_loop, daemon=True).start()

    def _recalc(self):
        g, n, i = (self.mem.get(f"D{1900 + k}", 0) for k in range(3))
        total = g + n + i
        self.mem["D1903"] = total
        self.mem["D1904"] = g * 1000 // total if total else 0

    def _demo_loop(self):
        k = 0
        while True:
            time.sleep(1.0)
            with self.lock:
                if self.mem.get("M1920"):                       # HMI 리셋 버튼 → 카운터 0
                    for d in range(1900, 1905):
                        self.mem[f"D{d}"] = 0
                else:
                    key = "D1900" if k % 5 else "D1901"
                    self.mem[key] = (self.mem.get(key, 0) + 1) & 0x7FFF
                    self._recalc()
                    self.mem["X1900"] = 1 - self.mem.get("X1900", 0)
            k += 1

    def read(self, names):
        with self.lock:
            return [int(self.mem.get(n, 0)) for n in names]

    def write(self, pairs):
        with self.lock:
            for n, v in pairs:
                self.mem[n] = int(v)


class OpcBackend:
    """MX OPC Server 경유 (plc_link.OpcLink). 태그 이름 = 디바이스 이름."""

    def __init__(self, link):
        self.link = link
        self.label = getattr(link, "label", "OPC")
        self.lock = threading.Lock()
        self._warned = set()

    def read(self, names):
        out = []
        with self.lock:
            for n in names:
                try:
                    out.append(int(self.link.read(n)))
                except Exception as e:
                    raise RelayError(END_BACKEND, f"OPC 읽기 실패 {n}: {e}") from None
        return out

    def write(self, pairs):
        with self.lock:
            for n, v in pairs:
                try:
                    self.link.write(n, v)
                except Exception as e:
                    raise RelayError(END_BACKEND, f"OPC 쓰기 실패 {n}: {e}") from None


# ------------------------------------------------------------------ MC 3E 처리
def _dev(data, off):
    """디바이스 번호 3바이트 + 코드 1바이트 → (kind, number, is_word)"""
    if off + 4 > len(data):
        raise RelayError(END_FORMAT, "디바이스 지정 길이 부족")
    num = data[off] | data[off + 1] << 8 | data[off + 2] << 16
    code = data[off + 3]
    if code in WORD_CODES:
        return WORD_CODES[code], num, True
    if code in BIT_CODES:
        return BIT_CODES[code], num, False
    raise RelayError(END_DEVICE, f"지원하지 않는 디바이스 코드 0x{code:02X}")


def _names(kind, start, count):
    return [dev_name(kind, start + i) for i in range(count)]


def _read_words(be, kind, start, points, is_word):
    """워드 단위 읽기. 비트 디바이스는 16점을 한 워드로 묶음(하위 비트 = 첫 점)."""
    if is_word:
        return be.read(_names(kind, start, points))
    bits = be.read(_names(kind, start, points * 16))
    return [sum((1 if bits[w * 16 + b] else 0) << b for b in range(16)) for w in range(points)]


def _write_words(be, kind, start, values, is_word):
    if is_word:
        be.write(list(zip(_names(kind, start, len(values)), [v & 0xFFFF for v in values])))
    else:
        pairs = []
        for w, v in enumerate(values):
            pairs += [(dev_name(kind, start + w * 16 + b), (v >> b) & 1) for b in range(16)]
        be.write(pairs)


def _s16(v):
    return v - 0x10000 if v & 0x8000 else v


def handle_command(be, cmd, sub, data, log):
    """명령 처리 → 응답 데이터(bytes). 실패는 RelayError."""
    if cmd == 0x0401:                                             # 일괄 읽기
        kind, start, is_word = _dev(data, 0)
        (points,) = struct.unpack_from("<H", data, 4)
        if sub in (0x0000, 0x0002):
            vals = _read_words(be, kind, start, points, is_word)
            return struct.pack(f"<{points}H", *[v & 0xFFFF for v in vals])
        if sub in (0x0001, 0x0003):
            if is_word:
                raise RelayError(END_DEVICE, "워드 디바이스를 비트 단위로 읽음")
            bits = be.read(_names(kind, start, points))
            out = bytearray()
            for i in range(0, points, 2):
                hi = 1 if bits[i] else 0
                lo = 1 if i + 1 < points and bits[i + 1] else 0
                out.append(hi << 4 | lo)
            return bytes(out)
    elif cmd == 0x1401:                                           # 일괄 쓰기
        kind, start, is_word = _dev(data, 0)
        (points,) = struct.unpack_from("<H", data, 4)
        body = data[6:]
        if sub in (0x0000, 0x0002):
            if len(body) < points * 2:
                raise RelayError(END_FORMAT, "쓰기 데이터 길이 부족")
            vals = list(struct.unpack_from(f"<{points}H", body, 0))
            _write_words(be, kind, start, [_s16(v) if is_word else v for v in vals], is_word)
            log(f"쓰기 {dev_name(kind, start)} × {points} = {vals[:8]}")
            return b""
        if sub in (0x0001, 0x0003):
            if is_word:
                raise RelayError(END_DEVICE, "워드 디바이스를 비트 단위로 씀")
            pairs = []
            for i in range(points):
                byte = body[i // 2]
                pairs.append((dev_name(kind, start + i), (byte >> 4) & 1 if i % 2 == 0 else byte & 1))
            be.write(pairs)
            log(f"쓰기 {dev_name(kind, start)} × {points} (비트) = {[v for _, v in pairs][:16]}")
            return b""
    elif cmd == 0x0403 and sub in (0x0000, 0x0002):               # 랜덤 읽기
        nw, nd = data[0], data[1]
        off, out = 2, bytearray()
        words, dwords = [], []
        for _ in range(nw):
            words.append(_dev(data, off))
            off += 4
        for _ in range(nd):
            dwords.append(_dev(data, off))
            off += 4
        for kind, num, is_word in words:
            out += struct.pack("<H", _read_words(be, kind, num, 1, is_word)[0] & 0xFFFF)
        for kind, num, is_word in dwords:
            lo, hi = _read_words(be, kind, num, 2, is_word) if is_word else _read_words(be, kind, num, 2, False)
            out += struct.pack("<HH", lo & 0xFFFF, hi & 0xFFFF)
        return bytes(out)
    elif cmd == 0x1402:                                           # 랜덤 쓰기
        if sub in (0x0001, 0x0003):                               # 비트 단위
            n, off, pairs = data[0], 1, []
            for _ in range(n):
                kind, num, is_word = _dev(data, off)
                if is_word:
                    raise RelayError(END_DEVICE, "랜덤 비트 쓰기에 워드 디바이스")
                pairs.append((dev_name(kind, num), data[off + 4] & 1))
                off += 5
            be.write(pairs)
            log(f"쓰기 (랜덤 비트) {pairs[:8]}")
            return b""
        if sub in (0x0000, 0x0002):                               # 워드 · 더블워드
            nw, nd = data[0], data[1]
            off = 2
            for _ in range(nw):
                kind, num, is_word = _dev(data, off)
                (v,) = struct.unpack_from("<H", data, off + 4)
                _write_words(be, kind, num, [_s16(v) if is_word else v], is_word)
                off += 6
            for _ in range(nd):
                kind, num, is_word = _dev(data, off)
                lo, hi = struct.unpack_from("<HH", data, off + 4)
                _write_words(be, kind, num, [_s16(lo), _s16(hi)] if is_word else [lo, hi], is_word)
                off += 8
            log(f"쓰기 (랜덤 워드 {nw} · 더블워드 {nd})")
            return b""
    elif cmd == 0x0406 and sub in (0x0000, 0x0002):               # 블록 읽기
        nw, nb = data[0], data[1]
        off, out = 2, bytearray()
        for _ in range(nw + nb):
            kind, num, is_word = _dev(data, off)
            (pts,) = struct.unpack_from("<H", data, off + 4)
            off += 6
            out += struct.pack(f"<{pts}H", *[v & 0xFFFF for v in _read_words(be, kind, num, pts, is_word)])
        return bytes(out)
    elif cmd == 0x1406 and sub in (0x0000, 0x0002):               # 블록 쓰기
        nw, nb = data[0], data[1]
        off = 2
        for _ in range(nw + nb):
            kind, num, is_word = _dev(data, off)
            (pts,) = struct.unpack_from("<H", data, off + 4)
            vals = list(struct.unpack_from(f"<{pts}H", data, off + 6))
            _write_words(be, kind, num, [_s16(v) if is_word else v for v in vals], is_word)
            off += 6 + pts * 2
        log(f"쓰기 (블록 {nw + nb}개)")
        return b""
    elif cmd == 0x0101 and sub == 0x0000:                         # CPU 형명 읽기
        return CPU_NAME + struct.pack("<H", CPU_CODE)
    elif cmd == 0x0619 and sub == 0x0000:                         # 루프백
        (n,) = struct.unpack_from("<H", data, 0)
        return struct.pack("<H", n) + data[2:2 + n]
    raise RelayError(END_CMD, f"미지원 명령 {cmd:04X} 서브 {sub:04X}")


def process_frame(be, req, log, stats):
    """3E 바이너리 요청 1개 → 응답 바이트. 요청이 3E 형식이 아니면 None."""
    if len(req) < 15 or req[0:2] != b"\x50\x00":
        return None
    route = req[2:7]                                              # 네트워크 · PC · 요구 대상 I/O · 국번
    (dlen,) = struct.unpack_from("<H", req, 7)
    if len(req) < 9 + dlen:
        return None
    _timer, cmd, sub = struct.unpack_from("<HHH", req, 9)
    data = req[15:9 + dlen]
    try:
        body = handle_command(be, cmd, sub, data, log)
        end = END_OK
    except RelayError as e:
        body, end = b"", e.code
        stats["errors"] += 1
        log(f"[오류 {e.code:04X}] {e}")
    except (struct.error, IndexError) as e:
        body, end = b"", END_FORMAT
        stats["errors"] += 1
        log(f"[오류 {END_FORMAT:04X}] 요청 형식 {cmd:04X}/{sub:04X}: {e}")
    stats["frames"] += 1
    stats["cmds"][f"{cmd:04X}/{sub:04X}"] = stats["cmds"].get(f"{cmd:04X}/{sub:04X}", 0) + 1
    if end != END_OK:
        # 오류 응답: 종료 코드 + 오류 정보(요청의 네트워크~국번 5바이트 + 명령 · 서브커맨드)
        body = route + struct.pack("<HH", cmd, sub)
    return b"\xD0\x00" + route + struct.pack("<HH", len(body) + 2, end) + body


# ------------------------------------------------------------------ 서버
class Relay:
    def __init__(self, backend, verbose=False):
        self.be = backend
        self.verbose = verbose
        self.stats = {"frames": 0, "errors": 0, "cmds": {}}
        self._seen = set()

    def log(self, msg, always=False):
        if always or self.verbose or msg.startswith("[오류") or msg.startswith("쓰기"):
            key = msg if msg.startswith("[오류") else None
            if key and key in self._seen and not self.verbose:
                return
            if key:
                self._seen.add(key)
            print(time.strftime("%H:%M:%S"), msg, flush=True)

    def frame(self, req):
        return process_frame(self.be, req, self.log, self.stats)


def make_tcp_handler(relay):
    class Handler(socketserver.BaseRequestHandler):
        def handle(self):
            relay.log(f"[TCP] 접속 {self.client_address[0]}:{self.client_address[1]}", always=True)
            buf = b""
            sock = self.request
            while True:
                try:
                    chunk = sock.recv(4096)
                except OSError:
                    break
                if not chunk:
                    break
                buf += chunk
                while len(buf) >= 9:
                    if buf[0:2] != b"\x50\x00":
                        relay.log(f"[오류] 3E 바이너리 형식이 아닌 요청 {buf[:16].hex()} (ASCII · 4E 프레임이면 WinGP 설정 확인)")
                        buf = b""
                        break
                    (dlen,) = struct.unpack_from("<H", buf, 7)
                    if len(buf) < 9 + dlen:
                        break
                    req, buf = buf[:9 + dlen], buf[9 + dlen:]
                    resp = relay.frame(req)
                    if resp:
                        sock.sendall(resp)
            relay.log(f"[TCP] 종료 {self.client_address[0]}:{self.client_address[1]}", always=True)
    return Handler


def make_udp_handler(relay):
    class Handler(socketserver.BaseRequestHandler):
        def handle(self):
            data, sock = self.request
            resp = relay.frame(data)
            if resp:
                sock.sendto(resp, self.client_address)
            elif data:
                relay.log(f"[오류] UDP: 3E 바이너리 형식이 아닌 요청 {data[:16].hex()}")
    return Handler


class _TCP(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class _UDP(socketserver.ThreadingUDPServer):
    allow_reuse_address = True
    daemon_threads = True


def start(relay, bind="0.0.0.0", port=5000, udp=True):
    servers = [_TCP((bind, port), make_tcp_handler(relay))]
    if udp:
        servers.append(_UDP((bind, port), make_udp_handler(relay)))
    for s in servers:
        threading.Thread(target=s.serve_forever, daemon=True).start()
    return servers


def main():
    p = argparse.ArgumentParser(description="HMI 중계 서버 (MC 프로토콜 3E 바이너리 → MX OPC / 메모리)")
    p.add_argument("--backend", choices=("memory", "opc"), default="opc")
    p.add_argument("--demo", action="store_true", help="memory 백엔드: 게이트 카운터가 1초마다 늘어남, M1920 이면 0")
    p.add_argument("--bind", default="0.0.0.0")
    p.add_argument("--port", type=int, default=5000)
    p.add_argument("--no-udp", action="store_true")
    p.add_argument("--opc-server", default="Mitsubishi.MXOPC.6")
    p.add_argument("--opc-device", default="QSIM")
    p.add_argument("--opc-wrapper", default="auto", help="auto(직접 연결) / direct / 래퍼 ProgID")
    p.add_argument("--opc-source", choices=("device", "cache"), default="device", help="Simulate 장치 시험은 cache")
    p.add_argument("--verbose", action="store_true", help="모든 요청 출력")
    args = p.parse_args()

    if args.backend == "memory":
        be = MemoryBackend(demo=args.demo)
    else:
        from plc_link import OPC_DS_CACHE, OPC_DS_DEVICE, OpcLink
        src = OPC_DS_CACHE if args.opc_source == "cache" else OPC_DS_DEVICE
        be = OpcBackend(OpcLink(args.opc_server, args.opc_device, args.opc_wrapper, src))
    relay = Relay(be, args.verbose)
    servers = start(relay, args.bind, args.port, not args.no_udp)
    print(f"[중계] MC 3E 바이너리 TCP{'' if args.no_udp else '·UDP'} {args.bind}:{args.port} → {be.label}"
          f"{' (데모 카운터)' if args.demo else ''} · WinGP 장치 IP = 이 PC 주소 (같은 PC면 127.0.0.1), 포트 {args.port}", flush=True)
    try:
        while True:
            time.sleep(10)
            st = relay.stats
            if st["frames"]:
                print(time.strftime("%H:%M:%S"), f"요청 {st['frames']}건 · 오류 {st['errors']}건 · 명령 {st['cmds']}", flush=True)
    except KeyboardInterrupt:
        print("\n[중계] 종료")
    finally:
        for s in servers:
            s.shutdown()
        if hasattr(be, "link"):
            be.link.close()


if __name__ == "__main__":
    main()
