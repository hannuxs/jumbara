# SIGAP JUMBARA: satu perintah untuk memeriksa kesiapan lalu menjalankan server.
#
# Cara pakai (dari folder proyek):
#   jalankan.bat                    PENGEMBANGAN (laptop): periksa semua lalu jalankan server HTTPS
#   jalankan.bat -Produksi          PRODUKSI (server): Caddy (HTTPS asli Let's Encrypt) + Waitress
#   jalankan.bat -CekSaja           hanya periksa, tidak menjalankan server
#   jalankan.bat -Tes               jalankan juga tes otomatis (pytest) dan ruff sebelum server
#   jalankan.bat -Http              pengembangan tanpa HTTPS (http://), misalnya bila ada masalah sertifikat
#
# Port diatur di web\.env (SIGAP_PORT, bawaan 8585), tidak lewat perintah.
# Pengembangan: HTTPS dengan sertifikat buatan sendiri (sigap_https_dev) di port SIGAP_PORT, karena kamera HP
#   hanya jalan lewat https://.
# Produksi: Caddy (tools\caddy.exe) mendengar port 80 dan 443, otomatis meminta dan memperbarui sertifikat
#   Let's Encrypt untuk SIGAP_DOMAIN, lalu meneruskan ke Waitress di 127.0.0.1:SIGAP_PORT. Router harus
#   meneruskan port luar 80 dan 443 ke PC server port 80 dan 443 (docs/21-DEPLOY-WINDOWS.md).
#
# Yang diperiksa dan diperbaiki otomatis bila aman:
#   Python 3.12, virtualenv web\.venv, paket requirements, file web\.env, kunci rahasia,
#   MariaDB menyala (dinyalakan bila mati), koneksi database, migrasi, tabel cache, data awal,
#   Tailwind CLI, CSS, file statis (mode DEBUG=False), port bebas, alamat IP untuk HP.
# Hanya memakai karakter ASCII agar aman di Windows PowerShell 5.1.
param(
    [switch]$CekSaja,
    [switch]$Produksi,
    [switch]$Tes,
    [switch]$Http,
    [switch]$Https  # tidak dipakai lagi (HTTPS sudah bawaan); dibiarkan agar perintah lama tidak galat
)
# "Continue": peringatan di stderr dari program luar (pip, tailwind) tidak boleh menghentikan skrip.
# Keberhasilan setiap langkah dinilai dari $LASTEXITCODE.
$ErrorActionPreference = "Continue"
# Pengembangan: HTTPS bawaan kecuali -Http. Produksi: HTTPS oleh Caddy, Waitress hanya di 127.0.0.1.
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
if ($args -contains "-Port") { Write-Host "  [!]  Opsi -Port sudah dihapus dan diabaikan. Ubah port lewat SIGAP_PORT di web\.env." -ForegroundColor Yellow }
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
$req = if ((Test-Path "requirements-dev.txt") -and -not $Produksi) { "requirements-dev.txt" } else { "requirements.txt" }
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
$Port = 8585
$teksPort = if ($envv["SIGAP_PORT"]) { $envv["SIGAP_PORT"] } elseif ($envv["WAITRESS_PORT"]) { $envv["WAITRESS_PORT"] } else { "8585" }
if ($teksPort -match '^\d+$' -and [int]$teksPort -ge 1024 -and [int]$teksPort -le 65535) { $Port = [int]$teksPort }
else { Masalah "SIGAP_PORT di .env tidak valid ($teksPort)." "Isi angka 1024-65535, misalnya SIGAP_PORT=8585"; Berhenti }
Info "Port aplikasi: $Port (SIGAP_PORT di .env)"
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


