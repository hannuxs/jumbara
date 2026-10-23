# SIGAP JUMBARA: satu perintah untuk memeriksa kesiapan lalu menjalankan server.
#
# Cara pakai (dari folder proyek):
#   jalankan.bat                    periksa semua, perbaiki yang aman, lalu jalankan server HTTPS (port 8000)
#   jalankan.bat -CekSaja           hanya periksa, tidak menjalankan server
#   jalankan.bat -Port 8080         pakai port lain
#   jalankan.bat -Produksi          jalankan dengan Waitress (seperti di belakang Apache), hanya http://
#   jalankan.bat -Tes               jalankan juga tes otomatis (pytest) dan ruff sebelum server
#   jalankan.bat -Http              tanpa HTTPS (http://), misalnya bila ada masalah sertifikat
#
# Bawaan HTTPS di laptop memakai sertifikat buatan sendiri (python manage.py sigap_https_dev) karena kamera HP
# (pemindai, Anjangsana) hanya jalan lewat https://. Di server produksi HTTPS diurus Apache + sertifikat asli
# (docs/21-DEPLOY-WINDOWS.md); aplikasi di sana berjalan sebagai Windows Service, bukan lewat jalankan.bat.
#
# Yang diperiksa dan diperbaiki otomatis bila aman:
#   Python 3.12, virtualenv web\.venv, paket requirements, file web\.env, kunci rahasia,
#   MariaDB menyala (dinyalakan bila mati), koneksi database, migrasi, tabel cache, data awal,
#   Tailwind CLI, CSS, file statis (mode DEBUG=False), port bebas, alamat IP untuk HP.
# Hanya memakai karakter ASCII agar aman di Windows PowerShell 5.1.
param(
    [int]$Port = 8000,
    [switch]$CekSaja,
    [switch]$Produksi,
    [switch]$Tes,
    [switch]$Http,
    [switch]$Https  # tidak dipakai lagi (HTTPS sudah bawaan); dibiarkan agar perintah lama tidak galat
)
# "Continue": peringatan di stderr dari program luar (pip, tailwind) tidak boleh menghentikan skrip.
# Keberhasilan setiap langkah dinilai dari $LASTEXITCODE.
$ErrorActionPreference = "Continue"
# HTTPS bawaan, kecuali -Http atau -Produksi (Waitress tidak melayani TLS).
$pakaiHttps = -not ($Http -or $Produksi)
$env:BROWSERSLIST_IGNORE_OLD_DATA = "1"
$env:PYTHONUTF8 = "1"
$web = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $web
$py = Join-Path $web ".venv\Scripts\python.exe"
$global:jumlahMasalah = 0
$global:jumlahPeringatan = 0

