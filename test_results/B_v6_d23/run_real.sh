# 실제 PLC 경로 한 회차(11-27, 저장소 밖 fio_shots/one5.sh · one6.sh를 옮겨 정리)
# 순서: serve를 새 DB로 하나만 → 시험 전 점검(real_preflight.py, NG면 멈춤) → PLC 초기화(opc_reset.py) → 씬 새로 열기 → 중계 + 회차
#
# 사용(Git Bash): bash run_real.sh <이름> [비상정지 계획] [팩 계획]
#   예) bash run_real.sh v9a "X1500@Y1914=1|X1500@X1600=1|X1500@X1608=1|X1502@Y1664=1" 1,1L,1,H,1,1
#   환경 변수: MODE=random(시연: 계측 · 보관 발열 매번 다르게, 기본 id = 재현) · OUT(기록 폴더, 기본 D:/seojung/fio_shots) · LIMIT(초, 기본 1000) · SCENE(기본 V7_plc_2.factoryio)
#             HOLD=1(팩이 다 나와도 LIMIT까지 중계 유지 — 시연용) · KEEPUNTIL=Y1929(그 비트가 켜질 때까지 계속)
#             PRESS="M1963@D1902=1:5"(HMI 비트 셋 버튼 흉내) · WATCHX="D1740,X1730"(더 기록할 번지) · SHOTS=1(화면 · 신호 기록)
#             BATCHES="12,6"(연속 운전: 회차를 나눠 정지 없이 투입) · SKIPCHECK=1(점검 건너뜀, 권하지 않음)
set -u
N=${1:?이름}; ESTOP=${2:-}; PLAN=${3:-1,2L,3,H,1L,2}
OUT=${OUT:-D:/seojung/fio_shots}; LIMIT=${LIMIT:-1000}; SCENE=${SCENE:-V7_plc_2.factoryio}
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$HERE/../.." && pwd)
export PYTHONIOENCODING=utf-8
mkdir -p "$OUT"; rm -f "$OUT/$N.log"

# 1. 남은 프로그램 정리: serve · 중계 · 기록을 모두 끔(11-26 · 11-27 serve 2개가 둘 다 답함, 11-28 재점검: Ctrl+C 뒤 남은 중계가 다음 회차와 겹칠 수 있음)
powershell -NoProfile -Command "Get-CimInstance Win32_Process | ?{ \$_.Name -match '^(py|python)\.exe$' -and \$_.CommandLine -match 'measurement_engine\.py\s+serve|opc_outside\.py|opc_shots\.py' } | %{ Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }"
DB="$OUT/serve_$N.db"; rm -f "$DB" "$DB-wal" "$DB-shm"
# 11-27 A2 · A12: 계획의 H 자리 팩 = 보관 중 이상 발열(serve --hot-packs, 시험 재현). MODE=random(시연)이고 계획에 H가 없으면 serve가 팩마다 6% 확률
MODE=${MODE:-id}; NP=$(echo "$PLAN" | tr ',' '\n' | grep -c .)
HOTS=$(echo "$PLAN" | tr ',' '\n' | awk '/^H/{printf "%s%d", (n++ ? "," : ""), 100 + NR}')
if [ "$MODE" = random ] && [ -z "$HOTS" ]; then HOTARG=(); else HOTARG=(--hot-packs "${HOTS:--}"); fi
# 11-28 연속 운전: BATCHES="12,6"이면 첫 묶음만 먼저 C 인계, 다음 묶음은 앞 회차가 끝나면 중계 프로그램이 인계(정지 없이 이어 투입)
export HANDOFF_DB="$DB"   # 11-28: 중계가 C 인계 셀 수를 DB에서 읽음(BATCHES면 다음 묶음 인계도)
[ -n "${BATCHES:-}" ] && NP1=${BATCHES%%,*} || NP1=$NP
(cd "$ROOT" && py -3.12 measurement_engine.py handoff --db "$DB" --start 101 --count "$NP1" | tail -1)

# 2. 점검(serve는 아직 안 띄움 — 아래 5에서)
if [ -z "${SKIPCHECK:-}" ]; then
  # 11-28: tee로 넘기면 점검의 끝 코드가 사라져 NG여도 진행됐음(v9e, GX가 꺼진 채 시작) → PIPESTATUS로 점검의 끝 코드를 봄
  py -3.12 "$HERE/real_preflight.py" --scene "$SCENE" --serve 0 | tee "$OUT/${N}_check.txt"
  [ "${PIPESTATUS[0]}" -eq 0 ] || { echo "점검 NG — 회차를 시작하지 않음 ($OUT/${N}_check.txt)"; exit 1; }
fi

# 3. 초기화(기본 목록 opc_reset_names.txt, 정지 중 초기화 M1964 · LOCK 해제 M1961) → 4. 씬 새로 열기
(cd "$HERE" && timeout 100 py -3.12 opc_reset.py) || { echo "PLC 초기화 실패 — 회차를 시작하지 않음"; exit 1; }
(cd "$ROOT/test_results/a28_1123" && bash open_scene.sh "$SCENE")

# 5. serve — 11-28 재점검: 초기화 뒤에 띄움(전에는 초기화 전에 떠서 지난 회차 랙 값 · 남은 요청을 이번 회차로 처리할 수 있었음)
(cd "$ROOT" && nohup py -3.12 -u measurement_engine.py serve --opc-device CSIM --opc-source cache --mode "$MODE" "${HOTARG[@]}" --db "$DB" > "$OUT/serve_$N.log" 2>&1 &)
echo "serve: 난수 $MODE · 발열 지정 ${HOTS:-$([ ${#HOTARG[@]} -eq 0 ] && echo '없음(6% 확률)' || echo '없음')}"
sleep 4
NS=$(powershell -NoProfile -Command "@(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | ?{ \$_.CommandLine -match 'measurement_engine\.py\s+serve' }).Count" | tr -d '\r')
[ "$NS" = 1 ] || { echo "serve가 $NS 개 — 회차를 시작하지 않음($OUT/serve_$N.log 확인)"; exit 1; }

# 6. 중계 + 회차
if [ -n "${SHOTS:-}" ]; then
  (cd "$HERE" && timeout $((LIMIT + 100)) py -3.12 opc_shots.py img "$OUT/$N" "$LIMIT" 3 >/dev/null 2>&1 &)
  (cd "$HERE" && timeout $((LIMIT + 100)) py -3.12 opc_shots.py sig "$OUT/${N}s" "$LIMIT" >/dev/null 2>&1 &)
fi
cd "$HERE"
timeout $((LIMIT + 150)) py -3.12 opc_outside.py "$PLAN" "$LIMIT" ${ESTOP:+--estop "$ESTOP"} ${HOLD:+--hold} --v2 --serve   --bridge "$ROOT/factoryio_test/$SCENE" > "$OUT/$N.log" 2>&1
tail -1 "$OUT/$N.log"
REP=$(cd "$ROOT" && py -3.12 measurement_engine.py report --db "$DB" 2>/dev/null)
echo "$REP" | tail -8
# 11-28 재점검: HOLD · KEEPUNTIL 없이 끝나면 마지막 팔레트가 6분 대기 중이라 회차가 안 닫힐 수 있음 → 알림
echo "$REP" | grep -q "회차 " || echo "참고: 회차 기록(batches) 없음 — 마지막 팔레트가 나가기 전에 중계가 끝났으면 정상(회차 끝까지 보려면 HOLD=1 또는 KEEPUNTIL=Y1929)"
