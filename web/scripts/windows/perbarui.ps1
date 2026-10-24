# Perbarui aplikasi di server setelah ada perubahan kode (dari folder web).
#   powershell -ExecutionPolicy Bypass -File scripts\windows\perbarui.ps1
# Hindari dijalankan pada jam sibuk (masa form biodata dan 12-15 November).
# Langkah: cadangan dulu, ambil kode terbaru (bila folder ini repositori git), lalu jalankan ulang server.
$ErrorActionPreference = "Stop"
$web = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $web
$py = Join-Path $web ".venv\Scripts\python.exe"

Write-Host "1/3 Membuat cadangan sebelum memperbarui..."
& $py manage.py sigap_jadwal --paksa-cadangan
if ($LASTEXITCODE -ne 0) { throw "Cadangan gagal. Pembaruan dibatalkan." }

if (Test-Path (Join-Path $web "..\.git")) {
    Write-Host "2/3 Mengambil kode terbaru (git pull)..."
    git pull --ff-only
    if ($LASTEXITCODE -ne 0) { throw "git pull gagal." }
} else {
    Write-Host "2/3 Bukan repositori git: salin berkas baru secara manual (jangan menimpa web\.env, web\privat, cadangan)."
}

Write-Host "3/3 Tutup jendela jalankan.bat -Produksi yang sedang berjalan (Ctrl+C), lalu jalankan lagi:"
Write-Host "      jalankan.bat -Produksi"
Write-Host "    jalankan.bat memasang paket baru, migrasi database, membangun CSS, dan collectstatic otomatis."
