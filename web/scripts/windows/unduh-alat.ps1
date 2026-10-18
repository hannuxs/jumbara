# Unduh alat yang tidak di-commit (berukuran besar): Tailwind CSS CLI standalone dan WinSW.
# Jalankan dari folder web:   powershell -ExecutionPolicy Bypass -File scripts\windows\unduh-alat.ps1
$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$web = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$tools = Join-Path $web "tools"
New-Item -ItemType Directory -Force -Path $tools | Out-Null

$alat = @(
    @{ Nama = "tailwindcss.exe"; Url = "https://github.com/tailwindlabs/tailwindcss/releases/download/v3.4.17/tailwindcss-windows-x64.exe" },
    @{ Nama = "WinSW-x64.exe";   Url = "https://github.com/winsw/winsw/releases/download/v2.12.0/WinSW-x64.exe" }
)

foreach ($a in $alat) {
    $tujuan = Join-Path $tools $a.Nama
    if (Test-Path $tujuan) {
        Write-Host "Sudah ada: $tujuan"
        continue
    }
    Write-Host "Mengunduh $($a.Nama) ..."
    Invoke-WebRequest -Uri $a.Url -OutFile $tujuan -UseBasicParsing
    Write-Host "Tersimpan: $tujuan"
}
Write-Host "Selesai."
