# Computer Use 테스트 결과 (Project B 환경 · 실물 PLC 없음)

- **실행일:** 2026-11-19
- **지시서:** `확인필요_및_논의사항.md` 10장 (F1~F4 · W1~W2 · C1~C4)
- **결과표:** 같은 문서 11장
- **산출물 폴더:** `test_results/` (스크린샷 JPG, GX Works2 테스트 프로젝트 `W_test.gxw`)

---

## 1. 한눈에 보기

| 항목 | 판정 | 핵심 결과 |
|---|---|---|
| F1 Factory I/O 에디션 · 드라이버 | ⚠️ 일부 | v2.5.10 **Modbus and OPC Edition**. 드라이버는 Modbus Client/Server · OPC Client DA/UA만 쓸 수 있음. **Mitsubishi 드라이버 없음** |
| F2 박스 · 비전 · 랙 · Sorter | ❌ 불가 | Factory I/O가 Computer Use의 문자 입력을 받지 않음 |
| F3 RFID 3개 · 주소 | ❌ 불가 | 같은 이유 |
| F4 RFID 시리얼 · 비트 폭 · 다중 태그 | ❌ 불가 | 같은 이유 + Modbus 쓰기 권한 거부 |
| W1 기종 · 디바이스 · 1500~19FF | ⚠️ 일부 | 원본(E:) 없음, **Q03UDV가 목록에 없어 Q03UDE로 대체**. 1500~19FF 읽기/쓰기 정상 |
| W2 카운터 래더 | ✅ 통과 | D1900=3 · D1901=1 · D1903=4 · **D1904=750**, M1920 리셋 정상 |
| C1 내장 이더넷 Modbus/TCP | ⚠️ 미지원(Q03UDE 기준) | MC 프로토콜 · MELSOFT 접속 · 소켓 통신만 있음 |
| C2 GX Simulator2 외부 연결 | ✅ 가능 | **MX OPC Server 6.10** 경유(MX Component 미설치) |
| C3 Python ↔ Factory I/O Modbus | ⚠️ 일부 | `192.168.0.213:502`로 연결 · 읽기 성공, `127.0.0.1`은 거부. 쓰기 미실행 |
| C4 구성 결론 | – | **(라) GX Simulator2 ↔ MX OPC ↔ Factory I/O + Python ↔ MX OPC** 권장, (나) 동시 구성 불가 |
| C5 (추가) 외부 프로그램 ↔ MX OPC | ✅ 통과 | 32비트 VBScript, 이어서 **32비트 Python + pywin32로 연결 · 읽기 · 쓰기 성공**. 직접 번지(D1700) 태그는 미등록 |

---

## 2. 테스트 환경

| 구분 | 내용 |
|---|---|
| Factory I/O | v2.5.10, Modbus and OPC Edition (플로팅 라이선스) |
| GX Works2 | Version 1.77F (GX Simulator2 포함) |
| MELSEC 통신 SW | MX OPC Server 6.10, MXChange 설치 · **MX Component 미설치** |
| Python | 3.10.11, `pymodbus 3.16.2`(이번에 설치) |
| 원본 PLC 프로젝트 | `E:\PLC\1\세탁기.gxw` — **E: 드라이브가 없어 열 수 없음** |
| 기존 Factory I/O 씬 | `문서\Factory IO\My Scenes\ProjectB*.factoryio` 5개 (손대지 않음) |

---

## 3. Factory I/O (F)

### F1. 에디션 · 드라이버 · 레지스터 한도 — ⚠️

- 하단 상태줄: `FACTORY I/O v2.5.10 - Modbus and OPC Edition`. (FILE · EDIT · VIEW 메뉴에 Help → About이 없음)
- **드라이버 목록**

  | 쓸 수 있음 | 비활성(에디션 밖) |
  |---|---|
  | None, Modbus TCP/IP Client, **Modbus TCP/IP Server**, **OPC Client DA/UA** | Advantech USB 4704/4750, Allen-Bradley Logix5000/Micro800/MicroLogix/SLC 5/05, Automgen Server, Control I/O, MHJ, Siemens LOGO!/S7-200·300·400/S7-1200·1500/S7-PLCSIM |

  - Mitsubishi 계열(MELSEC, MC 프로토콜) 드라이버: **없음**
  - OPC 계열: **OPC Client DA/UA 있음**
