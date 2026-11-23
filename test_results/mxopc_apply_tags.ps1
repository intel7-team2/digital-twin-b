# MX OPC 실행 프로젝트(QSIM 장치)에 Project B 태그 추가 — 관리자 권한 PowerShell에서 실행
#   서비스 정지 → mxopc_db.py add-io --set all --device QSIM (자동 백업: test_results\mdb_backup) → 서비스 시작
param([string]$Device = "QSIM", [string]$Log = "$PSScriptRoot\mxopc_apply_tags.log")
$env:PYTHONIOENCODING = "utf-8"
$root = Split-Path $PSScriptRoot -Parent
& {
  "== $(Get-Date -Format s) device=$Device"
  Stop-Service -Name 'MXOPC and MXOPC' -Force
  Start-Sleep 2
  (Get-Service 'MXOPC and MXOPC').Status
  python "$root\computer_use\mxopc_db.py" add-io --set all --device $Device
  Start-Service -Name 'MXOPC and MXOPC'
  (Get-Service 'MXOPC and MXOPC').Status
} *>&1 | Out-File -FilePath $Log -Encoding utf8