function Judul($t) { Write-Host ""; Write-Host "== $t" -ForegroundColor Cyan }
function Ok($t) { Write-Host "  [OK] $t" -ForegroundColor Green }
function Info($t) { Write-Host "   i   $t" }
function Peringatan($t) { $global:jumlahPeringatan++; Write-Host "  [!]  $t" -ForegroundColor Yellow }
function Masalah($t, $solusi) {
    $global:jumlahMasalah++
    Write-Host "  [X]  $t" -ForegroundColor Red
    if ($solusi) { Write-Host "       Solusi: $solusi" -ForegroundColor Red }
}
function Berhenti {
    Write-Host ""
    Write-Host "Ada $global:jumlahMasalah masalah yang harus diperbaiki dulu (lihat [X] di atas). Server tidak dijalankan." -ForegroundColor Red
    exit 1
}
function Baca-Env {
    $hasil = @{}
    foreach ($baris in Get-Content (Join-Path $web ".env") -Encoding UTF8) {
        if ($baris -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') { $hasil[$Matches[1]] = $Matches[2].Trim() }
    }
    return $hasil
}
function Port-Menyala([string]$alamat, [int]$p) {
    try {
        $c = New-Object System.Net.Sockets.TcpClient
        $iar = $c.BeginConnect($alamat, $p, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne(1500) -and $c.Connected
        $c.Close()
        return $ok
    } catch { return $false }
}

Write-Host "SIGAP JUMBARA - pemeriksaan kesiapan" -ForegroundColor Cyan
Write-Host "Folder aplikasi: $web"

# --- 1. Python dan virtualenv ------------------------------------------------
Judul "1. Python dan paket"
if (-not (Test-Path $py)) {
    $adaPy312 = $false
    try { & py -3.12 --version *> $null; $adaPy312 = ($LASTEXITCODE -eq 0) } catch { $adaPy312 = $false }
    if (-not $adaPy312) {
        Masalah "Python 3.12 tidak ditemukan." "winget install --id Python.Python.3.12 --scope user  (lalu buka terminal baru)"
        Berhenti
    }
    Info "Virtualenv belum ada, membuat web\.venv ..."
    & py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { Masalah "Gagal membuat virtualenv." "Jalankan manual: py -3.12 -m venv .venv"; Berhenti }
}
$versi = (& $py -c "import sys; print('%d.%d.%d' % sys.version_info[:3])").Trim()
if ($versi -like "3.12.*") { Ok "Python $versi (virtualenv web\.venv)" } else { Peringatan "Virtualenv memakai Python $versi, seharusnya 3.12" }

# Pasang paket bila requirements berubah sejak pemasangan terakhir.
$req = if (Test-Path "requirements-dev.txt") { "requirements-dev.txt" } else { "requirements.txt" }
$tanda = Join-Path $web ".venv\.sigap-requirements"
$sidikBaru = ((Get-FileHash $req).Hash + (Get-FileHash "requirements.txt").Hash)
$sidikLama = if (Test-Path $tanda) { Get-Content $tanda -Raw } else { "" }
if ($sidikBaru -ne $sidikLama.Trim()) {
    Info "Memasang/memperbarui paket dari $req ..."
    & $py -m pip install -q --disable-pip-version-check -r $req
    if ($LASTEXITCODE -ne 0) { Masalah "Pemasangan paket gagal." "Periksa koneksi internet lalu jalankan lagi"; Berhenti }
    Set-Content -Path $tanda -Value $sidikBaru
}
& $py -c "import django, MySQLdb, waitress, environ, cryptography, PIL, segno, reportlab, xlsxwriter, django_ratelimit, whitenoise" 2>$null
if ($LASTEXITCODE -eq 0) { Ok "Paket lengkap (Django $(& $py -c 'import django; print(django.get_version())'))" }
else { Masalah "Ada paket yang belum terpasang." ".venv\Scripts\pip install -r $req"; Berhenti }

# --- 2. File .env --------------------------------------------------------------
Judul "2. Pengaturan web\.env"
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Masalah "File .env belum ada. Sudah disalin dari .env.example, tetapi harus diisi dulu." "Buka web\.env lalu isi DB_PASSWORD, SIGAP_KUNCI_NIK, SIGAP_KUNCI_HASH_NIK, DJANGO_SECRET_KEY (cara membuatnya tertulis di file itu)"
    Berhenti
}
$envv = Baca-Env
$wajib = @("DJANGO_SECRET_KEY", "DB_NAME", "DB_USER", "DB_PASSWORD", "SIGAP_KUNCI_NIK", "SIGAP_KUNCI_HASH_NIK")
$kosong = @($wajib | Where-Object { -not $envv[$_] -or $envv[$_] -like "ganti-*" })
if ($kosong.Count) { Masalah ("Isian .env masih kosong: " + ($kosong -join ", ")) "Isi di web\.env (petunjuk ada di .env.example)"; Berhenti }
Ok "Isian wajib .env terisi"
$debug = ($envv["DJANGO_DEBUG"] -match '^(?i:true|1|yes|on)$')
if ($debug) { Info "Mode pengembangan (DJANGO_DEBUG=True)" } else { Info "Mode produksi (DJANGO_DEBUG=False): file statis diambil dari staticfiles" }
$dbHost = if ($envv["DB_HOST"]) { $envv["DB_HOST"] } else { "127.0.0.1" }
$dbPort = if ($envv["DB_PORT"]) { [int]$envv["DB_PORT"] } else { 3306 }

# --- 3. MariaDB ------------------------------------------------------------------
Judul "3. MariaDB ($dbHost`:$dbPort)"
if (-not (Port-Menyala $dbHost $dbPort)) {
    Peringatan "MariaDB di port $dbPort belum menyala. Mencoba menyalakan ..."
    $dinyalakan = $false
    foreach ($svc in @("MariaDB1011dev", "MariaDB1011")) {
        $s = Get-Service -Name $svc -ErrorAction SilentlyContinue
        if ($s -and $s.Status -ne "Running") {
            try { Start-Service -Name $svc; $dinyalakan = $true; Info "Service $svc dinyalakan" } catch { Info "Service $svc tidak bisa dinyalakan tanpa Administrator" }
        }
    }
    if (-not $dinyalakan -and (Test-Path (Join-Path $env:USERPROFILE "sigap-mariadb"))) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "mariadb-dev.ps1") -Port $dbPort | Out-Host
    }
    for ($i = 0; $i -lt 20 -and -not (Port-Menyala $dbHost $dbPort); $i++) { Start-Sleep -Seconds 1 }
}
if (Port-Menyala $dbHost $dbPort) { Ok "MariaDB menyala di port $dbPort" }
else {
    Masalah "MariaDB tidak menyala di port $dbPort." "Laptop: scripts\windows\mariadb-dev.ps1 ; Server: Start-Service MariaDB1011 ; atau periksa DB_PORT di .env"
    Berhenti
}

