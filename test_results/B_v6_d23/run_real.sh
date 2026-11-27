# 실제 PLC 경로 한 회차(11-27, 저장소 밖 fio_shots/one5.sh · one6.sh를 옮겨 정리)
# 순서: serve를 새 DB로 하나만 → 시험 전 점검(real_preflight.py, NG면 멈춤) → PLC 초기화(opc_reset.py) → 씬 새로 열기 → 중계 + 회차
#
# 사용(Git Bash): bash run_real.sh <이름> [비상정지 계획] [팩 계획]
#   예) bash run_real.sh v9a "X1500@Y1914=1|X1500@X1600=1|X1500@X1608=1|X1502@Y1664=1" 1,1L,1,H,1,1
#   환경 변수: OUT(기록 폴더, 기본 D:/seojung/fio_shots) · LIMIT(초, 기본 1000) · SCENE(기본 V7_plc_2.factoryio)
#             HOLD=1(팩이 다 나와도 LIMIT까지 중계 유지 — 시연용) · KEEPUNTIL=Y1929(그 비트가 켜질 때까지 계속)
#             PRESS="M1963@D1902=1:5"(HMI 비트 셋 버튼 흉내) · WATCHX="D1740,X1730"(더 기록할 번지) · SHOTS=1(화면 · 신호 기록)
#             SKIPCHECK=1(점검 건너뜀, 권하지 않음)
set -u
N=${1:?이름}; ESTOP=${2:-}; PLAN=${3:-1,2L,3,H,1L,2}
OUT=${OUT:-D:/seojung/fio_shots}; LIMIT=${LIMIT:-1000}; SCENE=${SCENE:-V7_plc_2.factoryio}
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$HERE/../.." && pwd)
export PYTHONIOENCODING=utf-8
mkdir -p "$OUT"; rm -f "$OUT/$N.log"

# 1. serve: 남은 것을 모두 끄고 새 DB로 하나만(11-26 · 11-27: 두 개가 같은 요청에 둘 다 답하거나, 없어서 검사기에서 멈춘 일)
powershell -NoProfile -Command "Get-CimInstance Win32_Process | ?{ \$_.CommandLine -match 'measurement_engine\.py\s+serve' -and \$_.ProcessId -ne \$PID } | %{ Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }"
DB="$OUT/serve_$N.db"; rm -f "$DB" "$DB-wal" "$DB-shm"
(cd "$ROOT" && py -3.12 measurement_engine.py handoff --db "$DB" --start 101 --count 6 | tail -1)
(cd "$ROOT" && nohup py -3.12 -u measurement_engine.py serve --opc-device CSIM --opc-source cache --db "$DB" > "$OUT/serve_$N.log" 2>&1 &)
sleep 4

# 2. 점검
if [ -z "${SKIPCHECK:-}" ]; then
  py -3.12 "$HERE/real_preflight.py" --scene "$SCENE" --serve 1 | tee "$OUT/${N}_check.txt" || { echo "점검 NG — 회차를 시작하지 않음 ($OUT/${N}_check.txt)"; exit 1; }
fi

# 3. 초기화(기본 목록 opc_reset_names.txt, 정지 중 초기화 M1964 · LOCK 해제 M1961) → 4. 씬 새로 열기
(cd "$HERE" && timeout 100 py -3.12 opc_reset.py)
(cd "$ROOT/test_results/a28_1123" && bash open_scene.sh "$SCENE")

# 5. 중계 + 회차
if [ -n "${SHOTS:-}" ]; then
  (cd "$HERE" && timeout $((LIMIT + 100)) py -3.12 opc_shots.py img "$OUT/$N" "$LIMIT" 3 >/dev/null 2>&1 &)
  (cd "$HERE" && timeout $((LIMIT + 100)) py -3.12 opc_shots.py sig "$OUT/${N}s" "$LIMIT" >/dev/null 2>&1 &)
fi
cd "$HERE"
timeout $((LIMIT + 150)) py -3.12 opc_outside.py "$PLAN" "$LIMIT" ${ESTOP:+--estop "$ESTOP"} ${HOLD:+--hold} --v2 --serve \
  --bridge "$ROOT/factoryio_test/$SCENE" > "$OUT/$N.log" 2>&1
tail -1 "$OUT/$N.log"
(cd "$ROOT" && py -3.12 measurement_engine.py report --db "$DB" 2>/dev/null | tail -8)
