# Project B — 배터리 팩 후공정 디지털 트윈

배터리 팩(4S / 6S)의 **에이징 → 종합 특성검사 → 분류** 후공정을 Factory I/O · GX Works2(PLC) · Python으로 구현하는 프로젝트입니다.
전처리 라인 **Project C**(셀 측정 · 팩 조립)의 다음 공정이며, 두 프로젝트는 **공유 DB**로 연결됩니다.

- 전처리(Project C) 보고서: https://claude.ai/artifact/BgiEAtN6Wo8GdoXshRqRBu
- 결정 사항 · 남은 일 · 테스트 기록: [확인필요_및_논의사항.md](확인필요_및_논의사항.md)
- AI 에이전트 작업 지침: [AGENTS.md](AGENTS.md) · [CLAUDE.md](CLAUDE.md)

---

## 1. 진행 순서와 환경

| 순서 | 프로젝트 | 환경 | PLC |
|---|---|---|---|
| 1 (지금) | **Project B** (이 저장소) | 작업 PC · 테스트 PC | **실물 없음** — GX Simulator2 시뮬레이션 |
| 2 | Project C (위 보고서) | 다른 환경 | 실물 PLC 있음 |
| 3 | **B ↔ C 연결 · 실물 PLC 측정** | Project C 환경, **다른 날 따로 측정** | 실물 |

- 실물 PLC가 필요한 확인은 이 환경에서 하지 않고 [확인필요_및_논의사항.md 12장](확인필요_및_논의사항.md)(P1~P6)에 모아 둡니다.
- 시연 PC는 아직 정해지지 않았습니다. 네트워크 주소는 `192.168.0.XXX`로 표기합니다(안건 A21).

## 2. 공정 요약 (v6)

```
[Project C] 팩 조립 → 공유 DB에 packs · cells 기록
   ↓ 팩(PACK ID) 이동
STEP 01  RFID ① 등록 (PACK ID · 셀 수) · 비전으로 박스 크기 대조 (4S = Small box / 6S = Large box)
STEP 02  관통형 AS/RS 6열 × 4단 = 24칸 (4S 1~3열 · 6S 4~6열) · 크레인 A 입고 / 크레인 B 출고
         보관 중 이상 발열(가상 온도) → 크레인 B 우선 인출, 칸 LOCK(20초 뒤 자동 해제)
1차 분리 Pop-up Wheel Sorter: 발열 팩 ↓ 격리(DB ISO) / 정상 → 메인 검사
STEP 03  메인 검사기: RFID ② → OCV(ΔV) · IR · 온도 → Python 판정 → 공유 DB
STEP 04  GOOD 직진 → GOOD OUT / RETEST · NG → M1720 → 재검사 라인(정치 없이 연속 이송)
         재검사기: RFID ③ → RETEST만 재측정, 메인 NG는 계측 없이 통과
2차 분리 Pop-up Wheel Sorter: GOOD ↑ X1903 간격 확인 후 합류 / NG ↓ NG OUT
STEP 05  게이트 카운터(D1900~D1904) · HMI(Pro-face)     ← 프로젝트 범위는 여기까지 (NG 팩은 NG 라인 배출로 끝)
```

- 판정 코드: 1 PASS · 2 RETEST · 3 NG-ΔV · 4 NG-IR · 5 NG-TEMP (재검사는 1회까지)
- 레이아웃 그림: [layout/layout_v6.png](layout/layout_v6.png)
- 자세한 구조 · 판정 기준 · 디바이스 표 · DB 스키마: [확인필요_및_논의사항.md 0장](확인필요_및_논의사항.md)

## 3. 빠른 시작

**시뮬레이터 (설치 불필요)**
- `v7.html`을 브라우저로 열기 → 구축 계획서 + 2D 공정 시뮬레이터
- `3d_layout.html`을 브라우저로 열기 → 3D 레이아웃 (인터넷 필요: three.js CDN)

**Python 엔진 (PLC 없이)**
```
python measurement_engine.py handoff --count 20     # Project C 인계 모사 → 공유 DB
python measurement_engine.py demo --count 20 --db   # 계측 · 판정까지 저장
python measurement_engine.py lookup --pack 17       # 팩 RFID 조회 → 셀 이력
python measurement_engine.py report                 # 양품 · 원인별 불량 · 발열 격리
python hmi_counter_monitor.py --demo                # HMI 카운터 표시 형식
```

