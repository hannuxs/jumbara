# 21. Pemasangan di Server Windows + XAMPP (Python/Django)

Panduan untuk Farhan memasang SIGAP JUMBARA di PC server Windows. Ditulis dan diuji oleh Claude Code pada 18 Oktober 2026 di laptop pengembangan (Windows 10 Pro, XAMPP dengan MariaDB 10.4, Python 3.12.10). Bagian yang **butuh hak Administrator** (memasang service, Task Scheduler, MSI MariaDB) sudah diperiksa sintaksnya tetapi belum dijalankan oleh Claude karena hak admin diblokir; ditandai **(belum diuji, jalankan sendiri)**.

Susunan di server:

```
HP/laptop -> HTTPS (Cloudflare Tunnel) -> Apache XAMPP :80
          -> /static/  disajikan langsung oleh Apache dari web\staticfiles\
          -> selain itu diteruskan ke Waitress 127.0.0.1:8000 (Django, Windows Service "SIGAP Jumbara")
          -> MariaDB 10.11 (Windows Service "MariaDB1011")
```

Semua perintah di bawah dijalankan di **PowerShell**. Yang bertanda **(Admin)** harus di PowerShell "Run as Administrator".

---

## 1. Prasyarat

| Program | Cara pasang | Cek |
|---|---|---|
| XAMPP (Apache) | Sudah ada di `C:\xampp`. PHP tidak dipakai | Apache jalan di XAMPP Control Panel |
| Python 3.12 | `winget install --id Python.Python.3.12 --scope user` (atau installer python.org, centang "Add to PATH" dan "py launcher") | `py --list` menampilkan `-V:3.12` |
| Git for Windows | `winget install --id Git.Git` | `git --version` |
| MariaDB 10.11 LTS | Lihat bagian 2 | `mysql --version` atau `mariadb --version` |
| cloudflared (HTTPS) | `winget install --id Cloudflare.cloudflared` | `cloudflared --version` |

Node.js **tidak** diperlukan. Tailwind CLI dan WinSW diunduh oleh skrip (bagian 3).

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
powershell -ExecutionPolicy Bypass -File scripts\windows\unduh-alat.ps1     # tailwindcss.exe + WinSW
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

`check --deploy` normal menyisakan 2 peringatan: `security.W004` (HSTS, aktifkan setelah domain final) dan `security.W008` (pengalihan HTTPS dilakukan Cloudflare).

### 3.1 Isi `web\.env` di server

| Kunci | Nilai produksi |
|---|---|
| `DJANGO_DEBUG` | `False` |
| `DJANGO_SECRET_KEY` | acak: `.venv\Scripts\python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `DJANGO_ALLOWED_HOSTS` | `sigapjumbara.<tld>,localhost,127.0.0.1` |
| `CSRF_TRUSTED_ORIGINS` | `https://sigapjumbara.<tld>` |
| `SIGAP_URL` | `https://sigapjumbara.<tld>` |
| `SIGAP_HTTPS` | `True` |
| `DB_PORT` | `3307` (atau `3306`) |
| `DB_PASSWORD` | sandi user `sigap` |
| `SIGAP_KUNCI_NIK` | `.venv\Scripts\python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `SIGAP_KUNCI_HASH_NIK` | `.venv\Scripts\python -c "import secrets; print(secrets.token_hex(32))"` |
| `SIGAP_FOLDER_PRIVAT` | `C:\sigap-jumbara\web\privat` |
| `SIGAP_FOLDER_CADANGAN` | disk lain, misalnya `D:\cadangan-sigap` |
| `SIGAP_MYSQLDUMP_PATH` | `C:\Program Files\MariaDB 10.11\bin\mariadb-dump.exe` |
| `SIGAP_SANDI_AWAL_*` | sandi awal 3 akun (min. 10 karakter), lalu segera diganti dari menu Akun |

**Penting:** `SIGAP_KUNCI_NIK` dan `SIGAP_KUNCI_HASH_NIK` wajib dicatat di tempat aman (pengelola sandi + flashdisk). Tanpa kunci ini, NIK di database dan di cadangan tidak bisa dibaca lagi. Jangan pernah mengganti `SIGAP_KUNCI_HASH_NIK` setelah ada data.

## 4. Waitress sebagai Windows Service (Admin) (belum diuji, jalankan sendiri)

```powershell
cd C:\sigap-jumbara\web
powershell -ExecutionPolicy Bypass -File scripts\windows\pasang-service.ps1
```

Skrip membuat service **"SIGAP Jumbara"** (id `SIGAPJumbara`) lewat WinSW yang menjalankan:
`.venv\Scripts\waitress-serve.exe --listen=127.0.0.1:8000 --threads=48 --channel-timeout=120 --connection-limit=1000 sigap.wsgi:application`
— start otomatis (tertunda), restart otomatis bila mati, bergantung pada service `MariaDB1011`, log di `web\logs\`. Di akhir skrip mencoba membuka `http://127.0.0.1:8000/`.

Yang sudah diuji Claude: perintah Waitress di atas (mode produksi, `DJANGO_DEBUG=False`) menjawab 200 untuk `/`, `/daftar/`, `/masuk/`, 404 ramah untuk halaman tidak ada, header keamanan lengkap; dan file XML WinSW yang dibuat skrip terbaca benar (`status` → `NonExistent`).

Perintah sehari-hari: `Restart-Service SIGAPJumbara`, `Get-Service SIGAPJumbara`. Mencopot: `pasang-service.ps1 -Hapus`.

## 5. Apache XAMPP sebagai reverse proxy

