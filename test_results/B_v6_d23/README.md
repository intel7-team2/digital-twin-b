# 래더로 Factory I/O 씬 돌리기 (소프트 PLC 시험) — 11-23

래더 명령어 목록(`plc/ladder_mnemonic_v6.txt`)을 PC에서 그대로 실행해 Factory I/O 씬(Modbus TCP Server)을 직접 움직이는 시험 도구입니다.
GX Simulator2 ↔ MX OPC는 쓰기 1회가 약 0.2초라 입고점 0.15초 제동 같은 타이밍이 어긋나므로, **래더 논리 확인은 이 도구로** 합니다.
C 인계(투입)와 Python 검사 엔진(`serve`) 응답은 이 스크립트가 대신합니다.

## 준비 (매번)

```bash
cd /d/seojung/digital-twin-b/test_results/a28_1123
python build_v6_plc.py ../../factoryio_test/V6_plc_16.factoryio     # 씬을 바꿨을 때만 (최종 씬: V6_plc_16)
bash open_scene.sh V6_plc_16.factoryio                               # Factory I/O를 새로 띄워 씬 열기 (매 시험 전 새로)
```

- Factory I/O 창은 **최대화해서 맨 앞**에 두세요(자동 화면 저장은 Factory IO 창 영역만 찍습니다).
- 시험 중 같은 씬을 이어서 다시 돌리면 상태가 섞입니다. 회차마다 `open_scene.sh`로 새로 여세요.

## 실행

```bash
cd /d/seojung/digital-twin-b/test_results/B_v6_d23
PYTHONIOENCODING=utf-8 python softplc.py "D:/seojung/digital-twin-b/factoryio_test/V6_plc_16.factoryio" 1,2L,3,H,1L,2 720
```

- 둘째 인자 = 팩 계획(쉼표로): `1` GOOD · `2` 재검사 → GOOD · `3` 메인 NG → 재검사 라인 → NG OUT · `H` 랙에 들어간 뒤 발열 접수 → 격리. 뒤에 `L`을 붙이면 6S(Large 박스), 없으면 4S(Medium 박스).
- 셋째 인자 = 제한 시간(초). 6팩이 약 5분.
- 끝 줄 `결과: GOOD n · NG n · 격리 n`이 계획과 같으면 통과. 위 6팩 계획의 정답은 **GOOD 4 · NG 1 · 격리 1**.
- 로그: `메인 검사 PACK n` · `재검사 PACK n`(읽은 PACK ID), `알람 M1951~M1957`, 감시 번지 변화.

### 환경 변수 (선택)

| 변수 | 뜻 | 예 |
|---|---|---|
| `SHOTS` | **자동 화면 저장 폴더**. `SHOT_EVERY`초마다 Factory IO 창만 JPEG로 저장 + `index.csv`(시각 · 주요 스텝 번호 · 카운터 · 알람) | `SHOTS=D:/seojung/fio_shots/run1` |
| `SHOT_EVERY` · `SHOT_W` | 저장 간격(초, 기본 2) · 가로 픽셀(기본 1600) | `SHOT_EVERY=1` |
| `STOPAT` | 이 번지가 이 값이 되는 순간 멈춤(그 장면을 화면으로 확인할 때) | `STOPAT=M1953=1` · `STOPAT=D1760=10` |
| `FORCE` | 씬에 없는 센서를 강제값으로 | `FORCE=X1511=1` |
| `TSCALE` | Factory I/O 배속과 맞출 때 타이머 배율(배속은 태그로 못 바꿔 지금은 안 씀) | `TSCALE=2` |

자동 화면 저장 예 (내일 시험용):

```bash
SHOTS=D:/seojung/fio_shots/run1 SHOT_EVERY=2 PYTHONIOENCODING=utf-8 python softplc.py "D:/seojung/digital-twin-b/factoryio_test/V6_plc_16.factoryio" 1,2L,3,H,1L,2 720
```

- 저장 폴더는 **저장소 밖**(`D:/seojung/fio_shots/…`)에 두세요(사진이 많아 커밋 대상이 아님). 6팩 약 150장 · 회차당 수십 MB.
- 끝난 뒤 `index.csv`에서 알람이 켜진 시각이나 스텝이 멈춘 시각을 찾고, 그 전후 몇 장만 열어 봅니다.
- Factory IO 창을 못 찾으면(최소화 등) 그 회차는 건너뛰고 경고만 남깁니다(다른 창은 찍지 않음).

## 주요 감시 번지

| 번지 | 뜻 |
|---|---|
| `D1541` | STEP 01(투입 · RFID ① 등록) 스텝. 15 = 알람 대기 |
| `D1548` | 입고 로딩 컨베이어 스텝(40 = 크레인 A 입고점 정지) |
| `D1640` · `D1641` | 크레인 A · B 스텝 |
| `D1656~D1659` | CT1 · CT2 · CT3 · CT4/CT5 합류 스텝 |
| `D1549` · `D1550` · `D1551` | 코너 CT CTM · CTG · CTR 스텝 |
| `D1750` · `D1760` | 메인 검사 · 재검사 스텝(14 · 16 = RFID 다시 읽기 대기, 51 = 판독 실패) |
| `D1558` · `D1568` | RFID ② · ③ 레지스터에 마지막으로 남은 읽기 값 |

## 11-23 마지막 상태 (논의 문서 15-9)

- 최종 씬 `V6_plc_16`: 4S = Medium · 6S = Large, CT2 뒤 대칭 배치(재검사 = CT2 왼쪽), 리무버 강제 ON, 높이 센서 `X1511` X=321 · Y8, RFID 리더 감지 1.0 m.
- 6팩 시험: 5회차 계획과 완전히 같음(알람 0). 6회차에서 **크레인 B가 처음 꺼낸 팩만 RFID ② · ③을 못 읽는 일**이 다시 나옴 → 내일 자동 화면 저장으로 원인 확인할 것.