**PLC 연결 (MX OPC Server 경유, D17 · D21 — 64비트 Python 가능, 래퍼 · pywin32 불필요)**
```
python tools\mxopc_tags.py --check --device QSIM   # MX OPC 태그 100개 등록 확인
python measurement_engine.py serve                 # 검사기 2대 + 발열 격리 핸드셰이크
python hmi_counter_monitor.py                      # 게이트 카운터 모니터
python hmi_mc_relay.py --backend opc               # Pro-face HMI(WinGP) 중계 서버 (MC 프로토콜, 포트 5000)
```
- OPC는 기본으로 OPC DA 커스텀 인터페이스에 직접 붙습니다(`--opc-wrapper auto`). OPC Core Components(프록시)만 있으면 됩니다. 이전 방식(32비트 Python + `OPC.SiemensDAAuto` 래퍼)은 `--opc-wrapper OPC.SiemensDAAuto`.
- Simulate 장치로 시험할 때는 `--opc-source cache`(장치 직접 읽기 · 쓰기는 거부됨).
- HMI 연결 1안(D20): WinGP 화면은 미쓰비시 "Q Series QnU CPU Ethernet" 드라이버로 만들고 접속 IP를 중계 서버로 둡니다. PLC 없이 접속만 시험할 때는 `python hmi_mc_relay.py --backend memory --demo`.
- MX OPC Configurator에 1500~19FF 태그를 먼저 등록해야 합니다 → [확인필요_및_논의사항.md 4-14](확인필요_및_논의사항.md)
- Modbus TCP로 직접 붙을 때: `--link modbus --host 192.168.0.XXX`
- MC 프로토콜 3E로 PLC에 직접 붙을 때(MX OPC를 못 쓰는 PC, D21): `--link mc --host 192.168.0.XXX [--port 5000]` (`pymcprotocol` 필요, PLC 오픈 설정 필요)
- 공유 DB 경로: `--db` 옵션 > 환경변수 `PROJECT_DB` > `inspection.db`

## 4. 파일 구성

