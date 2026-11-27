"""
Modbus TCP 연결 확인 도구 (Computer Use 테스트 C3용)

Factory I/O의 "Modbus TCP/IP Server" 드라이버 등 Modbus 서버에 붙어서
4가지 영역(Coils / Discrete Inputs / Holding Registers / Input Registers)을 읽고,
--write 를 주면 Holding Register 하나에 값을 써서 다시 읽어 봅니다.

사용법 (Dtwin_pj 폴더에서)
  pip install pymodbus
  python tools/modbus_probe.py --host 192.168.0.214 --port 502   # 시연 PC = 이 PC(SmST14, A21). 예전 테스트 PC는 192.168.0.213
  python tools/modbus_probe.py --addr 0 --count 8 --write 1234

Factory I/O Modbus Server 기준 방향
  Discrete Inputs  = Factory I/O 센서(Bool)   → 클라이언트가 읽음
  Coils            = Factory I/O 액추에이터(Bool) ← 클라이언트가 씀
  Input Registers  = Factory I/O 센서 값(Int/Float)
  Holding Registers= Factory I/O 액추에이터 값(Int/Float), RFID Command / Write Data 등
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from plc_link import client_call as _client_call  # pymodbus 버전별 unit 인자명 차이 흡수


def main():
    p = argparse.ArgumentParser(description="Modbus TCP 연결 확인")
    p.add_argument("--host", required=True, help="Factory I/O Modbus Server 주소 (시연 PC 192.168.0.214, 같은 PC면 127.0.0.1)")
    p.add_argument("--port", type=int, default=502)
    p.add_argument("--unit", type=int, default=1)
    p.add_argument("--addr", type=int, default=0, help="읽기 시작 주소 (0-based)")
    p.add_argument("--count", type=int, default=8)
    p.add_argument("--write", type=int, default=None, help="Holding Register --addr 에 쓸 값")
    args = p.parse_args()

    try:
        from pymodbus.client import ModbusTcpClient
    except ImportError:
        sys.exit("pymodbus 가 필요합니다: pip install pymodbus")

    c = ModbusTcpClient(args.host, port=args.port)
    if not c.connect():
        sys.exit(f"[실패] {args.host}:{args.port} 연결 안 됨 (서버 실행 여부 · 포트 · 방화벽 확인)")
    print(f"[연결] {args.host}:{args.port} unit={args.unit}")

    def show(name, fn, bits):
        rr = _client_call(fn, args.addr, count=args.count, unit=args.unit)
        if rr.isError():
            print(f"  {name:<18} 읽기 오류: {rr}")
            return
        vals = rr.bits[:args.count] if bits else rr.registers
        print(f"  {name:<18} [{args.addr}~{args.addr + args.count - 1}] {vals}")

    try:
        show("Coils", c.read_coils, True)
        show("Discrete Inputs", c.read_discrete_inputs, True)
        show("Holding Registers", c.read_holding_registers, False)
        show("Input Registers", c.read_input_registers, False)
        if args.write is not None:
            rr = _client_call(c.write_register, args.addr, args.write, unit=args.unit)
            print(f"  쓰기 HR[{args.addr}] = {args.write} → {'오류 ' + str(rr) if rr.isError() else 'OK'}")
            show("Holding Registers", c.read_holding_registers, False)
    finally:
        c.close()


if __name__ == "__main__":
    main()
