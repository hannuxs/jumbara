# MariaDB 10.11 PENGEMBANGAN di laptop (paket ZIP tanpa installer, port 3307).
#
# Nyalakan (jika belum menyala), jendela MariaDB dibuka terpisah dan boleh diperkecil:
#   powershell -ExecutionPolicy Bypass -File scripts\windows\mariadb-dev.ps1
# Jadikan Windows Service agar menyala otomatis setiap laptop hidup (SEKALI, "Run as Administrator"):
#   powershell -ExecutionPolicy Bypass -File scripts\windows\mariadb-dev.ps1 -PasangService
# Cek status saja:
#   powershell -ExecutionPolicy Bypass -File scripts\windows\mariadb-dev.ps1 -Status
#
# Folder MariaDB bisa diubah dengan -Folder (bawaan: %USERPROFILE%\sigap-mariadb).
param(
    [string]$Folder = (Join-Path $env:USERPROFILE "sigap-mariadb"),
    [int]$Port = 3307,
    [switch]$PasangService,
    [switch]$Status
)
$ErrorActionPreference = "Stop"
$namaService = "MariaDB1011dev"

$bin = Get-ChildItem -Path $Folder -Directory -Filter "mariadb-*" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $bin) { throw "MariaDB tidak ditemukan di $Folder. Lihat docs\21-DEPLOY-WINDOWS.md bagian 13." }
$mariadbd = Join-Path $bin.FullName "bin\mariadbd.exe"
$ini = Join-Path $Folder "data\my.ini"
if (-not (Test-Path $ini)) { throw "File konfigurasi tidak ada: $ini" }

function Test-Menyala {
    return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

if ($Status) {
    if (Test-Menyala) { Write-Host "MariaDB menyala di port $Port." } else { Write-Host "MariaDB MATI (port $Port tidak dipakai)." }
    $svc = Get-Service -Name $namaService -ErrorAction SilentlyContinue
    if ($svc) { Write-Host "Service $namaService : $($svc.Status), start $($svc.StartType)" } else { Write-Host "Belum dipasang sebagai service." }
    exit 0
}

if ($PasangService) {
    $admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $admin) { throw "Buka PowerShell dengan 'Run as Administrator' lalu jalankan lagi dengan -PasangService." }
    if (Get-Service -Name $namaService -ErrorAction SilentlyContinue) {
        Write-Host "Service $namaService sudah ada."
    } else {
        if (Test-Menyala) {
            Write-Host "MariaDB sedang menyala manual. Tutup dulu jendela MariaDB (atau restart laptop), lalu jalankan lagi."
            exit 1
        }
        & $mariadbd --install $namaService "--defaults-file=$ini"
        Set-Service -Name $namaService -StartupType Automatic
    }
    Start-Service -Name $namaService
    Start-Sleep -Seconds 3
    Get-Service -Name $namaService | Format-Table -AutoSize Name, Status, StartType
    exit 0
}

if (Test-Menyala) {
    Write-Host "MariaDB sudah menyala di port $Port. Tidak perlu apa-apa."
    exit 0
}
Write-Host "Menyalakan MariaDB di port $Port (jendela baru, jangan ditutup selama bekerja)..."
Start-Process -FilePath $mariadbd -ArgumentList "--defaults-file=`"$ini`"", "--console" -WindowStyle Minimized
for ($i = 0; $i -lt 30; $i++) {
    if (Test-Menyala) { Write-Host "Berhasil. MariaDB menyala di port $Port."; exit 0 }
    Start-Sleep -Seconds 1
}
throw "MariaDB belum menyala setelah 30 detik. Lihat log di $Folder\data\*.err"