$cekDb = & $py -c @"
import django, os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sigap.settings')
django.setup()
from django.db import connection
try:
    with connection.cursor() as c:
        c.execute('SELECT VERSION()')
        print(c.fetchone()[0])
except Exception as e:
    print('GAGAL ' + str(e)); sys.exit(1)
"@ 2>&1
if ($LASTEXITCODE -ne 0) {
    Masalah "Tidak bisa masuk ke database: $cekDb" "Periksa DB_NAME/DB_USER/DB_PASSWORD di .env dan pastikan user database sudah dibuat (docs\21-DEPLOY-WINDOWS.md bagian 2.2)"
    Berhenti
}
$versiDb = ($cekDb | Select-Object -Last 1)
if ($versiDb -match '^(\d+)\.(\d+)' -and ([int]$Matches[1] -gt 10 -or ([int]$Matches[1] -eq 10 -and [int]$Matches[2] -ge 5))) { Ok "Terhubung ke MariaDB $versiDb" }
else { Masalah "Versi database $versiDb tidak didukung (butuh MariaDB 10.5+)." "Periksa DB_PORT: jangan memakai MariaDB XAMPP 10.4"; Berhenti }

# --- 4. Struktur database dan data awal ---------------------------------------
Judul "4. Database aplikasi"
& $py manage.py migrate --noinput | Out-Null
if ($LASTEXITCODE -ne 0) { Masalah "Migrasi database gagal." "Jalankan: .venv\Scripts\python manage.py migrate (lihat pesan galatnya)"; Berhenti }
Ok "Migrasi database lengkap"
& $py manage.py createcachetable | Out-Null
& $py manage.py sigap_seed | Out-Null
if ($LASTEXITCODE -eq 0) { Ok "Data awal ada (akun, kontingen, kegiatan, titik absen, pengaturan)" } else { Peringatan "sigap_seed gagal, jalankan manual untuk melihat galatnya" }

# --- 5. Tampilan (CSS dan file statis) ---------------------------------------
Judul "5. Tampilan"
$tw = Join-Path $web "tools\tailwindcss.exe"
if (-not (Test-Path $tw)) {
    Info "Tailwind CLI belum ada, mengunduh ..."
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "unduh-alat.ps1") | Out-Null
}
if (Test-Path $tw) {
    & $tw -c tailwind\tailwind.config.js -i tailwind\input.css -o static\css\app.css --minify 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { Ok "CSS dibangun ulang (static\css\app.css)" }
    else { Peringatan "Tailwind gagal membangun CSS; memakai static\css\app.css yang ada" }
} elseif (Test-Path "static\css\app.css") {
    Peringatan "Tailwind CLI tidak ada; memakai static\css\app.css yang sudah di-commit"
} else { Masalah "CSS tidak ada dan Tailwind CLI tidak bisa diunduh." "scripts\windows\unduh-alat.ps1"; Berhenti }
if (-not $debug -or $Produksi) {
    & $py manage.py collectstatic --noinput | Out-Null
    if ($LASTEXITCODE -eq 0) { Ok "File statis dikumpulkan (collectstatic)" } else { Masalah "collectstatic gagal." ".venv\Scripts\python manage.py collectstatic"; Berhenti }
}

