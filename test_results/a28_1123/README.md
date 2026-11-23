# A28 시험 도구 (2026-11-23, PC SmST14)

결과 · 결론은 `확인필요_및_논의사항.md` 15-6 · D22. 시험 씬(`factoryio_test/F2*`)은 `.gitignore` 대상이라 여기 도구로 다시 만듭니다(Factory I/O 기본 씬 복사본 + 수정).

| 파일 | 내용 |
|---|---|
| `build_pw.py` · `pw_test.py` · `pw_stop_test.py` | Pop-up Wheel(Sorting by Weight 복사본) 씬 생성 · 지나가며 분기 · 세운 뒤 분기 |
| `build_ct.py` · `ct_test.py` · `build_ct2.py` · `ct2_test.py` | Chain Transfer 시험(참고, 채택 안 함) |
| `build_crane_stop.py` · `build_crane_rs.py` · `atload_check.py` | 크레인 입고점 정지 장치 시험(아날로그 로딩 · Roller Stop · 센서 세밀 위치) |
| `crane_step.py` | 크레인 한 동작씩(단계별 확인용) |
| `crane_cycle.py` | 크레인 연속 사이클(투입 → 집기 → 넣기 → 꺼내기 → 내려놓기 → 배출) |
| `build_two_cranes.py` · `build_two_cranes2.py` · `two.py` | A36 관통형 시험: 1차(B 180° 회전, 실패) · 2차(B를 A와 같은 방향, 펜스 · 출구 컨베이어 이동, 성공) · 두 크레인 한 동작씩 |
| `open_scene.sh` | Factory I/O를 씬으로 열고 Modbus 응답까지 대기 |
| `pyModbusTCP/` | 시험용 최소 Modbus 클라이언트(이 PC에 pyModbusTCP 미설치라 대신 씀). 스크립트와 같은 폴더에서 실행 |

크레인 사이클 씬(F2q)은 F2g(오전 세션) → F2n/F2p(이 폴더 도구) → Emitter 코일화 순서로 만들었습니다. 경로가 스크립트 안에 고정돼 있으니 다른 PC에서는 경로를 고쳐 씁니다.
