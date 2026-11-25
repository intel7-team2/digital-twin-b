# 래더로 Factory I/O 씬 돌리기 (소프트 PLC 시험 11-23 · 실제 PLC 시험 11-24)

래더 명령어 목록(`plc/ladder_mnemonic_v6.txt`)을 PC에서 그대로 실행해 Factory I/O 씬(Modbus TCP Server)을 직접 움직이는 시험 도구입니다.
GX Simulator2 ↔ MX OPC는 쓰기 1회가 약 0.2초라 입고점 0.15초 제동 같은 타이밍이 어긋나므로, **래더 논리 확인은 이 도구로** 합니다.
C 인계(투입)와 Python 검사 엔진(`serve`) 응답은 이 스크립트가 대신합니다.

## 준비 (매번)

```bash
cd /d/seojung/digital-twin-b/test_results/a28_1123
python build_v6_plc.py ../../factoryio_test/V6_plc_19_base.factoryio && python add_factory_look.py ../../factoryio_test/V6_plc_19_base.factoryio ../../factoryio_test/V6_plc_19.factoryio     # 씬을 바꿨을 때만 (최종 씬: V6_plc_19, 11-25)
bash open_scene.sh V6_plc_19.factoryio                               # Factory I/O를 새로 띄워 씬 열기 (매 시험 전 새로)
```

- Factory I/O 창은 **최대화해서 맨 앞**에 두세요(자동 화면 저장은 Factory IO 창 영역만 찍습니다).
- 시험 중 같은 씬을 이어서 다시 돌리면 상태가 섞입니다. 회차마다 `open_scene.sh`로 새로 여세요.

## 실행

