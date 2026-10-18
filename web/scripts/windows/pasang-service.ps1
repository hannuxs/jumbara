# Pasang Waitress (Django SIGAP JUMBARA) sebagai Windows Service memakai WinSW.
# WAJIB dijalankan di PowerShell "Run as Administrator", dari folder web:
#   powershell -ExecutionPolicy Bypass -File scripts\windows\pasang-service.ps1
# Parameter opsional: -Threads 48 -Port 8000 -Hapus (untuk mencopot service)
param(
    [int]$Threads = 48,
    [int]$Port = 8000,
    [switch]$Hapus
)
$ErrorActionPreference = "Stop"

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) { throw "Buka PowerShell dengan 'Run as Administrator' lalu jalankan lagi." }

$web = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$tools = Join-Path $web "tools"
$winsw = Join-Path $tools "WinSW-x64.exe"
$exe = Join-Path $tools "sigap-jumbara-service.exe"
$xml = Join-Path $tools "sigap-jumbara-service.xml"
$waitress = Join-Path $web ".venv\Scripts\waitress-serve.exe"
$logs = Join-Path $web "logs"

if ($Hapus) {
    if (Test-Path $exe) {
        & $exe stop | Out-Null
        & $exe uninstall
    }
    Write-Host "Service dicopot."
    exit 0
}

if (-not (Test-Path $winsw)) { throw "tools\WinSW-x64.exe belum ada. Jalankan scripts\windows\unduh-alat.ps1 dulu." }
if (-not (Test-Path $waitress)) { throw "Virtualenv belum siap (.venv\Scripts\waitress-serve.exe tidak ada). Jalankan: py -3.12 -m venv .venv ; .venv\Scripts\pip install -r requirements.txt" }
if (-not (Test-Path (Join-Path $web ".env"))) { throw "File .env belum ada. Salin .env.example menjadi .env lalu isi." }
New-Item -ItemType Directory -Force -Path $logs | Out-Null

Copy-Item $winsw $exe -Force
@"
<service>
  <id>SIGAPJumbara</id>
  <name>SIGAP Jumbara</name>
  <description>SIGAP JUMBARA (Django + Waitress) di 127.0.0.1:$Port. Diteruskan oleh Apache XAMPP.</description>
  <executable>$waitress</executable>
  <arguments>--listen=127.0.0.1:$Port --threads=$Threads --channel-timeout=120 --connection-limit=1000 sigap.wsgi:application</arguments>
  <workingdirectory>$web</workingdirectory>
  <env name="PYTHONUNBUFFERED" value="1" />
  <env name="PYTHONUTF8" value="1" />
  <startmode>Automatic</startmode>
  <delayedAutoStart>true</delayedAutoStart>
  <depend>MariaDB1011</depend>
  <onfailure action="restart" delay="10 sec" />
  <onfailure action="restart" delay="30 sec" />
  <onfailure action="restart" delay="60 sec" />
  <resetfailure>1 hour</resetfailure>
  <stoptimeout>20 sec</stoptimeout>
  <logpath>$logs</logpath>
  <log mode="roll-by-size">
    <sizeThreshold>10240</sizeThreshold>
    <keepFiles>8</keepFiles>
  </log>
</service>
"@ | Set-Content -Path $xml -Encoding UTF8

# Hapus baris <depend> jika service MariaDB bernama lain (misalnya "mysql" bawaan XAMPP).
if (-not (Get-Service -Name "MariaDB1011" -ErrorAction SilentlyContinue)) {
    (Get-Content $xml) | Where-Object { $_ -notmatch "<depend>" } | Set-Content -Path $xml -Encoding UTF8
    Write-Host "Catatan: service MariaDB1011 tidak ditemukan, ketergantungan service dilewati."
}

if (Get-Service -Name "SIGAPJumbara" -ErrorAction SilentlyContinue) {
    Write-Host "Service sudah ada, memasang ulang..."
    & $exe stop | Out-Null
    & $exe uninstall | Out-Null
}
& $exe install
& $exe start
Start-Sleep -Seconds 4
Get-Service -Name "SIGAPJumbara" | Format-Table -AutoSize Name, DisplayName, Status, StartType
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/" -UseBasicParsing -TimeoutSec 15
    Write-Host "Berhasil: http://127.0.0.1:$Port/ menjawab $($r.StatusCode)."
} catch {
    Write-Warning "Service terpasang tetapi belum menjawab. Lihat log di $logs (sigap-jumbara-service.err.log dan django.log)."
}
