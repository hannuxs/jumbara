# 21. Pemasangan di Server Windows (Python/Django, tanpa XAMPP)

Panduan untuk Farhan memasang SIGAP JUMBARA di PC server Windows. Ditulis dan diuji oleh Claude Code di laptop pengembangan (Windows 10 Pro, MariaDB 10.11, Python 3.12.10). Bagian yang **butuh hak Administrator** (Task Scheduler, MSI MariaDB) sudah diperiksa sintaksnya tetapi belum dijalankan oleh Claude karena hak admin diblokir; ditandai **(belum diuji, jalankan sendiri)**.

**Keputusan Farhan (24 Okt 2026):** produksi **tidak memakai XAMPP** (Apache tidak dipakai) dan **tidak memakai Windows Service** untuk aplikasi. Produksi dijalankan dari terminal dengan **`jalankan.bat -Produksi`**; pengembangan cukup **`jalankan.bat`**. Port aplikasi diatur hanya di `web\.env` (`SIGAP_PORT`, bawaan **8585**).

Susunan di server:

```
HP/laptop -> https://sigapjumbara.my.id  (port 443; http:// port 80 dialihkan ke https)
          -> Caddy (web\tools\caddy.exe, sertifikat Let's Encrypt otomatis)
          -> Waitress 127.0.0.1:SIGAP_PORT (Django; /static/ disajikan WhiteNoise)
          -> MariaDB 10.11 (Windows Service "MariaDB1011")
```

Caddy dan Waitress berjalan di satu jendela terminal yang dibuka `jalankan.bat -Produksi`. Menutup jendela atau menekan Ctrl+C menghentikan keduanya.

Semua perintah di bawah dijalankan di **PowerShell**. Yang bertanda **(Admin)** harus di PowerShell "Run as Administrator".

---

## 1. Prasyarat

| Program | Cara pasang | Cek |
|---|---|---|
| Python 3.12 | `winget install --id Python.Python.3.12 --scope user` (atau installer python.org, centang "Add to PATH" dan "py launcher") | `py --list` menampilkan `-V:3.12` |
| Git for Windows | `winget install --id Git.Git` | `git --version` |
| MariaDB 10.11 LTS | Lihat bagian 2 | `mysql --version` atau `mariadb --version` |
| Caddy 2.8.4 | Diunduh otomatis oleh `unduh-alat.ps1` (dipanggil `jalankan.bat -Produksi` bila belum ada), sidik SHA-512 diperiksa | `web\tools\caddy.exe version` |

Node.js, XAMPP, Apache, cloudflared, WinSW **tidak** diperlukan. **Port 80 dan 443 harus bebas**: hentikan/copot Apache XAMPP, IIS (`World Wide Web Publishing Service`), Skype lama, atau program lain yang memakainya. Cek: `netstat -ano | findstr ":80 :443"`.

## 2. Database MariaDB 10.11

XAMPP membawa MariaDB **10.4** yang tidak didukung Django 5.2. Keputusan Farhan (18 Okt 2026): **pasang MariaDB 10.11 terpisah di port 3307**, MariaDB XAMPP tetap di 3306 untuk proyek lain. Jika server produksi tidak punya database lain di XAMPP, boleh juga memakai port 3306 setelah MySQL XAMPP dihentikan (ubah `PORT=` dan `DB_PORT`).

### 2.1 Pasang sebagai service (Admin) (belum diuji, jalankan sendiri)

1. Unduh MSI resmi: `https://archive.mariadb.org/mariadb-10.11.19/winx64-packages/mariadb-10.11.19-winx64.msi` (≈ 86 MB). SHA256: `83af9d523bf7ba989ea0031d4ebca7e4dc21e49f435122570ddc87f0620b3a5c`. Cek dengan `Get-FileHash .\mariadb-10.11.19-winx64.msi`.
2. Pasang (ganti `SANDIROOT` dengan sandi root yang kuat, hanya huruf dan angka):
   ```powershell
   msiexec /i mariadb-10.11.19-winx64.msi /qn SERVICENAME=MariaDB1011 PORT=3307 PASSWORD=SANDIROOT UTF8=1 INSTALLDIR="C:\Program Files\MariaDB 10.11"
   ```
   Atau jalankan MSI dengan klik dua kali: centang "Use UTF8", isi sandi root, nama service `MariaDB1011`, port `3307`.
