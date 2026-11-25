# 사용: watch.sh <로그> [멈춤 판정 초=45] — 끝남 · 알람 · 라이선스 오류 · 정체(로그가 안 늘어남) 중 하나면 바로 돌아옴
L=$1; S=${2:-45}; PL="/c/Users/user/AppData/LocalLow/Real Games/Factory IO/Player.log"
while [ $SECONDS -lt 580 ]; do
  grep -qE "결과:|Traceback|모든 팩" $L && { echo "== 끝"; break; }
  grep "알람" $L | grep -vq M1500 && { echo "== 알람"; break; }
  grep -q "Error accessing" "$PL" && { echo "== 라이선스"; break; }
  [ $(( $(date +%s) - $(stat -c %Y $L) )) -gt $S ] && { echo "== 정체 ${S}초"; break; }
  sleep 2
done
grep -E "PACK|알람|결과|배출|D190|실패|Trace" $L | tail -${3:-12}