# --- Produksi: Caddy + Waitress ------------------------------------------------
$caddyExe = Join-Path $web "tools\caddy.exe"
$caddyfile = Join-Path $web "tools\Caddyfile"
$folderLog = Join-Path $web "logs"
if ($Produksi) {
    Judul "Produksi (HTTPS asli lewat Caddy)"
    $domain = ($envv["SIGAP_DOMAIN"] + "").Trim().ToLower()
    if (-not $domain -or $domain -notmatch '^[a-z0-9.-]+\.[a-z]{2,}$') {
        Masalah "SIGAP_DOMAIN belum diisi atau tidak valid di .env." "Isi SIGAP_DOMAIN=sigapjumbara.my.id (tanpa https:// dan tanpa garis miring)"; Berhenti
    }
    Ok "Domain: $domain"
    if ($debug) { Masalah "DJANGO_DEBUG=True di produksi berbahaya (pesan galat lengkap terlihat publik)." "Ubah DJANGO_DEBUG=False di web\.env"; Berhenti }
    if ($envv["SIGAP_HTTPS"] -match '^(?i:false|0|no|off)$') { Masalah "SIGAP_HTTPS=False di produksi membuat cookie login tidak aman." "Ubah SIGAP_HTTPS=True (atau hapus barisnya)"; Berhenti }
    $hostsCek = ($envv["DJANGO_ALLOWED_HOSTS"] -split ",") | ForEach-Object { $_.Trim().ToLower() }
    if ($hostsCek -notcontains $domain) { Masalah "DJANGO_ALLOWED_HOSTS belum memuat $domain." "Tambahkan: DJANGO_ALLOWED_HOSTS=$domain,localhost,127.0.0.1"; Berhenti }
    $csrfCek = ($envv["CSRF_TRUSTED_ORIGINS"] -split ",") | ForEach-Object { $_.Trim().ToLower() }
    if ($csrfCek -notcontains "https://$domain") { Masalah "CSRF_TRUSTED_ORIGINS belum memuat https://$domain." "Isi: CSRF_TRUSTED_ORIGINS=https://$domain"; Berhenti }
    if (($envv["SIGAP_URL"] + "").TrimEnd("/").ToLower() -ne "https://$domain") { Peringatan "SIGAP_URL sebaiknya https://$domain (dipakai di QR poster dan tautan)." }
    else { Ok "Pengaturan .env produksi sesuai (DEBUG mati, HTTPS, host, CSRF)" }
    if (-not (Test-Path $caddyExe)) {
        Info "Caddy belum ada, mengunduh ..."
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "unduh-alat.ps1") | Out-Host
    }
    if (-not (Test-Path $caddyExe)) { Masalah "tools\caddy.exe tidak ada." "Jalankan scripts\windows\unduh-alat.ps1 (butuh internet)"; Berhenti }
    foreach ($pt in @(80, 443)) {
        if (Port-Menyala "127.0.0.1" $pt) {
            if ($CekSaja) { Info "Port $pt sedang dipakai (Caddy SIGAP mungkin sudah berjalan)." }
            else { Masalah "Port $pt sudah dipakai program lain (Apache XAMPP, IIS, atau jendela SIGAP lain)." "Matikan program itu (Apache di XAMPP Control Panel: Stop) lalu jalankan lagi"; Berhenti }
        }
    }
    New-Item -ItemType Directory -Force -Path $folderLog | Out-Null
    $email = ($envv["SIGAP_EMAIL_ACME"] + "").Trim()
    $baris = @("# Dibuat otomatis oleh jalankan.bat -Produksi. Jangan diubah manual; ubah web\.env lalu jalankan lagi.", "{")
    if ($email) { $baris += "`temail $email" }
    $baris += "`tadmin localhost:2019"
    $baris += "}"
    $baris += ""
    $baris += "$domain {"
    $baris += "`tencode zstd gzip"
    $baris += "`treverse_proxy 127.0.0.1:$Port {"
    $baris += "`t`t# Header ini hanya boleh dari Cloudflare; buang agar IP pengunjung tidak bisa dipalsukan."
    $baris += "`t`theader_up -CF-Connecting-IP"
    $baris += "`t}"
    $baris += "`tlog {"
    $baris += "`t`toutput file " + ($folderLog -replace '\\', '/') + "/caddy-akses.log {"
    $baris += "`t`t`troll_size 10mb"
    $baris += "`t`t`troll_keep 5"
    $baris += "`t`t}"
    $baris += "`t}"
    $baris += "}"
    Set-Content -Path $caddyfile -Value ($baris -join "`r`n") -Encoding ASCII
    $cekCaddy = & $caddyExe validate --config $caddyfile --adapter caddyfile 2>&1
    if ($LASTEXITCODE -ne 0) { Masalah "Konfigurasi Caddy tidak valid: $($cekCaddy | Select-Object -Last 1)" ""; Berhenti }
    Ok "Caddy siap (tools\Caddyfile): https://$domain -> 127.0.0.1:$Port"
    Info "Syarat: router meneruskan port luar 80 dan 443 ke PC ini port 80 dan 443; Windows Firewall mengizinkan keduanya."
}

# --- Alamat akses -----------------------------------------------------------------
Judul "Alamat"
if ((Port-Menyala "127.0.0.1" $Port) -and $CekSaja) {
    Info "Port $Port sedang dipakai (server SIGAP mungkin sudah berjalan)."
} elseif (Port-Menyala "127.0.0.1" $Port) {
    Masalah "Port $Port sudah dipakai program lain (mungkin server SIGAP sudah berjalan di jendela lain)." "Tutup server lama (Ctrl+C di jendelanya) atau ganti SIGAP_PORT di web\.env"
    Berhenti
}
$hosts = ($envv["DJANGO_ALLOWED_HOSTS"] -split ",") | ForEach-Object { $_.Trim() }
$ipLan = @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" -and $_.PrefixOrigin -ne "WellKnown" } |
    Select-Object -ExpandProperty IPAddress)
$skema = if ($pakaiHttps) { "https" } else { "http" }
if ($Produksi) { Info "Alamat publik: https://$domain/  (superadmin: https://$domain/masuk/)" }
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
    $logCaddy = Join-Path $folderLog "caddy.log"
    $caddy = Start-Process -FilePath $caddyExe -ArgumentList @("run", "--config", "`"$caddyfile`"", "--adapter", "caddyfile") `
        -NoNewWindow -PassThru -RedirectStandardError $logCaddy -RedirectStandardOutput (Join-Path $folderLog "caddy-keluaran.log")
    Start-Sleep -Seconds 3
    if ($caddy.HasExited) {
        Write-Host "Caddy berhenti. Isi log terakhir:" -ForegroundColor Red
        Get-Content $logCaddy -Tail 15 | Out-Host
        exit 1
    }
    Write-Host "Caddy berjalan (HTTPS https://$domain, log: logs\caddy.log). Sertifikat diminta otomatis saat pertama kali." -ForegroundColor Cyan
    Write-Host "Menjalankan Waitress di 127.0.0.1:$Port. Hentikan keduanya dengan Ctrl+C." -ForegroundColor Cyan
    try {
        & (Join-Path $web ".venv\Scripts\waitress-serve.exe") "--listen=127.0.0.1:$Port" "--threads=$threads" "--channel-timeout=120" "--connection-limit=1000" sigap.wsgi:application
    } finally {
        if (-not $caddy.HasExited) { Stop-Process -Id $caddy.Id -Force -ErrorAction SilentlyContinue }
        Write-Host "Caddy dan Waitress dihentikan."
    }
} else {
    Write-Host "Menjalankan server pengembangan di port $Port. Hentikan dengan Ctrl+C." -ForegroundColor Cyan
    & $py manage.py runserver "0.0.0.0:$Port"
}