1. Buka `C:\xampp\apache\conf\httpd.conf`, pastikan baris `LoadModule` untuk `proxy`, `proxy_http`, `headers`, `rewrite`, `deflate`, `expires` tidak diberi `#`.
2. Salin isi `web\scripts\windows\apache-sigap.conf` ke akhir `C:\xampp\apache\conf\extra\httpd-vhosts.conf`. Ganti `ServerName` dengan domain final dan path jika folder proyek bukan `C:\sigap-jumbara`.
3. `C:\xampp\apache\conf\extra\httpd-mpm.conf` bagian `mpm_winnt_module`: `ThreadsPerChild 250`.
4. Cek: `C:\xampp\apache\bin\httpd.exe -t` harus `Syntax OK`, lalu restart Apache (XAMPP Control Panel atau `Restart-Service Apache2.4`).
5. Pastikan Apache dan MariaDB berjalan sebagai **service** (XAMPP Control Panel, kolom "Service").

Apache hanya menyajikan `web\staticfiles\`. Folder `web\privat\` (foto, cadangan) dan `web\.env` tidak berada di bawah Alias mana pun. Selain itu, aplikasi juga memakai WhiteNoise sehingga `/static/` tetap tersaji jika diakses langsung lewat Waitress.

## 6. HTTPS

**Keputusan Farhan (22 Okt 2026): Cloudflare Tunnel tidak dipakai.** HTTPS tetap wajib untuk kamera HP (pemindai Tahap 3, Anjangsana). Cara HTTPS ditentukan saat pemasangan; pilihan yang tersedia adalah opsi B (win-acme + Apache) di bawah. Uraian Cloudflare Tunnel dibiarkan sebagai referensi saja.

### (Referensi, tidak dipakai) Cloudflare Tunnel

Kamera HP hanya bisa dipakai lewat HTTPS. Syarat: domain `sigapjumbara.<tld>` memakai nameserver Cloudflare (akun Cloudflare gratis).

1. Cloudflare dashboard > **Zero Trust** > Networks > Tunnels > **Create a tunnel** (Cloudflared), nama `sigap-jumbara`.
2. Pilih Windows, salin perintah yang berisi token, jalankan di PowerShell **(Admin)**:
   `cloudflared.exe service install <TOKEN>` — cloudflared menjadi Windows service dan hidup otomatis.
3. Tab **Public Hostname**: hostname `sigapjumbara.<tld>` (dan `www` jika perlu), service `HTTP` → `localhost:80` (Apache).
4. SSL/TLS > Edge Certificates: aktifkan **Always Use HTTPS**.
5. Isi `.env`: `SIGAP_URL`, `DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` (bagian 3.1), `SIGAP_HTTPS=True`, `SECURE_SSL_REDIRECT=False`. `Restart-Service SIGAPJumbara`.
6. Setelah stabil dan domain final: `SECURE_HSTS_SECONDS=31536000`.

Opsi B (win-acme + Apache :443) hanya jika server punya IP publik tetap dan port 80/443 diteruskan router; tidak disarankan untuk tenggat ini.

**Uji kamera di HP saat pengembangan:** `cloudflared tunnel --url http://localhost:8000` lalu buka alamat `https://....trycloudflare.com` yang muncul (`.env` laptop sudah mengizinkan `*.trycloudflare.com`).

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
- Firewall: tidak perlu membuka port masuk (Cloudflare Tunnel keluar sendiri). Waitress hanya mendengar `127.0.0.1`.
- UPS bila ada. Salin cadangan berkala ke disk lain/penyimpanan awan milik panitia.

## 9. Pembaruan aplikasi

**(Admin)** dari `C:\sigap-jumbara\web`:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows\perbarui.ps1
```
Urutannya: cadangan dulu → `git pull` → `pip install` → `migrate` → `collectstatic` → restart service → `sigap_cek_lingkungan`. Hindari jam sibuk. Untuk perbaikan yang lama, nyalakan **Mode perawatan** di Superadmin > Pengaturan form (semua halaman menampilkan "Sedang perbaikan sebentar", kecuali untuk superadmin).

## 10. Memulihkan cadangan (sudah diuji ke database terpisah)

1. Hentikan aplikasi: `Stop-Service SIGAPJumbara`.
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
6. `Start-Service SIGAPJumbara`, lalu `python manage.py sigap_cek_lingkungan`.

Hasil uji 18 Okt 2026: cadangan dipulihkan ke database `sigap_uji_pulih`; jumlah biodata dan kontingen sama dengan aslinya, foto ada.

## 11. Daftar periksa sebelum 25 Oktober

- [ ] MariaDB 10.11 berjalan sebagai service `MariaDB1011` dan hidup otomatis setelah restart PC.
- [ ] Service `SIGAPJumbara` hidup otomatis setelah restart PC.
- [ ] HTTPS aktif dengan domain final (cara ditentukan saat pemasangan; Cloudflare Tunnel tidak dipakai).
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
| Foto 413/terlalu besar di Apache | `LimitRequestBody` di vhost (bawaan contoh: 12 MB) |

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
- Menjalankan server pengembangan: **`jalankan.bat`** dari folder proyek (memeriksa semuanya, menyalakan MariaDB bila mati, lalu `runserver 0.0.0.0:8000`). Cara manual: `.venv\Scripts\python manage.py runserver 0.0.0.0:8000`.
- `jalankan.bat -CekSaja -Produksi` juga berguna di server produksi untuk memeriksa kesiapan (tanpa menyalakan server, karena di server dipakai service `SIGAPJumbara`).
- Tes: `.venv\Scripts\pytest` (database `sigap_jumbara_test` dibuat otomatis).
