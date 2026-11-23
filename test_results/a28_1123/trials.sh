# 사용: SOFT=1 bash trials.sh 15 1 9 ...  — 칸마다 씬 새로 열고 s1 → s2 칸 → s3 main(CT1 → X1700)
S="D:/seojung/digital-twin-b/factoryio_test/V6_roller_9.factoryio"
for c in "$@"; do
  bash open_scene.sh V6_roller_9.factoryio >/dev/null
  r="통과"
  for s in "s1" "s2 $c" "s3 main"; do
    PYTHONIOENCODING=utf-8 timeout 200 python sec.py "$S" $s > /tmp/t.txt 2>&1
    grep -q "결과: 통과" /tmp/t.txt || { r="실패($s) $(grep 결과 /tmp/t.txt)"; break; }
  done
  echo "칸 $c: $r"
done