| 파일 | 역할 | 실행 방법 |
|---|---|---|
| `v7.html` | 구축 계획서 본문 + 2D 공정 시뮬레이터(v6) + 판정 테스트기(4S/6S 전환) + HMI 카운터 + 팩·셀 DB 패널(RFID 조회) | 브라우저로 열기 |
| `3d_layout.html` | 3D 공정 레이아웃 뷰어(v6). 4S(작은 박스)·6S(큰 박스)가 구역별 입고 → 1차 분리(발열 격리) → 메인 검사 → 재검사 라인(연속) → 재검사 → 2차 분리(합류/NG)로 움직입니다. "구조 확인 포인트"를 누르면 해당 위치로 카메라가 이동합니다. 셀 조회 화면은 없습니다. | 브라우저로 열기 (인터넷 필요: three.js CDN) |
| `3d_factoryio_v6.html` | **Factory I/O 부품 기준 3D 배치 뷰어(v6) 1판**. 상면도 1판 `layout/factoryio_topview_v6.svg`(M1720 = Pop-up Wheel Sorter)를 3D로 세운 것입니다. `3d_factoryio_v6_v2.html`과 조작 · 흐름 시연이 같고, M1720 분기 부품만 다릅니다. | 브라우저로 열기 (인터넷 필요: three.js CDN). `?view=top` · `?play=1` |
| `3d_factoryio_v6_v2.html` | **Factory I/O 부품 기준 3D 배치 뷰어(v6) 2판**. 상면도 2판 `layout/factoryio_topview_v6_v2.svg`(M1720 = Pusher)와 같은 좌표(1칸 = 1 m) · 라벨 · 번지로 컨베이어 · 랙 · 스태커 크레인 · Small/Large box를 세웠습니다. 탑뷰(정사영)/사선 뷰 전환과 구간 카메라, 흐름 시연(D10~D18 경로 규칙)이 있습니다. 시연의 판정은 경로를 보여 주는 순서값이며 계측 엔진 값이 아닙니다. | 브라우저로 열기 (인터넷 필요: three.js CDN). `?view=top`(탑뷰로 열기) · `?play=1`(바로 재생) |
| `measurement_engine.py` | Python 가상 계측 엔진(검사기 2대) + 공유 DB | `handoff --count 20` (C 인계 모사)<br>`demo --db` (인계 + 판정 저장, 재검사는 station 2)<br>`lookup --pack 17` / `--cell CELL-00017B` (팩 RFID 조회)<br>`isolate --pack 9 --temp 412` (발열 격리 DB 기록)<br>`report` (양품 · 원인별 불량 · 발열 격리 · 팩 종류별)<br>`stats --cells 6` (판정 비율)<br>`python3.12-32 measurement_engine.py serve` (검사기 2대 핸드셰이크 D1710 · D1740 + 발열 격리 D1650 + DB 저장. 기본 MX OPC Server 장치 `QSIM`, **32비트 Python + pywin32**. `--link modbus --host 192.168.0.XXX`로 Modbus 직접도 가능) |
| `hmi_counter_monitor.py` | STEP 05 게이트 카운터 확인 도구. PLC `D1900~D1904`와 공유 DB 집계를 함께 보여 주고, PLC 합계·수율이나 NG·격리 수가 DB와 맞지 않으면 경고합니다. | `--demo` (PLC 없이 표시 형식 확인)<br>`python3.12-32 hmi_counter_monitor.py` (OPC, 1초마다 표시)<br>`--once`, `--reset` (M1920 리셋)<br>`--link modbus --host 192.168.0.XXX` (Modbus 직접) |
| `hmi_mc_relay.py` | **HMI 중계 서버**(D20). Pro-face WinGP에는 미쓰비시 PLC처럼(MC 프로토콜 3E 바이너리, TCP · UDP 5000) 응답하고, 값은 MX OPC로 GX Simulator2와 주고받음. MX Component 불필요 | `python3.12-32 hmi_mc_relay.py --backend opc`<br>`python hmi_mc_relay.py --backend memory --demo` (PLC 없이 접속 시험) |
| `plc_link.py` | **PLC 통신 계층**(D17). 코드는 디바이스 이름(D1700 · M1920)만 쓰고, 여기서 OPC 태그(`QSIM.D1700`) 또는 Modbus 주소로 바꿈. `serve` · HMI 모니터 · `modbus_probe.py`가 사용 | 직접 실행하지 않음 |
| `tools/mxopc_tags.py` | **MX OPC 태그 목록(1500~19FF, 100개)** 생성 · 변환 · 확인. 태그 이름 = 디바이스 이름. Configurator 내보내기 CSV를 견본으로 가져오기용 CSV 생성, 기존 3000번대 태그 번지 이동, 등록 확인 | `python tools\mxopc_tags.py` (목록)<br>`--template qsim_export.csv --out qsim_import_v5.csv`<br>`--remap-old qsim_export.csv --out qsim_remap.csv`<br>`python3.12-32 tools\mxopc_tags.py --check` |
| `tools/mxopc_tags_v5.csv` | 위 목록의 기본 CSV (태그 · 디바이스 · 형식 · 설명). Configurator 가져오기 형식과 다를 수 있어 `--template` 사용을 권장 | – |
| `tools/mxopc_client.py` | MX OPC Server(OPC DA) 연결 도구(C5-2). 장치 · 태그 목록, `--read`, `--write TAG VALUE --restore`. **32비트 Python 전용** | `python3.12-32 tools\mxopc_client.py --read CNT_GOOD` |
| `tools/mxopc_probe.vbs` | 같은 확인을 설치 없이 하는 읽기 전용 VBScript(C5) | `C:\Windows\SysWOW64\cscript.exe //nologo tools\mxopc_probe.vbs QSIM CNT_GOOD` |
| `tools/modbus_probe.py` | Modbus TCP 연결 확인 도구(Computer Use 테스트 C3용). Coils · Discrete Inputs · Holding · Input Registers를 읽고, `--write`로 Holding Register 하나에 써서 다시 읽음 | `pip install pymodbus` 후 `python tools\modbus_probe.py --host 192.168.0.XXX --port 502` (주소 필수, 시연 PC 미정) |
| `hmi/` | Pro-face HMI 화면 시안(1024×768): `hmi_mockup.html`(`#s1`~`#s4`), PNG 4장. 내용 · 번지는 `확인필요_및_논의사항.md` 14장 | 브라우저로 열기 |
| `layout/` | 상면 레이아웃 그림. **`layout_v6`(현재안)만 남김** (이전 판은 Git 이력에 있음) | `.drawio`는 draw.io(app.diagrams.net)에서 수정, `.png`는 미리보기, `make_layout_v6.py`로 다시 생성 |
| `computer_use/` | **월요일(11-23) Computer Use 작업 준비**: 지시서 `README.md`, 점검 `preflight.py`, Factory I/O 씬 XML 도구 `fio_scene.py`(시험 씬 · 태그 이름 · Modbus/OPC 연결), Modbus 조작 `fio_modbus.py`(크레인 · RFID), 핸드셰이크 확인 `plc_side_check.py`, MX OPC 프로젝트 DB 도구 `mxopc_db.py`, 센서 · 액추에이터 번지 안 `fio_io_map_v6.csv`, 그림 `img/` | `python computer_use/preflight.py --opc`<br>`python computer_use/fio_scene.py tests` (시험 씬 다시 만들기)<br>`python computer_use/make_guides.py` (그림) |
| `plc/` | **v6 공정 PLC 래더 설계서(초안)** `ladder_design_v6.md`: STEP 01~05 스텝 표(시작 조건 · 출력 · 끝 조건 · 타이머 · 번지)와 GX Works2 입력용 명령어 목록. 번지 안(확정 전)과 번지 없는 내부 디바이스(자리 표시, 안건 A30)를 구분해 적음. GX Works2 입력 · 시뮬레이션 전. `ladder_alloc_v6.csv`는 내부 번지 배정 초안(A30, 확정 전), `ladder_mnemonic_v6.txt`는 그 초안으로 치환한 입력용 목록(자동 생성). `check_ladder_design.py`는 설계서의 번지가 0-4 표 · 번지 안에 있는지, 배정이 겹치지 않는지 대조 | `python plc/check_ladder_design.py`<br>`--apply plc/ladder_mnemonic_v6.txt` (치환 목록 다시 만들기) |
| `test_results/` | Computer Use 테스트 결과(스크린샷 · 로그 · `Computer_Use_테스트결과.md`) · GX Works2 테스트 프로젝트 `W_test.gxw` | – |
| `확인필요_및_논의사항.md` | 현재 구조 · 결정(D#) · 검증 결과 · 확인 필요 사항 · 논의 안건(A#) · 테스트 지시서 · 결과 기록 | – |
| `README.md` · `AGENTS.md` · `CLAUDE.md` | 저장소 안내 · AI 에이전트 공통 지침 · Claude Code 지침 | – |

- `hmi_counter_monitor.py`는 `measurement_engine.py`·`plc_link.py`의 함수를 가져다 씁니다. 그래서 **세 파일을 같은 폴더에 두고**, `python -I` 없이 실행해야 합니다.
- OPC 연결(`serve`, HMI 모니터, `mxopc_tags.py --check`)도 D21부터 64비트 Python에서 됩니다. 32비트가 필요한 것은 래퍼를 쓰는 `tools/mxopc_client.py` · `tools/mxopc_probe.vbs`뿐입니다.

## 5. 규칙

### 프로젝트 범위
- 측정은 **팩 단위**(팩 단자 2점)만 합니다. 셀별 측정 · 셀 교체 · 사람이 하는 수동 측정은 **범위 밖**이며 기능을 만들지 않습니다(D7).
- NG 팩은 **NG 라인 하나**로 배출하는 데서 끝나고, 불량 원인은 PACK ID별로 DB에만 남깁니다(D3).
- 팩 종류는 18650 3.7 V 셀 기준 **4S 2×2 = Small box**, **6S 2×3 = Large box** 두 가지입니다. 판정 기준은 셀 기준 × 셀 수입니다(D8).

### PLC 번지 · 통신
- PLC 디바이스는 **1500~19FF 블록**만 씁니다. M·D는 10진 `1500~1999`, X·Y는 16진 `1500~19FF`입니다(D9).
  - 15xx 입고·RFID / 16xx AS/RS·격리·1차 분리 / 17xx 검사·분류 / 18xx 재검사 라인 / 19xx 게이트·HMI
- 새 번지를 쓰면 **디바이스 표 3곳**을 같이 고칩니다: `확인필요_및_논의사항.md` 0-4 · `v7.html` PLC 디바이스 맵 · `tools/mxopc_tags.py` 태그 목록.
- Python ↔ PLC 통신은 **MX OPC Server(OPC DA)**를 기본으로 합니다(D17). MX OPC 태그 이름은 **디바이스 이름과 같게**(`QSIM.D1700`) 등록합니다.
- PACK ID는 1~32767(16비트) 범위입니다(D6).
- HMI는 **Pro-face(WinGP)**를 씁니다(D19). 실물 PLC · MX Component 없이 **WinGP ↔ `hmi_mc_relay.py` ↔ MX OPC ↔ GX Simulator2**로 연결합니다(D20). 화면은 실물 PLC용과 같은 드라이버 · 번지로 만들어, Project C 환경에서는 접속 IP만 바꿉니다. 랙 칸별 보관 현황 같은 추가 화면은 `확인필요_및_논의사항.md` 13장 "HMI 확장 기능"에 모아 두고, 착수가 정해지면 구현합니다.

### 코드 수정
- **계측 분포 · 판정 기준 · C 인계 모사는 세 곳에 복사되어 있습니다**(`v7.html` · `3d_layout.html` · `measurement_engine.py`). 하나를 바꾸면 세 곳을 같이 고치고, 같은 PACK ID에서 같은 값이 나오는지 확인합니다.
- 공정 흐름을 바꾸면 **2D(`v7.html`)와 3D(`3d_layout.html`)를 함께** 고치고, 레이아웃 그림(`layout/make_layout_v*.py`)도 다시 만듭니다.
- 공유 DB 스키마를 바꾸면 `SCHEMA_VERSION`을 올립니다. 이전 형식 DB는 엔진이 안내하고 멈춥니다.
- `layout/`에는 **최신판만** 둡니다. 이전 판은 Git 이력으로 봅니다.

### 문서
- 결정은 `확인필요_및_논의사항.md` **2장에 D번호**로, 논의할 것은 **5장에 A번호**로, 바뀐 내용은 **8장 변경 이력**에 적습니다.
- 문서 · 화면 문구는 한국어로 씁니다. 디바이스 번지 · 파일 이름 · 명령은 `코드` 표기로 씁니다.
- 시뮬레이션 · 스크립트로 확인한 것과 실기로 확인한 것을 구분해서 적습니다. 실기 확인 전 항목은 "미확인"으로 둡니다.

### 테스트 · 장비 (실물 PLC 없는 환경)
- GX Works2는 **시뮬레이션으로만** 동작시킵니다. 실기 "PLC 쓰기 / 읽기 / RUN"은 쓰지 않습니다.
- 원본 PLC 프로젝트(`E:\PLC\1\*.gxw`)는 저장 · 덮어쓰기하지 않습니다. 테스트 래더는 새 프로젝트로 `test_results\`에 저장합니다.
- Factory I/O 씬은 새로 만들어 `factoryio_test\`에 다른 이름으로 저장합니다.
- 확인할 수 없는 항목은 추측하지 말고 "확인 불가 + 이유"로 적습니다. 테스트 지시서와 결과 표는 `확인필요_및_논의사항.md` 10 · 11장입니다.
- 실물 PLC가 필요한 확인은 Project C 환경에서 측정일을 따로 잡아 합니다(12장). 그곳에서는 쓰기 · RUN 전에 현장 담당자 확인과 기존 프로그램 백업을 먼저 합니다.

### Git
- 기본 브랜치는 `main`입니다. 테스트 결과처럼 따로 검토할 작업은 `test/...` 브랜치로 올린 뒤 `main`에 합칩니다.
- 공유 DB 파일(`*.db`), Python 캐시, 인계 JSON은 커밋하지 않습니다(`.gitignore`).

## 6. 참고

- 전처리(Project C) 보고서: https://claude.ai/artifact/BgiEAtN6Wo8GdoXshRqRBu
- Factory I/O 센서 목록: https://docs.factoryio.com/manual/parts/sensors/ (온도 센서 없음)
- Factory I/O 공작물: https://docs.factoryio.com/manual/parts/items/ (온도 속성 없음, Small box 8 kg · Large box 15 kg)