```bash
cd /d/seojung/digital-twin-b/test_results/B_v6_d23
PYTHONIOENCODING=utf-8 python softplc.py "D:/seojung/digital-twin-b/factoryio_test/V6_plc_19.factoryio" 1,2L,3,H,1L,2 720
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
SHOTS=D:/seojung/fio_shots/run1 SHOT_EVERY=2 PYTHONIOENCODING=utf-8 python softplc.py "D:/seojung/digital-twin-b/factoryio_test/V6_plc_19.factoryio" 1,2L,3,H,1L,2 720
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

## 실제 PLC 시험 (GX Simulator2 + MX OPC + Factory I/O, 11-24 · 논의 문서 15-10 · 15-11)

1. MX OPC 실행 프로젝트를 `test_results/MXOPC_B_v6_d24f.mdb`(태그 360, `D1506` INT 포함)로: 관리자 명령 프롬프트에서
   `reg add "HKLM\SOFTWARE\Mitsubishi\MXOPCServer\Configuration" /v FileName /t REG_SZ /d "D:\seojung\digital-twin-b\test_results\MXOPC_B_v6_d24f.mdb" /f /reg:32` 후 `net stop "MXOPC and MXOPC"` · `net start "MXOPC and MXOPC"`
2. GX Works2에서 `B_v6_d23.gxw` → [디버그] 시뮬레이션 시작. **래더를 바꿨으면**: 시뮬레이터 창 STOP → [온라인] PLC 쓰기(파라미터 + 프로그램, 모두 예) → RESET → RUN.
   다른 이름의 프로젝트로 시뮬레이션을 시작하면 시뮬레이터가 하나 더(B) 떠 MX OPC(1번 = A)와 어긋남 → 시뮬레이터 · `SimManager`를 끄고 다시 시작
3. `py -3.12 opc_reset.py ../MXOPC_B_v6_d24f.mdb` (이전 회차 M · D를 0으로, 크레인 변환표 상수는 남김)
4. Factory I/O에 **Modbus 씬** `factoryio_test/V6_plc_19.factoryio`를 엶(`a28_1123/open_scene.sh V6_plc_19.factoryio`)
5. `py -3.12 opc_outside.py 1,2L,3,H,1L,2 1200 --bridge "D:/seojung/digital-twin-b/factoryio_test/V6_plc_19.factoryio" > 로그` — Factory I/O(Modbus) ↔ PLC(OPC) 중계 + C 인계 · 검사 응답 · 발열 접수 대행. 운전 비트 `M1950`을 직접 SET
6. 기록: `py -3.12 opc_shots.py img <폴더> <초> [간격]`(화면) · `py -3.12 opc_shots.py sig <폴더> <초>`(크레인 · 출고 신호 `signals.csv`)

- **지연(측정)**: MX OPC 쓰기 한 번 약 0.6 s, 왕복 0.8 ~ 1.3 s. OPC Client 씬(`V6_plc_17_opc`) 직결은 수 초라 위치 맞춤이 안 돼 중계 방식만 씀.
- 11-24 결과: 투입 ~ 크레인 A · B 6팩 정상. **CT1 다음 메인 라인 1에서 팔레트가 돌아 메인 판독 실패(미해결, 소프트 PLC는 정상)**.
- **11-25 결과: `V6_plc_18` + 래더 386회로로 실제 PLC 경로 6팩 2회 모두 GOOD 4 · NG 1 · 격리 1, 알람 0**(논의 문서 15-12). `opc_outside.py`는 여러 값을 한 번에 씀.
- 시험 중에는 `bash watch_run.sh <로그> 45`: 끝 · 알람 · 라이선스 오류 · 정체(로그가 45초 안 늘어남)면 바로 돌아옴. Factory I/O가 `(Unlicensed)`가 되면 라이선스 서버 응답 초과이니 다시 실행.
- 느린 재생 시험: `py make_timescale.py 2`(타이머 2배 사본 → `x2/` CSV) + Factory I/O 콘솔(`\`) `scene.time_scale = 0.5` + 툴바 Time Scale. 사본은 시험용이라 커밋하지 않음.
- 중지할 때는 `opc_outside.py` · `opc_shots.py` 프로세스가 남지 않게 확인(두 개가 같이 돌면 C 인계가 섞임).

## 11-24 시험 도구

| 파일 | 뜻 |
|---|---|
| `opc_outside.py` · `opc_reset.py` · `opc_shots.py` | 실제 PLC 시험(위). 중계는 입력 쓰기 · 출력 읽기 스레드 분리, 바뀐 출력만 씀 |
| `make_timescale.py` | 느린 재생용 타이머 N배 사본(명령어 목록 · GX CSV) |
| `softplc.py` `OUT_DELAY` · `OUT_ONLY` | 출력을 N초 늦게 써서 실제 PLC 경로 지연 흉내(`OUT_DELAY=1.0`이면 메인 라인 회전 재현), `OUT_ONLY=Y1662,...`는 그 출력만 늦춤 |
| `mb_watch.py` | Factory I/O 쪽 코일 · 입력 비트를 Modbus로 읽어 바뀔 때만 CSV(소프트 PLC ↔ 중계 비교) |
| `../a28_1123/move_sensor.py` | 씬의 센서 하나를 격자 위치로 옮김(시험용) |
| `../a28_1123/patch_entry_analog.py` | 입고 진입 롤러를 `Y1504` → 아날로그 `D1506`으로 씬 패치 |
| `build_reader_variant.py` | 리더 ② · ③ 위치만 바꾼 씬(`V6_plc_16_<이름>`). 리더 배치 비교는 씬마다 하나씩(같은 태그가 리더 두 개 범위에 있으면 응답 안 함) |
| `build_reader_probe.py` · `rfid_clash.py` · `rfid_seq.py` | 후보 리더를 옆에 같이 다는 비교 · 동시 명령 시험(위 이유로 실패한 방식, 기록용) |
| `softplc.py` 추가 | 타이머 현재값 비교(`AND>= T1513 K5`), `STOPAT` 여러 개(`D1750=14\|D1760=16`), 화면 저장은 PrintWindow로 Factory IO 창만(가려져도 찍힘) |

## 11-23 마지막 상태 (논의 문서 15-9)

- 최종 씬(그때) `V6_plc_16`: 4S = Medium · 6S = Large, CT2 뒤 대칭 배치(재검사 = CT2 왼쪽), 리무버 강제 ON, 높이 센서 `X1511` X=321 · Y8, RFID 리더 감지 1.0 m.
- 6팩 시험: 5회차 계획과 완전히 같음(알람 0). 6회차에서 **크레인 B가 처음 꺼낸 팩만 RFID ② · ③을 못 읽는 일**이 다시 나옴 → 내일 자동 화면 저장으로 원인 확인할 것.
