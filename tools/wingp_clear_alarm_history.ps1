# WinGP 알람 이력 지우기(11-28, 시연 전용)
# WinGP는 알람 이력 같은 '꺼져도 남는 값'을 nand\PRJ001\USER\SCREEN\Backup.dat(+ .bak)에 저장함.
# 이 스크립트는 WinGP를 끄고 두 파일을 보관 폴더로 옮김 → WinGP를 다시 켜면 알람 이력이 빈 상태로 시작(새 알람은 정상 기록).
# 되돌리기: 보관 폴더의 Backup.dat · Backup.bak를 원래 폴더로 다시 복사(WinGP를 끈 상태에서).
# 이 프로젝트 HMI는 Backup.dat에 알람 이력 말고 따로 남기는 값이 없음(레시피 · 백업 번지 안 씀).
#
# 사용(PowerShell): powershell -ExecutionPolicy Bypass -File tools\wingp_clear_alarm_history.ps1 [-Keep D:\seojung\fio_shots\hmi]
param([string]$Keep = "D:\seojung\fio_shots\hmi", [string]$WinGP = "C:\Pro-face\WinGP")

$dir = Join-Path $WinGP "nand\PRJ001\USER\SCREEN"
if (-not (Test-Path $dir)) { Write-Host "WinGP 프로젝트 폴더가 없음: $dir"; exit 1 }

$p = Get-Process PCRuntime -ErrorAction SilentlyContinue
if ($p) {
    Write-Host "WinGP를 끕니다(PID $($p.Id -join ', '))"
    $p | Stop-Process -Force
    Start-Sleep -Seconds 2
}

$dest = Join-Path $Keep ("wingp_alarm_" + (Get-Date -Format "MMdd_HHmmss"))
New-Item -ItemType Directory -Force -Path $dest | Out-Null
$moved = 0
foreach ($f in "Backup.dat", "Backup.bak") {
    $src = Join-Path $dir $f
    if (Test-Path $src) { Move-Item $src $dest; $moved++ }
}
Write-Host "알람 이력 파일 $moved 개를 $dest 로 옮김 → WinGP를 다시 켜면 이력이 비어 있음"