# --- 6. Pemeriksaan menyeluruh aplikasi ---------------------------------------
Judul "6. Pemeriksaan aplikasi (sigap_cek_lingkungan)"
& $py manage.py check | Out-Null
if ($LASTEXITCODE -ne 0) { Masalah "manage.py check menemukan masalah." ".venv\Scripts\python manage.py check"; Berhenti }
& $py manage.py sigap_cek_lingkungan
if ($LASTEXITCODE -ne 0) { Masalah "sigap_cek_lingkungan menemukan masalah wajib (tanda X di atas)." ""; Berhenti }

if ($Tes) {
    Judul "7. Tes otomatis"
    & (Join-Path $web ".venv\Scripts\ruff.exe") check .
    if ($LASTEXITCODE -ne 0) { Masalah "ruff check menemukan masalah." ""; Berhenti }
    & (Join-Path $web ".venv\Scripts\pytest.exe") -q
    if ($LASTEXITCODE -ne 0) { Masalah "Ada tes yang gagal." ""; Berhenti }
    Ok "ruff dan pytest lulus"
}

# --- Alamat akses -----------------------------------------------------------------
Judul "Alamat"
if ((Port-Menyala "127.0.0.1" $Port) -and $CekSaja) {
    Info "Port $Port sedang dipakai (server SIGAP mungkin sudah berjalan)."
} elseif (Port-Menyala "127.0.0.1" $Port) {
    Masalah "Port $Port sudah dipakai program lain (mungkin server SIGAP sudah berjalan di jendela lain)." "Tutup server lama (Ctrl+C di jendelanya) atau pakai: jalankan.bat -Port 8080"
    Berhenti
}
$hosts = ($envv["DJANGO_ALLOWED_HOSTS"] -split ",") | ForEach-Object { $_.Trim() }
$ipLan = @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" -and $_.PrefixOrigin -ne "WellKnown" } |
    Select-Object -ExpandProperty IPAddress)
$skema = if ($pakaiHttps) { "https" } else { "http" }
Info "Laptop ini : $skema`://localhost:$Port/"
foreach ($ip in $ipLan) {
    if ($hosts -contains $ip) { Info "HP (Wi-Fi sama): $skema`://$ip`:$Port/   (ketik $skema`://)" }
    else { Peringatan "IP $ip belum ada di DJANGO_ALLOWED_HOSTS. Tambahkan ,$ip di web\.env bila ingin membuka dari HP." }
}
Info "Superadmin : $skema`://localhost:$Port/masuk/"
if ($pakaiHttps) {
    Info "Sertifikat buatan sendiri: pertama kali di HP/browser muncul peringatan. Chrome: Lanjutan > Lanjutkan. Safari: Tampilkan Detail > kunjungi."
} else {
    Peringatan "Mode http:// : kamera HP (pemindai, Anjangsana) tidak bisa dipakai. Jalankan jalankan.bat tanpa -Http/-Produksi untuk HTTPS."
}

Write-Host ""
if ($global:jumlahPeringatan) { Write-Host "Siap, dengan $global:jumlahPeringatan peringatan (tanda [!])." -ForegroundColor Yellow }
else { Write-Host "Semua siap." -ForegroundColor Green }

if ($CekSaja) { exit 0 }

Write-Host ""
if ($pakaiHttps) {
    Write-Host "Menjalankan server HTTPS di port $Port. Hentikan dengan Ctrl+C." -ForegroundColor Cyan
    & $py manage.py sigap_https_dev "0.0.0.0:$Port"
} elseif ($Produksi) {
    $threads = if ($envv["WAITRESS_THREADS"]) { $envv["WAITRESS_THREADS"] } else { "48" }
    Write-Host "Menjalankan Waitress (mode produksi) di port $Port. Hentikan dengan Ctrl+C." -ForegroundColor Cyan
    & (Join-Path $web ".venv\Scripts\waitress-serve.exe") "--listen=0.0.0.0:$Port" "--threads=$threads" "--channel-timeout=120" sigap.wsgi:application
} else {
    Write-Host "Menjalankan server pengembangan di port $Port. Hentikan dengan Ctrl+C." -ForegroundColor Cyan
    & $py manage.py runserver "0.0.0.0:$Port"
}
