# Daftarkan tugas Windows Task Scheduler "SIGAP jadwal" yang menjalankan
#   python manage.py sigap_jadwal
# setiap 1 menit (cadangan harian 02.00 WITA, cadangan tiap 3 jam saat acara, bersih-bersih sesi).
# WAJIB dijalankan di PowerShell "Run as Administrator", dari folder web:
#   powershell -ExecutionPolicy Bypass -File scripts\windows\daftar-task-scheduler.ps1
# Copot:  ... daftar-task-scheduler.ps1 -Hapus
param([switch]$Hapus)
$ErrorActionPreference = "Stop"
$nama = "SIGAP jadwal"

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) { throw "Buka PowerShell dengan 'Run as Administrator' lalu jalankan lagi." }

if ($Hapus) {
    Unregister-ScheduledTask -TaskName $nama -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Tugas '$nama' dihapus."
    exit 0
}

$web = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$python = Join-Path $web ".venv\Scripts\python.exe"
$manage = Join-Path $web "manage.py"
if (-not (Test-Path $python)) { throw "Virtualenv belum siap: $python tidak ada." }

$aksi = New-ScheduledTaskAction -Execute $python -Argument "`"$manage`" sigap_jadwal" -WorkingDirectory $web
$pemicu = New-ScheduledTaskTrigger -Once -At (Get-Date).Date -RepetitionInterval (New-TimeSpan -Minutes 1) -RepetitionDuration (New-TimeSpan -Days 3650)
$opsi = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 50) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
# Berjalan sebagai SYSTEM: tetap jalan walau tidak ada yang login ("Run whether user is logged on or not").
$akun = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

Register-ScheduledTask -TaskName $nama -Action $aksi -Trigger $pemicu -Settings $opsi -Principal $akun -Force | Out-Null
Write-Host "Tugas '$nama' terdaftar (setiap 1 menit)."
Start-ScheduledTask -TaskName $nama
Start-Sleep -Seconds 8
Get-ScheduledTaskInfo -TaskName $nama | Format-List LastRunTime, LastTaskResult, NextRunTime
Write-Host "LastTaskResult 0 = berhasil. Cek juga menu Superadmin > Cadangan data."
