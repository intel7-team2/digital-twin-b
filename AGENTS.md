# AGENTS.md — AI 에이전트 공통 작업 지침

이 저장소에서 일하는 AI 에이전트(Claude Code, Codex, Computer Use 등)가 따르는 지침입니다.
프로젝트 소개 · 실행 방법 · 사람용 규칙은 [README.md](README.md), 결정 · 남은 일 · 테스트 기록은 [확인필요_및_논의사항.md](확인필요_및_논의사항.md)에 있습니다.

## 1. 먼저 읽을 것

1. `README.md` — 프로젝트 범위, 환경, 파일 구성, 규칙
2. `computer_use/README.md` — Computer Use(화면 조작) 작업 지시서 · 준비 도구 · 알려진 함정 (Factory I/O · GX Works2 · MX OPC · WinGP 화면 작업 전에)
3. `확인필요_및_논의사항.md`
   - 0장: 현재 구조(v6) · 판정 기준 · 디바이스 표 · DB 스키마 — **현재 상태의 기준**
   - 2장: 확정된 결정 D1~D18 — 결정을 거스르는 변경은 사용자에게 먼저 묻습니다
   - 4장 · 5장: 확인 필요 사항 · 논의 안건(열림 / 보류 / 닫힘)
   - 10~12장: 테스트 지시서 · 결과 기록 · Project C 환경 측정 항목
   - 16장: 래더 · Factory I/O · HMI 분산 작업 방식 · **번지 규칙(초안에 있는 번지만, 새 번지 금지, A24 비움)** · 2단계 합치기 순서(1단계 래더 + Factory I/O → 2단계 HMI) — Computer Use로 PLC · Factory I/O · HMI 작업을 할 때 먼저 읽음

## 2. 바꾸면 안 되는 것 (사용자 결정)

- **범위:** 팩 단위 측정만. 셀별 측정 · 셀 교체 · 사람이 하는 수동 측정 기능은 만들지 않습니다(D7). NG 팩은 NG 라인 배출로 끝납니다.
- **NG 1라인:** 불량은 원인과 관계없이 한 라인(2차 분리 ↓ `M1732`)으로 배출하고, 원인은 DB `ng_cause`로만 구분합니다(D3, D16).
- **팩 종류:** 4S 2×2 = Factory I/O Small box, 6S 2×3 = Large box, 18650 3.7 V. 판정 기준 = 셀 기준 × 셀 수(D8).
- **번지:** 1500~19FF 블록만(M·D 10진, X·Y 16진)(D9). PACK ID 1~32767(D6).
- **구조 v6:** 랙 1개(6열 × 4단, 4S 1~3열 · 6S 4~6열) · 크레인 A/B · 1차 분리(발열 격리) · 메인 검사기 · `M1720` → 정치 버퍼 없는 연속 재검사 라인 → 재검사기 · 2차 분리. `M1710` 라인 없음(D10~D18).
- **통신:** Python ↔ PLC는 MX OPC Server(OPC DA) 기본, 태그 이름 = 디바이스 이름(D17). OPC는 래퍼 없이 직접 연결(64/32비트, D21). Modbus(`--link modbus`)와 MC 프로토콜(`--link mc`, D21)은 선택지로만 둡니다.
- **HMI:** Pro-face(WinGP)(D19). 연결은 1안 WinGP ↔ `hmi_mc_relay.py`(MC 프로토콜 3E) ↔ MX OPC ↔ GX Simulator2(D20). MX Component(유료)를 전제로 한 구성을 기본으로 바꾸지 않습니다. HMI 화면은 **WinGP(GP-Pro EX 4.08)로 그릴 수 있는 것만** 넣습니다 — 화면을 고칠 때마다 `확인필요_및_논의사항.md` 14-3 순서로 확인하고 결과를 남깁니다. `확인필요_및_논의사항.md` 13장 "HMI 확장 기능"(E1 랙 칸별 보관 현황 등)은 **기록만 해 둔 것**이며, 사용자가 착수를 정하기 전에는 구현하지 않습니다. 13장의 번지도 제안일 뿐이라 디바이스 표 · 태그 목록에 넣지 않습니다.
- **보류 안건**(A1 · A2 · A5 · A9 · A12 · A16, 계측·판정)은 사용자가 다시 안내받아 정하기로 했습니다. 임의로 결정해 반영하지 않습니다.
- **환경:** 이 환경에는 실물 PLC가 없습니다. 실물 PLC · B ↔ C 연결 확인은 Project C 환경에서 다른 날 합니다(12장). 이 환경의 테스트 계획에 실물 PLC 작업을 넣지 않습니다.

## 3. 수정할 때 같이 고칠 곳

