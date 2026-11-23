"""pyModbusTCP 대체(시험용, 최소 기능). 이 PC에 pyModbusTCP가 없어 설치 대신 씀."""
import socket, struct
class ModbusClient:
    def __init__(self, host="127.0.0.1", port=502, unit_id=1, timeout=2.0, auto_open=True):
        self.host, self.port, self.unit, self.timeout = host, port, unit_id, timeout
        self.s = None; self.tid = 0; self.last_error_as_txt = ""
    def _open(self):
        if self.s is None:
            self.s = socket.create_connection((self.host, self.port), self.timeout)
            self.s.settimeout(self.timeout)
    def _rx(self, n):
        b = b""
        while len(b) < n:
            c = self.s.recv(n - len(b))
            if not c: raise IOError("closed")
            b += c
        return b
    def _req(self, pdu):
        try:
            self._open(); self.tid = (self.tid + 1) & 0xFFFF
            self.s.sendall(struct.pack(">HHHB", self.tid, 0, len(pdu) + 1, self.unit) + pdu)
            h = self._rx(7); ln = struct.unpack(">H", h[4:6])[0]; body = self._rx(ln - 1)
            if body[0] & 0x80:
                self.last_error_as_txt = f"exception {body[1]}"; return None
            return body
        except Exception as e:
            self.last_error_as_txt = repr(e)
            try: self.s and self.s.close()
            except Exception: pass
            self.s = None; return None
    def _bits(self, fc, a, n):
        r = self._req(struct.pack(">BHH", fc, a, n))
        return None if r is None else [bool(r[2 + i // 8] >> (i % 8) & 1) for i in range(n)]
    def _regs(self, fc, a, n):
        r = self._req(struct.pack(">BHH", fc, a, n))
        return None if r is None else list(struct.unpack(">" + "H" * n, r[2:2 + 2 * n]))
    def read_coils(self, a, n=1): return self._bits(1, a, n)
    def read_discrete_inputs(self, a, n=1): return self._bits(2, a, n)
    def read_holding_registers(self, a, n=1): return self._regs(3, a, n)
    def read_input_registers(self, a, n=1): return self._regs(4, a, n)
    def write_single_coil(self, a, v): return True if self._req(struct.pack(">BHH", 5, a, 0xFF00 if v else 0)) is not None else None
    def write_single_register(self, a, v): return True if self._req(struct.pack(">BHH", 6, a, v & 0xFFFF)) is not None else None
    def write_multiple_coils(self, a, vals):          # FC15 (11-23 소프트 PLC 시험용 추가)
        n = len(vals); by = bytearray((n + 7) // 8)
        for i, v in enumerate(vals):
            if v: by[i // 8] |= 1 << (i % 8)
        return True if self._req(struct.pack(">BHHB", 15, a, n, len(by)) + bytes(by)) is not None else None
    def write_multiple_registers(self, a, vals):      # FC16
        return True if self._req(struct.pack(">BHHB", 16, a, len(vals), 2 * len(vals)) + b"".join(struct.pack(">H", v & 0xFFFF) for v in vals)) is not None else None