- **Modbus TCP/IP Server 설정**(`config.cfg`와 드라이버 화면)
  - 포트 502, Slave ID 1, 자동 연결 ON
  - 네트워크 어댑터 `Realtek Gaming 2.5GbE` → **`192.168.0.213:502`에서 대기** (로그: `Started at '192.168.0.213:502'`)
  - 빈 씬에서 드라이버 화면 기본 표시: Input 0~14, Coil 0~9, Holding Reg 0
- **영역별 개수 한도 · offset: 확인 불가.** CONFIGURATION 버튼을 Computer Use로 여러 번 눌렀지만 설정 패널이 열리지 않았습니다. 직접 열어서 확인해야 합니다.
- 스크린샷: `F1_에디션.jpg`, `F1_드라이버.jpg`, `F1_드라이버목록.jpg`

### F2 · F3 · F4 — ❌ 확인 불가

- Factory I/O(Unity 앱)는 Computer Use의 **마우스 드래그(부품을 씬에 놓기)는 받았지만 문자 입력은 받지 않았습니다.**
  - 팔레트 검색창에 `RFID`를 `type`과 개별 키 입력으로 넣어 봤지만 둘 다 반영되지 않음
  - CONFIGURATION 버튼도 반응 없음
- Emitter 박스 종류 선택, RFID Command/Write Data 값 입력, 드라이버 태그 배정을 할 수 없어 F2~F4는 진행하지 않았습니다.
- F4의 Write Data(22200 · 40000) 시험은 Python `--write`로도 할 수 있지만, 이 세션의 권한 설정(auto mode)에서 **Modbus 쓰기 명령이 거부**되었습니다.
- **후속:** F2~F4는 직접 수행하거나, Modbus 쓰기를 허용한 뒤 Python으로 RFID 명령 레지스터를 조작합니다.

---

## 4. GX Works2 시뮬레이션 (W)

### W1. 기종 · 디바이스 · 1500~19FF — ⚠️