| 바꾸는 것 | 같이 고칠 곳 |
|---|---|
| 계측 분포 · 판정 기준 · C 인계 모사 | `v7.html`(MEAS · makeHandoff) · `3d_layout.html`(MEAS) · `measurement_engine.py`(measure · judge · c_handoff) — 같은 PACK ID에서 같은 값이 나와야 함 |
| 공정 흐름 · 라인 구조 | `v7.html` 2D 시뮬레이터(SVG + JS) · `3d_layout.html` · `3d_factoryio_v6.html` · `3d_factoryio_v6_v2.html`(Factory I/O 부품 3D 1판 · 2판, 좌표는 `layout/make_factoryio_topview.py`와 같게) · `layout/make_layout_v*.py`(새 판 생성, 이전 판 삭제) · `measurement_engine.py` 안내 문구 · `v7.html` 계획서 본문 |
| PLC 디바이스 번지 | `확인필요_및_논의사항.md` 0-4 · `v7.html` PLC 디바이스 맵 · `tools/mxopc_tags.py` TAGS(→ `--csv`로 `tools/mxopc_tags_v5.csv` 다시 생성) · Python 상수(`STATIONS` · `ISO_BLOCK` · `COUNTER_BASE` · `RESET_COIL`) |
| 공유 DB 스키마 | `measurement_engine.py` `SCHEMA_VERSION` 올림 · `확인필요_및_논의사항.md` 0-5 · `v7.html` DB 패널(필요 시) |
| PLC 통신 | `plc_link.py` 한 곳. `serve` · HMI 모니터 · `modbus_probe.py` · `hmi_mc_relay.py`(OPC 백엔드)는 이 모듈을 씀 |
| HMI 화면이 쓰는 번지 | MX OPC 태그 목록(`tools/mxopc_tags.py`)에 있어야 중계 서버가 읽고 씀. 없는 번지는 C05C 오류 응답 |
| HMI 화면 구성(배치 · 부품 · 표시 방식) | **먼저 `확인필요_및_논의사항.md` 14-3 기준으로 WinGP 가능 여부 확인** → `hmi/hmi_mockup.html` · `hmi/screen_0#` · `hmi/bg/` · `hmi/guide/` PNG · `hmi/hmi_parts_v2.csv` · 14장 표 · 8장 이력. 불가 · 미확인은 안건(A#)으로 |
| Factory I/O 센서 · 액추에이터 번지(4-16) | `computer_use/fio_io_map_v6.csv` → `python computer_use/make_guides.py`(그림) · 확정하면 PLC 디바이스 번지 행처럼 0-4 · `v7.html` · `tools/mxopc_tags.py`도 |
| 결정 · 안건 | `확인필요_및_논의사항.md` 2장(D#) · 5장(A#) · 8장 변경 이력 · 맨 위 "진행 현황" 표 |

## 4. 검증

- **Python:** `python measurement_engine.py demo --count 20`, `report`, `python hmi_counter_monitor.py --demo`가 오류 없이 도는지. Windows 콘솔에서는 `PYTHONIOENCODING=utf-8`을 붙입니다.
- **HTML 시뮬레이터:** 브라우저 오류 0건, 정상 운전 처리량이 이전과 같은지(2D 1200초에 약 335~350팩), 메인 라인 위 정지 · 팩 근접이 없는지. 시험 방법과 기준값은 `확인필요_및_논의사항.md` 3장에 있습니다.
- **OPC:** `serve`는 MX OPC Server가 있는 PC에서만 실제 확인이 됩니다(D21부터 64비트 Python 가능). Simulate 장치는 `--opc-source cache`로 읽기만 확인되고 쓰기는 거부됩니다. 없는 환경에서는 가짜 연결(plc_link의 `read_words` · `write_words`를 흉내 내는 객체)로 핸드셰이크를 확인하고, "실기 미확인"으로 적습니다.
- 확인하지 못한 것은 확인한 것처럼 적지 않습니다. 결과는 숫자와 함께 문서에 남깁니다.

## 5. 문서 작성

- 한국어로 씁니다. 디바이스 번지 · 파일 이름 · 명령은 `코드` 표기.
- 새 결정은 D번호, 새 안건은 A번호를 이어서 붙입니다(번호 재사용 금지). 닫힌 안건은 "닫힘" 표로 옮기고 결론을 적습니다.
- 바뀐 내용은 8장 변경 이력에 한 줄로 남깁니다.
- 시연 PC 주소처럼 아직 정해지지 않은 값은 `192.168.0.XXX`처럼 자리만 표시하고 안건으로 남깁니다.

## 6. 장비 · 파일 안전 규칙

- GX Works2는 시뮬레이션으로만. 실기 "PLC 쓰기 / 읽기 / RUN" 금지.
- `E:\PLC\1\*.gxw` 등 원본 PLC 프로젝트는 보기만 하고 저장 · 덮어쓰기 금지. 테스트 래더는 새 프로젝트로 `test_results\`에.
- Factory I/O 씬은 새 이름으로 `factoryio_test\`에 저장.
- 사용자가 허락하지 않은 프로그램 설치는 하지 않고 "설치 필요"로 적습니다.
- MX OPC 쓰기 시험은 원래 값을 읽어 두고 끝나면 복원합니다(`mxopc_client.py --write ... --restore`).

## 7. Git

- 기본 브랜치 `main`. 커밋 · push는 사용자가 요청할 때만 합니다.
- PC를 나눠 래더 · Factory I/O · HMI를 작업할 때(`확인필요_및_논의사항.md` 16장)는 `main`에 직접 push하지 않고 PC별 작업 브랜치에 올린 뒤 PR을 만듭니다. 브랜치를 모르면 push 전에 사용자에게 묻습니다.
- `*.db` · `__pycache__/` · 인계 JSON은 커밋하지 않습니다(`.gitignore`).
- 다른 브랜치(예: `test/computer-use-results`)의 변경을 가져올 때는 로컬 수정이 없는지 먼저 확인합니다.