3. Tambahkan pengaturan berikut di `C:\Program Files\MariaDB 10.11\data\my.ini` bagian `[mysqld]`, lalu `Restart-Service MariaDB1011`:
   ```ini
   bind-address=127.0.0.1
   character-set-server=utf8mb4
   collation-server=utf8mb4_unicode_ci
   default-time-zone='+08:00'
   max_connections=200
   innodb_buffer_pool_size=1G
   sql_mode=STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION
   ```
   (`innodb_buffer_pool_size` sekitar 1/4 RAM; 512M cukup untuk laptop 8 GB.)

### 2.2 Buat database dan user (sudah diuji)

```powershell
& "C:\Program Files\MariaDB 10.11\bin\mariadb.exe" -h127.0.0.1 -P3307 -uroot -p
```
```sql
CREATE DATABASE sigap_jumbara CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'sigap'@'localhost' IDENTIFIED BY 'SANDI_APLIKASI';
CREATE USER 'sigap'@'127.0.0.1' IDENTIFIED BY 'SANDI_APLIKASI';
GRANT ALL PRIVILEGES ON sigap_jumbara.* TO 'sigap'@'localhost', 'sigap'@'127.0.0.1';
-- database tes otomatis (pytest) hanya perlu di laptop pengembangan:
GRANT ALL PRIVILEGES ON sigap_jumbara_test.* TO 'sigap'@'localhost', 'sigap'@'127.0.0.1';
FLUSH PRIVILEGES;
```

## 3. Aplikasi (sudah diuji)

```powershell
cd C:\
git clone <alamat-repo> sigap-jumbara        # atau salin folder proyek ke C:\sigap-jumbara
cd C:\sigap-jumbara\web
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File scripts\windows\unduh-alat.ps1     # tailwindcss.exe + caddy.exe
copy .env.example .env
notepad .env                                   # isi, lihat 3.1
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py createcachetable
.venv\Scripts\python manage.py sigap_seed      # 3 akun, 29 kontingen, 13 kegiatan, 60 titik absen, 6 sesi Anjangsana, pengaturan
powershell -ExecutionPolicy Bypass -File scripts\windows\bangun-css.ps1
.venv\Scripts\python manage.py collectstatic --noinput
.venv\Scripts\python manage.py check --deploy
.venv\Scripts\python manage.py sigap_cek_lingkungan
```

`sigap_seed` aman dijalankan berulang (tidak membuat data ganda, tidak mengubah sandi akun yang sudah ada, tidak menimpa kuota yang sudah diubah manual).

`check --deploy` normal menyisakan 2 peringatan: `security.W004` (HSTS, aktifkan setelah domain final) dan `security.W008` (pengalihan http ke https dilakukan Caddy, bukan Django).

Langkah migrasi, `collectstatic`, CSS, dan pemeriksaan di atas juga dijalankan otomatis oleh `jalankan.bat -Produksi` setiap kali dijalankan.

### 3.1 Isi `web\.env` di server