1. **원본 기종 확인 불가:** `E:\PLC\1\` 경로 없음(E: 드라이브 없음).
2. **Q03UDV 선택 불가:** GX Works2 1.77F의 QCPU(Q 모드) 기종 목록은 Q03UD · Q03UDE까지만 있고 **Q03UDV가 없습니다.** 가장 가까운 **Q03UDE**로 새 래더 프로젝트를 만들어 `test_results\W_test.gxw`에 저장했습니다.
3. **디바이스 기본값(Q03UDE):**

   | X | Y | M | L | B | F | SB | V | S | T | ST | C | D | W | SW |
   |---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
   | 8K | 8K | 8K | 8K | 8K | 2K | 2K | 2K | 8K | 2K | 0K | 1K | 12K | 8K | 2K |

   - 래치(1)/(2) 범위: **설정 없음**(빈칸)
   - X/Y 8K = 0~1FFF(16진) → `X1900~X19FF` 사용 가능. M 8K(0~8191), D 12K(0~12287) → `M/D 1500~1999` 사용 가능
4. **시뮬레이션:** [디버그] → [시뮬레이션 시작/정지] → PLC 쓰기(파라미터 · MAIN) 완료 → RUN(`SM400` ON 확인).
5. **현재값 변경 → 일괄 모니터로 다시 읽기**

   | 디바이스 | 쓴 값 | 읽은 값 | 판정 |
   |---|---|---|---|
   | `D1700` | 1234 | 1234 | ✅ |
   | `D1730` | 5678 | 5678 | ✅ |
   | `D1904` | 999 | 0 | ✅ (W2 래더가 매 스캔 덮어씀 — 정상) |
   | `M1920` | ON | 1 | ✅ |
   | `X1903` | ON | ON (`X1900` 워드 = 8 → 3번 비트) | ✅ |

   → **1500~19FF 블록은 시뮬레이션에서 유효합니다.**
- 참고: PLC 파라미터를 처음 열 때 `MELSOFT 응용 프로그램 에러 <ES:03ff0004>`가 났고, 다시 열면 정상적으로 열렸습니다.
- 스크린샷: `W1_기종목록_Q03UDE까지.jpg`, `W1_기종목록2/3.jpg`, `W1_GXWorks2버전.jpg`, `W1_파라미터오류_ES03ff0004.jpg`, `W1_디바이스.jpg`, `W1_시뮬레이션_PLC쓰기.jpg`, `W1_시뮬레이션_일괄모니터.jpg`, `W1_D1700_읽기.jpg`, `W1_D1730_읽기.jpg`, `W1_M1920_읽기.jpg`, `W1_X1903_읽기.jpg`

### W2. 카운터 래더 — ✅ 통과

**입력한 래더 (49스텝)**

```
LD   X1900         INCP D1900
LD   X1901         INCP D1901
LD   X1902         INCP D1902
LD   SM400         +    D1900 D1901 D1990
LD   SM400         +    D1990 D1902 D1903        ; D1903 = 합계
LD<> D1903 K0      *    D1900 K1000 D1992        ; 32비트 결과 D1992~D1993
LD   SM400         MOV  D1903 D1994
LD   SM400         MOV  K0    D1995              ; 나눗수 32비트화
LD<> D1903 K0      D/   D1992 D1994 D1996        ; 몫 D1996
LD   SM400         MOV  D1996 D1904              ; D1904 = 양품률(‰)
LD   M1920         FMOV K0 D1900 K5              ; 리셋
LD=  D1903 K0      MOV  K0 D1996                 ; 리셋 뒤 D1904가 0으로 남도록
```

- `D1900 × 1000`은 D1900이 33을 넘으면 16비트(32767)를 넘기 때문에 32비트 곱셈 · 나눗셈으로 계산했습니다.
- 작업용 번지 `D1990~D1996`은 현재 번지 표에서 쓰지 않는 번지입니다. 실제 프로그램에 넣을 때 번지 표에 등록하세요.

**결과**

| 단계 | D1900 | D1901 | D1902 | D1903 | D1904 |
|---|---|---|---|---|---|
| 기대값 | 3 | 1 | – | 4 | 750 |
| X1900 ×3, X1901 ×1 후 | **3** | **1** | 0 | **4** | **750** |
| M1920 ON 후 | 0 | 0 | 0 | 0 | 0 |

- 스크린샷: `W2_래더_1.jpg`, `W2_래더_2.jpg`, `W2_결과.jpg`, `W2_리셋후.jpg`

---

## 5. 통신 방법 (C)

### C1. 내장 이더넷 Modbus/TCP — ⚠️ 미지원 (Q03UDE 기준)

- [PLC 파라미터] → [내장 Ethernet 포트 설정] → [오픈 설정]의 "오픈 방식" 선택지: **MC 프로토콜 · MELSOFT 접속 · 소켓 통신** 3개. **Modbus/TCP 항목 없음.**
- GX Works2 도움말에서 "Modbus" 검색: 결과 2건 모두 **QJ71MT91**(Modbus/TCP 인터페이스 모듈)을 인텔리전트 기능 모듈로 다루는 예시였고, 내장 이더넷 설명은 없었습니다.
- **결론:** 미지원(MC 프로토콜 · 소켓만). 단, Q03UDV는 이 GX Works2 버전에서 고를 수 없어 직접 확인하지 못했습니다 → 12장 P2에서 실기로 확인.
- 스크린샷: `C1_내장Ethernet.jpg`, `C1_오픈설정_프로토콜.jpg`, `C1_도움말_Modbus.jpg`

### C2. GX Simulator2 외부 연결 — ✅ 가능 (MX OPC Server 경유)

- **MX Component:** 미설치 (`C:\Program Files (x86)\MELSOFT\ACT` 없음, 시작 메뉴에 Communication Setup Utility 없음).
- **MX OPC Server 6.10:** 설치됨. MX OPC Configurator에 장치 2개:
  - `QSIM` — PC 쪽 I/F **GX Simulator**, 태그 197개
  - `ychoi` — PC 쪽 I/F GX Simulator
- **Factory I/O 기존 씬(ProjectB)** 은 드라이버 `OPC Client DA/UA` → 서버 `Mitsubishi.MXOPC.6`에 **연결된 상태**(초록 체크)였습니다. 즉 **Factory I/O ↔ MX OPC Server ↔ GX Simulator2** 경로가 이미 구성되어 있습니다.
- ⚠️ **주의:** `QSIM` 태그 번지가 **이전 3000번대**(`D3302` AC_IR, `M3142` CLAMP, `D3500` CNT_GOOD, `D3100` CRA_TARGET …)로 남아 있습니다. D9에서 번지를 1500~19FF로 옮겼으므로 OPC 태그와 Factory I/O 씬 태그 이름도 새 번지로 바꿔야 합니다.
- **결론:** 외부 연결 가능 — 경로: MX OPC Server 6.10. (MX Component 경로는 설치 필요)
- 스크린샷: `C2_기존씬_MXOPC연결.jpg`, `C2_MXOPC_QSIM_태그.jpg`

### C3. Python ↔ Factory I/O Modbus TCP Server — ⚠️ 일부

| 명령 | 결과 |
|---|---|
| `pip install pymodbus` | 3.16.2 설치 |
| `modbus_probe.py --host 127.0.0.1 --port 502` | **연결 거부** (WinError 10061) |
| `modbus_probe.py --host 192.168.0.213 --port 502 --count 16` | **연결 · 4영역 읽기 성공** (빈 씬이라 모두 0/False) |
| 0~65535 범위 읽기(Coils · DI · HR · IR) | **모든 번지 읽기 가능**, 오류 응답 없음 |
| `--write 1` | 미실행 — 이 세션 권한 설정에서 Modbus 쓰기가 거부됨 |
| RFID ① Command 레지스터 쓰기 | 미실행 — F3 씬을 만들지 못함 |

**결론**
- Python은 Factory I/O Modbus Server에 **직접 붙을 수 있습니다**(읽기 확인). 다만 서버가 랜카드 IP에 바인딩되므로 `--host 192.168.0.213`(또는 Modbus Server의 어댑터를 루프백으로 변경)을 써야 합니다. 10장 C3 명령의 `127.0.0.1`은 그대로는 동작하지 않습니다.
- Factory I/O 번지는 드라이버 화면에서 태그마다 0부터 배정되므로 프로젝트 번지(`D1700` 등)와 **자동으로 같지 않습니다.** Python이 Factory I/O에 직접 붙는 구성이라면 `measurement_engine.py`의 `STATIONS`(`result: 1700`, `req: 1710` / `1730`, `1740`)와 `ISO_BLOCK = 1650`을 Factory I/O 배정 번호로 바꾸거나, Modbus Server offset으로 맞춰야 합니다(offset 가능 여부는 F1에서 미확인).

### C4. 가능한 구성

| 구성 | 판정 | 이유 |
|---|---|---|
| (가) GX Simulator2 ↔ Factory I/O + Python ↔ GX Simulator2 | ⚠️ 절반 | Factory I/O ↔ GX Simulator2는 **MX OPC로 이미 동작**. Python ↔ GX Simulator2 직접은 **MX Component 미설치라 불가(설치 필요)** |
| (나) GX Simulator2 ↔ Factory I/O, Python ↔ Factory I/O Modbus Server | ❌ 동시 불가 | Factory I/O는 드라이버를 **하나만** 고를 수 있음. OPC Client(→PLC)와 Modbus Server(→Python)를 함께 쓸 수 없음 |
| (다) PLC 로직 없이 Factory I/O ↔ Python만 | ✅ 가능(시연 한정) | Modbus Server 읽기 확인. PLC 로직을 Python이 대신해야 함 |
| **(라) GX Simulator2 ↔ MX OPC Server ↔ Factory I/O, Python ↔ MX OPC Server** | **권장 · 검증 필요** | 이 PC에 이미 있는 경로. Python은 OPC DA 클라이언트로 MX OPC Server의 태그(`D1700` 등)를 읽고 씀 → PLC 번지 그대로 사용 가능. **Python ↔ MX OPC(OPC DA, 32비트 COM) 연결은 아직 시험하지 않음** |

실기(12장)에서는 Python ↔ PLC를 **MC 프로토콜**로 직결하는 방안을 함께 검토합니다(C1 결과상 내장 이더넷 Modbus는 기대하기 어려움).

### C5. (추가) 외부 프로그램 ↔ MX OPC Server 연결 시험 — ⚠️ 일부

C4의 (라) 구성을 검증하기 위해 추가로 진행했습니다.

**환경 확인**

| 항목 | 결과 |
|---|---|
| 64비트 Python 3.10 | pywin32 없음 → COM 사용 불가 |
| OPC DA Automation 래퍼 | `OPC.Automation`(OPC Foundation) · Graybox · Matrikon 없음. **`OPC.SiemensDAAuto`**(TIA/WinCC 설치에 포함)만 있고 **32비트 전용**(`C:\Program Files (x86)\Common Files\Siemens\opc\sopcdaauto.dll`) |
| MX OPC Server | `Mitsubishi.MXOPC.6` (LocalServer `MXOPC.exe`), TCP 대기 포트 없음 → **OPC UA 아님, OPC DA(COM)만** |
| OPC DA 프록시(IOPCServer) | 64비트 · 32비트 모두 등록됨 |

**시험 (32비트 VBScript `C:\Windows\SysWOW64\cscript.exe` + `OPC.SiemensDAAuto`)**

| 단계 | 결과 |
|---|---|
| 서버 연결 | ✅ ServerState=1(RUNNING), `MITSUBISHI MXOPCServer 6.0.10` |
| 주소 공간 탐색 | ✅ 장치 `QSIM`(태그 196개, 하위 `Device Statistics`) · `ychoi`. `Dynamic Tags` 아래는 비어 있음 |
| 정적 태그 읽기 | ✅ `QSIM.CNT_GOOD` = 3, `QSIM.CLAMP` = False, 품질 192(Good) |
| 정적 태그 쓰기 | ✅ `QSIM.CNT_GOOD` ← 4321 → 다시 읽기 4321 → **바로 3으로 복원** |
| 직접 번지 | ❌ `QSIM.D1700`, `QSIM.D1700.Short`, `QSIM.D1700:S`, `QSIM.Dynamic Tags.D1700`, `QSIM!D1700`, `QSIM.D3500`, `QSIM.SM400`, `QSIM.D1900` 모두 `0xC0040007`(없는 태그 ID) |
| PowerShell(x86) | 연결은 되지만 `Read` · 브라우저 메서드 호출이 late-binding에서 막힘 → VBScript로 전환 |

**확인된 사실 · 주의**
- **`QSIM`은 테스트용 시뮬레이터가 아니라, 오전 9:21부터 실행 중이던 다른 GX Simulator2 인스턴스에 붙어 있습니다.** (테스트 시뮬레이터에서 D3500=0인데 OPC는 3을 읽음.) GX Simulator2를 2개 띄우면 MX OPC가 어느 쪽에 붙는지 확인해야 합니다. 쓰기로 바꾼 값은 원래대로 되돌렸습니다.
- MX OPC는 **등록된 태그로만** 읽고 쓸 수 있고, 지금 등록된 것은 3000번대 태그뿐입니다. Python이 `D1700` · `D1710` · `D1650` 등을 다루려면 MX OPC Configurator에 1500~19FF 태그를 등록해야 합니다(동적 태그 표기는 찾지 못함).
- **Python에서 쓰려면** 다음 중 하나가 필요합니다.
  1. 32비트 Python + `pywin32` 설치 → `win32com.client.Dispatch("OPC.SiemensDAAuto")`로 VBScript와 같은 방식 사용 (가장 확실)
  2. 64비트 OPC DA Automation 래퍼 설치 + 64비트 Python에 `pywin32`
  3. 임시로 64비트 Python에서 32비트 `cscript` 스크립트를 호출하는 다리
- 점검 도구: `tools/mxopc_probe.vbs` (읽기 전용, CP949 저장). 실행 로그: `test_results/C5_MXOPC_probe.log`
  ```
  C:\Windows\SysWOW64\cscript.exe //nologo tools\mxopc_probe.vbs QSIM CNT_GOOD CLAMP
  ```

#### C5-2. Python ↔ MX OPC — ✅ 통과

위 1번 방법(32비트 Python + pywin32)으로 진행했습니다.

| 단계 | 결과 |
|---|---|
| 32비트 Python 설치 | `pymanager install 3.12-32` → **Python 3.12.10 (32-bit)**, python.org 서명 확인. 실행 이름 `python3.12-32` (경로 `%LOCALAPPDATA%\Python\pythoncore-3.12-32\python.exe`) |
| pywin32 설치 | `python3.12-32 -m pip install pywin32` → `import win32com.client` 정상 |
| 연결 · 태그 목록 | ✅ ServerState=1, 장치 `QSIM` · `ychoi`, `QSIM` 태그 196개 |
| 읽기 | ✅ `CNT_GOOD`=3, `CLAMP`=False, `DISP_DV`=0 (품질 192 Good) |
| 쓰기 · 복원 | ✅ `CNT_GOOD` 3 → 4321 쓰기 → 다시 읽기 4321 → 3으로 복원 |
| 직접 번지 | ❌ `QSIM.D1700` → `0xC0040007` (태그 미등록, VBScript 결과와 같음) |

- 도구: `tools/mxopc_client.py` (목록 · `--read` · `--write TAG VALUE --restore`). 64비트 Python으로 실행하면 안내 문구를 내고 멈춥니다.
  ```
  python3.12-32 tools\mxopc_client.py --read CNT_GOOD CLAMP
  python3.12-32 tools\mxopc_client.py --write CNT_GOOD 4321 --restore
  ```
- 로그: `test_results/C5_Python_MXOPC.log`
- **결론:** 구성 (라)의 **Python ↔ MX OPC Server ↔ GX Simulator2** 경로가 동작합니다. 남은 일:
  1. MX OPC Configurator에 B 번지(1500~19FF) 태그 등록. 최소: 검사기 핸드셰이크 `D1700~D1703` · `D1710~D1714` · `D1730~D1733` · `D1740~D1744`, 발열 격리 `D1650~D1653`, RFID `D1520~D1537`, 카운터 `D1900~D1904` · `M1920`
  2. `measurement_engine.py`의 통신부(지금은 64비트 + pymodbus)를 OPC 방식(32비트 Python)으로 바꿀지, Modbus를 유지할지 결정

---

## 6. 후속 조치

| # | 할 일 | 관련 |
|---|---|---|
| 1 | Factory I/O F2~F4를 직접 수행(또는 Modbus 쓰기를 허용한 뒤 Python으로 RFID 레지스터 조작) | 4-5 · 4-6 · 4-7 |
| 2 | Factory I/O Modbus Server CONFIGURATION에서 영역별 개수 한도 · offset 직접 확인 | 4-4 |
| 3 | ~~Python ↔ MX OPC Server 연결 시험~~ → C5-2에서 **32비트 Python으로 통과**. **남은 것:** MX OPC에 1500~19FF 태그 등록 · `measurement_engine.py` 통신을 OPC로 바꿀지 결정 | 4-3 · C4 · C5 |
| 4 | MX OPC `QSIM` 태그와 Factory I/O `ProjectB` 씬 태그를 **3000번대 → 1500~19FF**로 갱신 | D9 |
| 5 | Q03UDV 지원이 필요하면 GX Works2 업데이트 여부 결정(1.77F 목록에 없음). 아니면 Q03UDE로 시뮬레이션 계속 | 4-1 |
| 6 | 래더의 작업용 번지 `D1990~D1996`을 번지 표에 등록 | W2 |
| 7 | 10장 C3 명령의 `--host 127.0.0.1`을 `192.168.0.213`으로 고치거나 어댑터 설정 안내 추가 | C3 |

---

## 7. 테스트 중 바꾼 것 · 남은 상태

- **Factory I/O:** Modbus 시험을 위해 드라이버를 잠시 Modbus TCP/IP Server로 바꿨다가 **원래대로 OPC Client DA/UA로 되돌림**(연결 확인). 지금은 빈 새 씬이 열려 있어 `ProjectB`를 다시 열어야 합니다. 새 씬은 내용이 없어 `factoryio_test\`에 저장하지 않았습니다(빈 폴더만 생성).
- **GX Works2:** 테스트 프로젝트 `test_results\W_test.gxw` 저장. 시뮬레이션은 **정지**함. 원본 프로젝트는 열지 않음(E: 없음).
- **MX OPC Configurator:** 열어서 보기만 했고 설정은 바꾸지 않음.
- **설치:** `pymodbus 3.16.2`(64비트 Python 3.10). C5-2 진행 때 요청에 따라 **32비트 Python 3.12.10**(`pymanager install 3.12-32`)과 그 환경의 **pywin32** 추가 설치. 이때 Python install manager가 26.4로 자동 업데이트됨.
- **C5 쓰기 시험:** 기존 시뮬레이터(ProjectB 쪽)의 `CNT_GOOD`(D3500)에 4321을 썼다가 **3으로 되돌림**(두 번 모두 복원 확인).
- 스크린샷은 지시서의 `.png`가 아니라 `.jpg`로 저장했습니다.
