# 21. Pemasangan di Server Windows + XAMPP (Python/Django)

Dokumen ini adalah kerangka. **Claude Code wajib melengkapinya** dengan langkah yang benar-benar diuji, termasuk perintah persis, path, dan pesan galat umum. Tulis untuk Farhan yang akan mengerjakannya sendiri.

Susunan di server:

```
HP/laptop -> HTTPS (Cloudflare Tunnel atau win-acme) -> Apache XAMPP :80/:443
          -> /static/  disajikan langsung oleh Apache dari web\staticfiles\
          -> selain itu diteruskan ke Waitress 127.0.0.1:8000 (Django, Windows Service)
          -> MariaDB 10.5+ (service)
```

## 1. Prasyarat di PC server dan laptop pengembangan

- **XAMPP** (Apache dipakai; PHP tidak dipakai). Pasang di `C:\xampp`.
- **MariaDB 10.5 atau lebih baru** (disarankan 10.11 LTS). Cek `mysql --version`; XAMPP lama membawa 10.4 yang tidak didukung Django 5.2. Lihat `02-ARSITEKTUR.md`.
- **Python 3.12** untuk Windows (centang "Add python.exe to PATH" dan "py launcher").
- **Git for Windows**.
- **Tailwind CSS standalone CLI** untuk Windows (`tailwindcss-windows-x64.exe`), disimpan di `web\tools\` (tidak di-commit jika besar; skrip unduh disediakan). Node.js tidak wajib.
- **WinSW** atau **NSSM** untuk menjadikan Waitress Windows Service.
- (Opsional) `cloudflared` untuk HTTPS opsi A.

## 2. Database

- Ganti kata sandi `root` MariaDB.
- Buat database `sigap_jumbara` (`utf8mb4_unicode_ci`), database tes `sigap_jumbara_test`, dan user khusus `sigap` dengan hak ke dua database itu (hak CREATE untuk database tes diperlukan pytest-django).
- `my.ini`: `max_connections=200`, `innodb_buffer_pool_size` sesuai RAM, `character-set-server=utf8mb4`, `collation-server=utf8mb4_unicode_ci`, `default-time-zone='+08:00'`, `sql_mode` mengandung `STRICT_TRANS_TABLES`.

## 3. Aplikasi

```
cd C:\sigap-jumbara\web
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      (lalu isi)
python manage.py check --deploy
python manage.py migrate
python manage.py sigap_seed          (akun, kontingen, kegiatan, titik absen, sesi Anjangsana, pengaturan; idempoten)
python manage.py collectstatic --noinput
python manage.py sigap_cek_lingkungan
```

Isi penting `.env`: `DJANGO_DEBUG=False`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `SIGAP_URL=https://sigapjumbara.<tld>`, `CSRF_TRUSTED_ORIGINS`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `SIGAP_FOLDER_PRIVAT`, `SIGAP_FOLDER_CADANGAN`, `SIGAP_MYSQLDUMP_PATH`, `SIGAP_SANDI_AWAL_SUPERADMIN`, `SIGAP_SANDI_AWAL_PANITIA`, `SIGAP_SANDI_AWAL_JURI`, `WAITRESS_THREADS`.

## 4. Waitress sebagai Windows Service

- `web\scripts\windows\pasang-service.ps1` membuat service "SIGAP Jumbara" dengan WinSW/NSSM yang menjalankan:
  `C:\sigap-jumbara\web\.venv\Scripts\waitress-serve.exe --listen=127.0.0.1:8000 --threads=48 --channel-timeout=120 sigap.wsgi:application`
- Start otomatis, restart otomatis jika mati, log ke `web\logs\`.
- Perintah memulai ulang setelah pembaruan: `Restart-Service "SIGAP Jumbara"`.

## 5. Apache XAMPP sebagai reverse proxy

- Aktifkan `mod_proxy`, `mod_proxy_http`, `mod_headers`, `mod_rewrite`, `mod_deflate`, `mod_expires` di `httpd.conf`.
- VirtualHost:
  - `Alias /static/ "C:/sigap-jumbara/web/staticfiles/"` dengan cache panjang.
  - `ProxyPass /static/ !`
  - `ProxyPass / http://127.0.0.1:8000/` dan `ProxyPassReverse / http://127.0.0.1:8000/`
  - `ProxyPreserveHost On`, `RequestHeader set X-Forwarded-Proto "https"` (jika HTTPS di depan).
  - `LimitRequestBody 12582912` (12 MB, untuk unggah foto).
- **Folder privat (foto) tidak boleh berada di bawah Alias/DocumentRoot.**
- `httpd-mpm.conf`: `ThreadsPerChild 250`.
- Apache dan MariaDB dijalankan **sebagai Windows Service** (XAMPP Control Panel > Service).

## 6. HTTPS (wajib karena kamera)

- **Opsi A (disarankan jika tidak ada IP publik tetap): Cloudflare Tunnel.** `cloudflared` sebagai service, hostname diarahkan ke `http://localhost:80` (Apache). HTTPS otomatis.
- **Opsi B: win-acme + Apache.** Domain mengarah ke IP publik server, port 80/443 diteruskan router ke PC server, sertifikat diperpanjang otomatis.
- Setelah HTTPS jalan: `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_SSL_REDIRECT` (hati-hati loop di balik tunnel), `CSRF_TRUSTED_ORIGINS` berisi domain.

## 7. Task Scheduler

- Tugas "SIGAP jadwal" setiap 1 menit: `C:\sigap-jumbara\web\.venv\Scripts\python.exe C:\sigap-jumbara\web\manage.py sigap_jadwal`, "Run whether user is logged on or not".
- Skrip `web\scripts\windows\daftar-task-scheduler.ps1` membuat tugas ini otomatis.

## 8. Kesiapan PC server selama acara

- Matikan sleep/hibernate, atur Windows Update agar tidak restart 25 Oktober sampai 16 November.
- Windows Defender Firewall: izinkan Apache (jika opsi B). Waitress hanya mendengar `127.0.0.1`.
- UPS bila ada.
- Cadangan disimpan ke disk lain atau disalin berkala ke penyimpanan awan.

## 9. Pembaruan aplikasi

```
cd C:\sigap-jumbara\web
git pull
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
Restart-Service "SIGAP Jumbara"
```

Hindari pembaruan besar di jam sibuk (form biodata dan 12-15 November). Sediakan mode perawatan sederhana (pengaturan `perawatan=aktif` yang menampilkan halaman "Sedang perbaikan sebentar" kecuali untuk superadmin).

## 10. Memulihkan cadangan

Langkah memulihkan dump SQL dan folder privat (foto). Uji sekali sebelum 25 Oktober.

## 11. Daftar periksa sebelum 25 Oktober

- [ ] MariaDB 10.5+ berjalan sebagai service.
- [ ] Service Waitress hidup otomatis setelah restart PC.
- [ ] HTTPS aktif dengan domain final.
- [ ] `python manage.py check --deploy` tanpa peringatan penting, `DJANGO_DEBUG=False`.
- [ ] Form biodata diuji dari Android murah, Android baru, iPhone.
- [ ] Cadangan otomatis menghasilkan file, dan pemulihan berhasil diuji.
- [ ] Kata sandi tiga akun sudah diganti dari bawaan.
- [ ] Jadwal buka 26 Okt 00.00 WITA dan tutup 2 Nov 23.59 WITA sudah benar di pengaturan.
- [ ] Nomor WhatsApp superadmin sudah diisi.
