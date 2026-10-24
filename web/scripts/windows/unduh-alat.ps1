# Unduh alat yang tidak di-commit (berukuran besar): Tailwind CSS CLI standalone dan Caddy (HTTPS produksi).
# Jalankan dari folder web:   powershell -ExecutionPolicy Bypass -File scripts\windows\unduh-alat.ps1
# Setiap berkas diperiksa sidik SHA-512/SHA-256 dari rilis resmi sebelum dipakai.
$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$web = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$tools = Join-Path $web "tools"
New-Item -ItemType Directory -Force -Path $tools | Out-Null

# 1. Tailwind CSS CLI (pengembangan dan produksi: membangun CSS).
$tw = Join-Path $tools "tailwindcss.exe"
if (Test-Path $tw) {
    Write-Host "Sudah ada: $tw"
} else {
    Write-Host "Mengunduh tailwindcss.exe ..."
    Invoke-WebRequest -Uri "https://github.com/tailwindlabs/tailwindcss/releases/download/v3.4.17/tailwindcss-windows-x64.exe" -OutFile $tw -UseBasicParsing
    Write-Host "Tersimpan: $tw"
}

# 2. Caddy 2.8.4 (produksi: HTTPS asli Let's Encrypt otomatis, lihat jalankan.bat -Produksi).
$caddy = Join-Path $tools "caddy.exe"
$sidikCaddy = "89f8fc9ece9941a15a0981b3c69543d3b9b5fe095e747875a05fc1775d4d78d4505a7fe54a58d496dade601e85f6053a00a1b0382a781d3e8b6eec044384f6e6"
if (Test-Path $caddy) {
    Write-Host "Sudah ada: $caddy"
} else {
    $zip = Join-Path $env:TEMP "caddy_2.8.4_windows_amd64.zip"
    Write-Host "Mengunduh Caddy 2.8.4 ..."
    Invoke-WebRequest -Uri "https://github.com/caddyserver/caddy/releases/download/v2.8.4/caddy_2.8.4_windows_amd64.zip" -OutFile $zip -UseBasicParsing
    $sidik = (Get-FileHash -Path $zip -Algorithm SHA512).Hash.ToLower()
    if ($sidik -ne $sidikCaddy) {
        Remove-Item $zip -Force
        throw "Sidik SHA-512 Caddy tidak cocok (unduhan rusak atau dipalsukan). Coba lagi."
    }
    $sementara = Join-Path $env:TEMP ("caddy-" + [guid]::NewGuid().ToString("N"))
    Expand-Archive -Path $zip -DestinationPath $sementara -Force
    Copy-Item (Join-Path $sementara "caddy.exe") $caddy
    Remove-Item $sementara -Recurse -Force
    Remove-Item $zip -Force
    Write-Host "Tersimpan: $caddy (sidik SHA-512 cocok)"
}
Write-Host "Selesai."
