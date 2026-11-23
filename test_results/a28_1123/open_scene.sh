# 사용: open_scene.sh <씬 파일 이름>  — Factory I/O를 새로 띄우고 Modbus 502 응답까지 대기(최대 60 s)
taskkill //IM "Factory IO.exe" //F >/dev/null 2>&1; sleep 3
("/c/Program Files (x86)/Real Games/Factory IO/Factory IO.exe" "load:D:/seojung/digital-twin-b/factoryio_test/$1" >/dev/null 2>&1 &)
for i in $(seq 1 60); do
  python -I -c "import socket,struct,sys
s=socket.create_connection(('127.0.0.1',502),1); s.settimeout(1); s.sendall(struct.pack('>HHHBBHH',1,0,6,1,2,0,1)); sys.exit(0 if len(s.recv(20))>=9 else 1)" 2>/dev/null && { sleep 3; echo "열림 $1 (${i}s)"; exit 0; }
  sleep 1
done
echo "60 s 안에 Modbus 응답 없음: $1"; exit 1
