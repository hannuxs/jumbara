# Perbarui aplikasi di server setelah ada perubahan kode (jalankan sebagai Administrator, dari folder web).
#   powershell -ExecutionPolicy Bypass -File scripts\windows\perbarui.ps1
# Hindari dijalankan pada jam sibuk (masa form biodata dan 12-15 November).
$ErrorActionPreference = "Stop"
$web = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $web
$py = Join-Path $web ".venv\Scripts\python.exe"

Write-Host "1/6 Membuat cadangan sebelum memperbarui..."
& $py manage.py sigap_jadwal --paksa-cadangan
if ($LASTEXITCODE -ne 0) { throw "Cadangan gagal. Pembaruan dibatalkan." }

Write-Host "2/6 Mengambil kode terbaru (git pull)..."
git pull --ff-only
if ($LASTEXITCODE -ne 0) { throw "git pull gagal." }

Write-Host "3/6 Memasang paket..."
& (Join-Path $web ".venv\Scripts\pip.exe") install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "pip install gagal." }

Write-Host "4/6 Migrasi database..."
& $py manage.py migrate --noinput
if ($LASTEXITCODE -ne 0) { throw "migrate gagal." }
& $py manage.py createcachetable

Write-Host "5/6 File statis..."
& $py manage.py collectstatic --noinput
if ($LASTEXITCODE -ne 0) { throw "collectstatic gagal." }

Write-Host "6/6 Memulai ulang service..."
Restart-Service -Name "SIGAPJumbara"
Start-Sleep -Seconds 4
& $py manage.py sigap_cek_lingkungan