| Kunci | Nilai produksi |
|---|---|
| `DJANGO_DEBUG` | `False` (wajib; `True` menampilkan kode, isi pengaturan, dan jejak galat ke publik saat ada galat) |
| `DJANGO_SECRET_KEY` | acak: `.venv\Scripts\python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `DJANGO_ALLOWED_HOSTS` | `sigapjumbara.my.id,localhost,127.0.0.1` |
| `CSRF_TRUSTED_ORIGINS` | `https://sigapjumbara.my.id` |
| `SIGAP_URL` | `https://sigapjumbara.my.id` (dipakai di QR form, tautan WhatsApp, kartu) |
| `SIGAP_HTTPS` | `True` (wajib; cookie sesi dan CSRF hanya dikirim lewat https) |
| `SIGAP_DOMAIN` | `sigapjumbara.my.id` (domain untuk sertifikat Caddy; wajib untuk `-Produksi`) |
| `SIGAP_EMAIL_ACME` | email Farhan (opsional; pemberitahuan Let's Encrypt bila sertifikat bermasalah) |
| `SIGAP_PORT` | `8585` (port Waitress di 127.0.0.1; tidak perlu dibuka di router) |
| `DB_PORT` | `3307` (atau `3306`) |
| `DB_PASSWORD` | sandi user `sigap` |
| `SIGAP_KUNCI_NIK` | `.venv\Scripts\python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `SIGAP_KUNCI_HASH_NIK` | `.venv\Scripts\python -c "import secrets; print(secrets.token_hex(32))"` |
| `SIGAP_FOLDER_PRIVAT` | `C:\sigap-jumbara\web\privat` |
| `SIGAP_FOLDER_CADANGAN` | disk lain, misalnya `D:\cadangan-sigap` |
| `SIGAP_MYSQLDUMP_PATH` | `C:\Program Files\MariaDB 10.11\bin\mariadb-dump.exe` |
| `SIGAP_SANDI_AWAL_*` | sandi awal 3 akun (min. 10 karakter), lalu segera diganti dari menu Akun |

**Penting:** `SIGAP_KUNCI_NIK` dan `SIGAP_KUNCI_HASH_NIK` wajib dicatat di tempat aman (pengelola sandi + flashdisk). Tanpa kunci ini, NIK di database dan di cadangan tidak bisa dibaca lagi. Jangan pernah mengganti `SIGAP_KUNCI_HASH_NIK` setelah ada data.

## 4. Domain, router, dan firewall (sekali saja)

1. **DNS domain** `sigapjumbara.my.id`: record `A` mengarah ke IP publik internet server (cek IP di https://ifconfig.me dari server). Bila IP publik berubah-ubah (IP dinamis), perbarui record ini atau pakai layanan DDNS. Cek: `nslookup sigapjumbara.my.id` harus menghasilkan IP publik itu.
2. **Router/modem**: teruskan (port forwarding/virtual server) **port 80 → IP lokal server port 80** dan **port 443 → IP lokal server port 443**, protokol TCP. Jangan meneruskan ke 8585: port itu hanya untuk Waitress di dalam server. Beri server IP lokal tetap (DHCP reservation) agar penerusan tidak putus.
3. **Windows Firewall (Admin)**:
   ```powershell
   New-NetFirewallRule -DisplayName "SIGAP HTTP" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow
   New-NetFirewallRule -DisplayName "SIGAP HTTPS" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow
   ```
   Saat Caddy pertama kali jalan, Windows mungkin bertanya izin jaringan: pilih **Allow**.
4. Bila ISP memblokir port 80 masuk, Let's Encrypt tetap bisa memakai port 443 (TLS-ALPN). Bila 443 juga diblokir, HTTPS asli tidak bisa didapat dari server ini; hubungi ISP atau pakai jaringan lain.

## 5. Menjalankan produksi

Dari folder proyek (`C:\sigap-jumbara`):

```
jalankan.bat -Produksi
```

Yang dilakukan:
1. Pemeriksaan biasa (Python, paket `requirements.txt`, `.env`, MariaDB, migrasi, CSS, `collectstatic`, `sigap_cek_lingkungan`).
2. Pemeriksaan khusus produksi, menolak jalan bila salah: `SIGAP_DOMAIN` terisi, `DJANGO_DEBUG=False`, `SIGAP_HTTPS` tidak `False`, domain ada di `DJANGO_ALLOWED_HOSTS`, `https://domain` ada di `CSRF_TRUSTED_ORIGINS`, `caddy.exe` ada (diunduh bila belum), port 80 dan 443 bebas. Peringatan bila `SIGAP_URL` bukan `https://domain`.
3. Menulis `web\tools\Caddyfile` dari `.env` (jangan diubah manual) lalu `caddy validate`.
4. Menyalakan **Caddy** (log `web\logs\caddy.log`, akses `web\logs\caddy-akses.log`) dan **Waitress** di `127.0.0.1:SIGAP_PORT` (48 thread, bisa diubah `WAITRESS_THREADS`).

Pertama kali, Caddy meminta sertifikat ke Let's Encrypt (beberapa detik sampai 1 menit); sertifikat disimpan di `%AppData%\Caddy` dan **diperbarui otomatis**. Setelah itu buka `https://sigapjumbara.my.id` dari HP memakai data seluler (bukan Wi-Fi server) dan pastikan gembok tampil tanpa peringatan.

Caddy membuang header `CF-Connecting-IP` dari luar dan mengisi `X-Forwarded-For`/`X-Forwarded-Proto` sendiri, sehingga IP pengirim di log dan pembatas laju tidak bisa dipalsukan (sudah diuji).

**Biarkan jendela terminal terbuka** selama acara. Agar hidup lagi setelah PC restart, buat pintasan `jalankan.bat -Produksi` di folder Startup (`Win+R` → `shell:startup`) atau login otomatis lalu jalankan manual. Hentikan dengan **Ctrl+C** (Caddy ikut berhenti).

Cek kesiapan tanpa menyalakan server: `jalankan.bat -Produksi -CekSaja`.

## 6. HTTPS

- **Produksi:** Caddy dengan sertifikat asli Let's Encrypt (bagian 4-5). Keputusan Farhan 24 Okt 2026, menggantikan rencana Apache/win-acme. Cloudflare Tunnel tidak dipakai (keputusan 22 Okt 2026).
- **Laptop (pengembangan dan uji coba):** `jalankan.bat` selalu HTTPS (`python manage.py sigap_https_dev`) di `https://IP-laptop:8585` dengan sertifikat buatan sendiri untuk localhost dan IP laptop; `http://` di port yang sama dialihkan ke `https://`. Di HP (Wi-Fi sama) buka alamat itu dan terima peringatan sertifikat: Chrome Android > Lanjutan > Lanjutkan; Safari iPhone > Tampilkan Detail > kunjungi situs web ini. IP laptop harus ada di `DJANGO_ALLOWED_HOSTS`; izinkan port 8585 di Windows Firewall bila diminta. Server produksi **tidak** memakai ini: bila browser menampilkan "Not secure" dengan sertifikat "SIGAP JUMBARA (uji lokal)", berarti server dijalankan dengan `jalankan.bat` biasa, bukan `-Produksi`.
- Setelah stabil dan domain final: `SECURE_HSTS_SECONDS=31536000` di `.env`.

**Uji beban di server (sebelum acara, `22-PENGUJIAN.md`):** dengan `jalankan.bat -Produksi` berjalan, dari folder `web` di terminal lain:
`.venv\Scripts\python manage.py sigap_uji_beban --perangkat 30 --titik 15 --pindaian 40 --ya`
(alamat otomatis `127.0.0.1:SIGAP_PORT`). Hasil harus "Uji beban LULUS" dengan 0 pasangan ganda dan p95 di bawah 1 detik. Data uji (kontingen tersembunyi UJI-BEBAN, titik UB-...) dihapus otomatis. Jangan dijalankan setelah acara dimulai.

## 7. Task Scheduler (Admin) (belum diuji, jalankan sendiri)

```powershell
cd C:\sigap-jumbara\web
powershell -ExecutionPolicy Bypass -File scripts\windows\daftar-task-scheduler.ps1
```

Membuat tugas **"SIGAP jadwal"** sebagai akun SYSTEM, setiap 1 menit menjalankan `python manage.py sigap_jadwal`:
- cadangan harian setelah pukul 02.00 WITA,
- cadangan setiap 3 jam pada 12–15 November (tanggal bisa diubah di pengaturan `jadwal.acara_mulai/selesai`),
- bersih-bersih sesi kedaluwarsa sekali sehari.

Perintah `sigap_jadwal` sendiri sudah diuji: `python manage.py sigap_jadwal --paksa-cadangan` menghasilkan `sigap_YYYYmmdd_HHMMSS_*.zip` berisi `database.sql`, folder `foto\`, dan `BACA-SAYA.txt`. Cadangan lebih dari 14 hari dihapus otomatis. Cadangan juga bisa dibuat dari menu **Superadmin > Cadangan data**.

## 8. Kesiapan PC server selama acara

- Matikan sleep/hibernate: `powercfg /change standby-timeout-ac 0` dan `powercfg /change hibernate-timeout-ac 0`.
- Windows Update: tunda pembaruan (Settings > Windows Update > Pause updates) sampai 16 November, atur "Active hours".
- Firewall: hanya port masuk 80 dan 443 (Caddy). Waitress hanya mendengar `127.0.0.1`, MariaDB `bind-address=127.0.0.1`.
- UPS bila ada. Salin cadangan berkala ke disk lain/penyimpanan awan milik panitia.

## 9. Pembaruan aplikasi

Dari `C:\sigap-jumbara\web`:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows\perbarui.ps1
```
Urutannya: cadangan database dulu → `git pull` (bila folder adalah repositori git; bila tidak, salin file baru secara manual) → pesan untuk menghentikan `jalankan.bat -Produksi` (Ctrl+C) lalu menjalankannya lagi. Saat dijalankan ulang, `jalankan.bat -Produksi` memasang paket, migrasi, CSS, dan `collectstatic`. Hindari jam sibuk. Untuk perbaikan yang lama, nyalakan **Mode perawatan** di Superadmin > Pengaturan form (semua halaman menampilkan "Sedang perbaikan sebentar", kecuali untuk superadmin).

## 10. Memulihkan cadangan (sudah diuji ke database terpisah)

1. Hentikan aplikasi: Ctrl+C di jendela `jalankan.bat -Produksi`.
2. Ekstrak ZIP cadangan ke folder baru, misalnya `D:\pulih\` (isi: `database.sql`, `foto\`, `BACA-SAYA.txt`).
3. Pulihkan database (sebaiknya ke database baru dulu untuk diperiksa):
   ```powershell
   $m = "C:\Program Files\MariaDB 10.11\bin\mariadb.exe"
   & $m -h127.0.0.1 -P3307 -uroot -p -e "CREATE DATABASE sigap_pulih CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
   cmd /c "`"$m`" -h127.0.0.1 -P3307 -uroot -p sigap_pulih < D:\pulih\database.sql"
   ```
   Periksa isinya, misalnya `SELECT COUNT(*) FROM sigap_pulih.biodata_peserta;`. Jika benar, ubah `DB_NAME=sigap_pulih` di `.env` (atau impor ke `sigap_jumbara` setelah database lama diganti nama/dicadangkan).
4. Salin isi `D:\pulih\foto\` ke `SIGAP_FOLDER_PRIVAT\foto\` (timpa).
5. `.env` harus memakai **kunci NIK yang sama** dengan saat cadangan dibuat.
6. Jalankan lagi `jalankan.bat -Produksi` (sudah termasuk `sigap_cek_lingkungan`).

Hasil uji 18 Okt 2026: cadangan dipulihkan ke database `sigap_uji_pulih`; jumlah biodata dan kontingen sama dengan aslinya, foto ada.

## 11. Daftar periksa sebelum 25 Oktober

- [ ] MariaDB 10.11 berjalan sebagai service `MariaDB1011` dan hidup otomatis setelah restart PC.
- [ ] `jalankan.bat -Produksi` berjalan tanpa tanda X; gembok HTTPS tampil di `https://sigapjumbara.my.id` dari HP dengan data seluler.
- [ ] Router meneruskan 80 dan 443 ke server; Windows Firewall mengizinkan 80/443; tidak ada Apache/IIS di 80/443.
- [ ] Pintasan `jalankan.bat -Produksi` di Startup (atau petugas tahu cara menjalankannya lagi setelah restart).
- [ ] `python manage.py check --deploy` hanya menyisakan W004/W008; `DJANGO_DEBUG=False`.
- [ ] `python manage.py sigap_cek_lingkungan` tanpa tanda X.
- [ ] Form biodata diuji dari Android murah, Android baru, iPhone (Safari) lewat HTTPS.
- [ ] Tugas "SIGAP jadwal" menghasilkan cadangan, dan pemulihan berhasil diuji di server.
- [ ] Kata sandi tiga akun sudah diganti dari bawaan (menu Superadmin > Akun).
- [ ] Jadwal buka 26 Okt 00.00 WITA dan tutup 2 Nov 23.59 WITA, status **Otomatis** (bukan Paksa buka).
- [ ] Nomor WhatsApp dan nama superadmin sudah diisi.
- [ ] Kunci NIK di `.env` sudah dicatat di tempat aman.
- [ ] Data uji coba dihapus dari database produksi (atau produksi memakai database baru yang bersih).

## 12. Galat umum

**Tidak bisa masuk setelah mengubah `SIGAP_SANDI_AWAL_*` di `.env`:** sandi di `.env` hanya dipakai saat akun pertama kali dibuat. Untuk menyetel ulang: `python manage.py sigap_atur_sandi superadmin` (ketik sandi baru) atau `python manage.py sigap_atur_sandi --semua --dari-env`.

| Gejala | Penyebab dan solusi |
|---|---|
| `django.db.utils.NotSupportedError: MariaDB 10.5 or later is required` | Masih terhubung ke MariaDB XAMPP 10.4. Periksa `DB_PORT` di `.env` |
| `(2003) Can't connect to MySQL server` atau `(2002) Can't connect to server on '127.0.0.1' (10061)` | MariaDB mati atau port salah. Server: `Start-Service MariaDB1011`. Laptop: `scripts\windows\mariadb-dev.ps1` (lihat bagian 13). Periksa `DB_PORT` |
| `ImproperlyConfigured: Set the SIGAP_KUNCI_NIK environment variable` | `.env` belum lengkap |
| Halaman 500 setelah `DEBUG=False`, log berisi `Missing staticfiles manifest entry` | Belum `collectstatic --noinput` setelah pembaruan |
| Kirim form gagal "Muat ulang halaman" (403 CSRF) lewat domain | `CSRF_TRUSTED_ORIGINS` belum berisi `https://domain` |
| `DisallowedHost` | Domain belum ada di `DJANGO_ALLOWED_HOSTS` |
| Kamera tidak bisa dibuka di HP | Akses bukan lewat HTTPS |
| Cadangan gagal "mysqldump tidak ditemukan" | Perbaiki `SIGAP_MYSQLDUMP_PATH` |
| "Not secure" / sertifikat "SIGAP JUMBARA (uji lokal)" di domain | Server dijalankan dengan `jalankan.bat` (mode laptop). Pakai `jalankan.bat -Produksi` |
| `-Produksi` berhenti: "Port 80 (atau 443) sudah dipakai program lain" | Apache XAMPP/IIS masih jalan. Hentikan: XAMPP Control Panel > Stop Apache (hapus centang Service), atau `Stop-Service W3SVC` lalu `Set-Service W3SVC -StartupType Disabled` (Admin) |
| Caddy log: `challenge failed`, `timeout during connect` | Domain belum mengarah ke IP publik, atau router belum meneruskan 80/443, atau firewall memblokir. Periksa bagian 4 |
| Caddy log: `too many certificates` / `rateLimited` | Terlalu sering meminta sertifikat (batas Let's Encrypt). Tunggu sesuai pesan; jangan menghapus `%AppData%\Caddy` |

## 13. Catatan laptop pengembangan Farhan

- MariaDB 10.11.19 untuk pengembangan dipasang **tanpa installer** (ZIP resmi, terverifikasi SHA256) di `C:\Users\USER\sigap-mariadb\`, port **3307**, data di `C:\Users\USER\sigap-mariadb\data\`. Ini **belum menjadi service**, jadi **mati setiap laptop restart**. Gejalanya saat `runserver`: `OperationalError: (2002, "Can't connect to server on '127.0.0.1' (10061)")`.
  - Menyalakan (setiap kali laptop baru hidup), dari folder `web`:
    ```powershell
    powershell -ExecutionPolicy Bypass -File scripts\windows\mariadb-dev.ps1
    ```
    Jendela MariaDB terbuka terpisah (terperkecil); jangan ditutup selama bekerja. Cek: `... mariadb-dev.ps1 -Status`.
  - **Disarankan, sekali saja:** jadikan Windows Service agar menyala otomatis. Buka PowerShell **Run as Administrator**, tutup dulu jendela MariaDB yang sedang jalan, lalu:
    ```powershell
    cd D:\sigap-jumbara\web
    powershell -ExecutionPolicy Bypass -File scripts\windows\mariadb-dev.ps1 -PasangService
    ```
    Service bernama `MariaDB1011dev`, start otomatis.
- Sandi root MariaDB laptop dibuat acak; sandi user `sigap` ada di `web\.env` (`DB_PASSWORD`). Sandi root perlu diganti/ditanyakan bila butuh (lihat catatan sesi di `PROGRES.md`).
- MariaDB XAMPP 10.4 di port 3306 tidak diubah.
- Menjalankan server pengembangan: **`jalankan.bat`** dari folder proyek (memeriksa semuanya, menyalakan MariaDB bila mati, lalu HTTPS di port `SIGAP_PORT`, bawaan 8585). Cara manual: `.venv\Scripts\python manage.py sigap_https_dev`.
- `jalankan.bat -Produksi -CekSaja` memeriksa kesiapan server produksi tanpa menyalakan server.
- Tes: `.venv\Scripts\pytest` (database `sigap_jumbara_test` dibuat otomatis).
