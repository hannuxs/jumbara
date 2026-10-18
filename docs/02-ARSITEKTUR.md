# 02. Arsitektur dan Stack (Python)

Keputusan Farhan (18 Oktober 2026): **bahasa pemrograman Python**. Server produksi tetap **PC Windows dengan XAMPP**.

## Lingkungan

- **Produksi:** PC/server **Windows** milik Farhan dengan **XAMPP**. Dari XAMPP yang dipakai: **Apache** (reverse proxy + file statis + HTTPS jika opsi win-acme) dan **MariaDB/MySQL** (database). PHP di XAMPP tidak dipakai.
- **Aplikasi Python** berjalan sebagai **Windows Service** (Waitress) di `127.0.0.1:8000`, Apache meneruskan permintaan ke sana.
- **Pengembangan:** laptop Windows Farhan, VS Code + Claude Code, Python + MariaDB XAMPP.
- **Semua perintah dan skrip harus jalan di Windows** (PowerShell atau Git Bash). Jangan menulis skrip khusus Linux (`.sh`, cron, systemd, supervisor, gunicorn, uWSGI, Docker). Jika butuh skrip, buat `.ps1`/`.bat` atau perintah `python manage.py ...`.

## Stack yang dipakai

| Lapisan | Pilihan | Catatan |
|---|---|---|
| Bahasa | **Python 3.12** (installer resmi Windows, centang "Add to PATH") | Virtualenv di `web\.venv` |
| Framework | **Django 5.2 LTS** | Auth, sesi, ORM, migrasi, form, CSRF, template, perintah manajemen. Cocok untuk tenggat yang sempit |
| Server aplikasi | **Waitress** (WSGI murni Python, jalan di Windows) | `waitress-serve --threads=48 --listen=127.0.0.1:8000 sigap.wsgi:application`. gunicorn tidak jalan di Windows |
| Layanan Windows | **WinSW** atau **NSSM** untuk menjalankan Waitress sebagai service yang hidup otomatis | Skrip pemasangan disediakan di `web\scripts\windows\` |
| Web server depan | **Apache XAMPP** sebagai reverse proxy (`mod_proxy`, `mod_proxy_http`, `mod_headers`) dan penyaji `/static/` | Alternatif: WhiteNoise menyajikan statis dari Django |
| Database | **MariaDB XAMPP**, InnoDB, `utf8mb4_unicode_ci` | Driver `mysqlclient` (ada wheel Windows). Lihat catatan versi di bawah |
| Template | **Django Templates + Alpine.js + Tailwind CSS** | Tanpa SPA berat; ringan untuk HP murah |
| CSS | **Tailwind CSS standalone CLI** (`tailwindcss.exe`, tanpa Node) | Hasil build `static/css/app.css` di-commit |
| Pustaka JS | `qr-scanner` (nimiq), `cropperjs`, `alpinejs`, `idb-keyval` (IndexedDB), ikon Lucide/Heroicons | **Diunduh sekali dan disimpan di `static/vendor/`** (di-commit, versi dicatat). Tidak ada CDN saat runtime. Node.js tidak wajib |
| Font | Poppins (judul) dan Inter (isi), file WOFF2 di-host sendiri di `static/fonts/` | Subset latin, bobot 400/500/600/700 |
| Gambar (foto 3x4) | **Pillow** (`ImageOps.exif_transpose`, crop, resize, simpan JPEG tanpa EXIF) | |
| Buat QR | **segno** (murni Python, SVG/PNG) | |
| PDF (kartu, QR kontingen, piagam, laporan) | **ReportLab** (murni Python, tata letak presisi dalam mm, cocok untuk F4 dan kartu B-2) | **Jangan WeasyPrint** (butuh GTK, sulit di Windows) |
| Excel | **XlsxWriter** (tulis cepat) atau openpyxl | Unduhan biodata dan rekap |
| Rumus form builder | **Parser sendiri** (tokenizer + recursive descent / shunting-yard) | **Dilarang `eval`/`exec`**, juga jangan `simpleeval` tanpa daftar putih ketat |
| Konfigurasi | `django-environ` atau `python-dotenv` membaca `web\.env` | |
| Rate limit | `django-ratelimit` dengan cache database Django | Cache LocMem tidak dibagi antarthread dengan aman untuk hitungan; pakai `DatabaseCache` |
| Tes | **pytest + pytest-django** | Database tes terpisah `sigap_jumbara_test` |
| Kualitas kode | `ruff` (lint + format) | |

`web\requirements.txt` berisi versi yang dikunci (`==`). Pakai `pip install -r requirements.txt` di virtualenv.

## Catatan versi MariaDB (penting, cek di Tahap 0)

- Django 5.2 membutuhkan **MariaDB 10.5 atau lebih baru**. XAMPP 8.2.x bawaan membawa **MariaDB 10.4**.
- Langkah Tahap 0: jalankan `mysql --version`. Jika masih 10.4, pilih salah satu dan catat di `docs/IMPROVISASI.md`:
  - **A (disarankan):** pasang **MariaDB 10.11 LTS** resmi untuk Windows sebagai service (port 3306), lalu matikan MySQL bawaan XAMPP. Apache XAMPP tetap dipakai.
  - **B:** ganti binari MariaDB di dalam folder XAMPP ke 10.11 (lebih rawan; buat cadangan dulu).
  - **C:** MySQL 8.0/8.4 untuk Windows (juga didukung Django).
- Jangan turun ke versi Django lama yang sudah tidak menerima pembaruan keamanan.

## Struktur folder repositori

```
sigap-jumbara/
├── CLAUDE.md                aturan kerja Claude Code (baca dulu)
├── README.md                panduan singkat untuk Farhan
├── PROMPT_TAHAP_1.md ...    prompt per tahap
├── docs/                    spesifikasi (sumber kebenaran)
├── data/                    data awal (kontingen, kegiatan, titik absen, template penilaian)
├── assets/brand/            logo PMI, logo Jumbara V, logo HANS PROJECT + aturan pakai
└── web/                     aplikasi Django (dibuat Claude Code di Tahap 0)
```

Usulan isi `web/` (boleh disesuaikan, catat jika berubah):

```
web/
├── manage.py
├── requirements.txt
├── .env.example
├── sigap/                 pengaturan proyek (settings, urls, wsgi)
├── apps/
│   ├── inti/              pengaturan aplikasi, log aktivitas, tempat sampah, cadangan, perintah umum
│   ├── akun/              tiga akun, login, sesi 2 jam, middleware peran
│   ├── kontingen/         kontingen, kuota
│   ├── biodata/           form publik, data peserta, foto, ekspor
│   ├── kartu/             token QR, PDF kartu, QR kontingen
│   ├── absensi/           kegiatan, titik absen, kehadiran, API pindai, rekap, poin
│   ├── anjangsana/        link publik, kunjungan, review, peringkat
│   ├── penilaian/         form builder mode 1/2, mesin rumus, juri
│   └── piagam/            template dan penerbitan piagam
├── templates/
├── static/                css (hasil Tailwind), js, vendor, fonts, images
├── tailwind/              input.css + tailwind.config.js untuk CLI standalone
├── scripts/windows/       .ps1/.bat: pasang service, Task Scheduler, build CSS
└── tests/
```

File privat (foto, unggahan form, cadangan) disimpan di folder di luar `static` dan di luar DocumentRoot Apache, misalnya `web\privat\` (path dari `.env`), dan hanya dilayani lewat view Django yang memeriksa login.

## Pola kode

- Django standar: model per app, logika bisnis di `services.py`, validasi di `forms.py` (Django Form/ModelForm) atau serializer sederhana untuk JSON, view tipis.
- Hak akses: decorator/mixin peran (`@peran_wajib("SUPERADMIN")`) + middleware. Admin bawaan Django (`/django-admin/`) boleh dipakai untuk darurat oleh superadmin saja, tapi **semua fitur utama dibuat sebagai halaman sendiri** yang ramah HP dan berbahasa Indonesia.
- `TextChoices` untuk nilai tetap: `Tingkat` (MULA, MADYA, WIRA), `Peran` (PESERTA, PIMPINAN_KONTINGEN, PEMBINA_PENDAMPING, PENINJAU), `JenisKelamin`, `GolonganDarah`, `StatusPindai`.
- `TIME_ZONE = "Asia/Makassar"`, `USE_TZ = True`, `LANGUAGE_CODE = "id"`. Atur zona waktu sesi MariaDB `+08:00` dan pastikan tabel zona waktu MariaDB terisi atau gunakan offset.
- Nama model dan field dalam Bahasa Indonesia untuk domain (`Kontingen`, `Peserta`, `TitikAbsen`, `Kehadiran`), konsisten.
- Semua teks yang dilihat pengguna dalam Bahasa Indonesia, termasuk pesan validasi.

## Kebersamaan (concurrency): wajib dipikirkan dari awal

Catatan panitia: pemindai harus bisa berjalan bersamaan. Jumat 13 November pukul 08.00 ada enam kegiatan serentak, dan banyak kegiatan dipecah per tingkat, jadi lebih dari 15 titik absen aktif dan puluhan HP memindai di waktu yang sama.

1. **Kunci unik di database** untuk mencegah dobel: `UniqueConstraint(titik_absen, peserta)` pada kehadiran aktif. Sisipkan di dalam `transaction.atomic()` dan tangkap `IntegrityError`, lalu kembalikan status kuning beserta jam dan nama pemindai pertama. Jangan memakai pola "cek dulu lalu insert" tanpa kunci unik.
2. **Idempoten:** setiap pindaian dari HP membawa `client_uuid` (UUID v4 dibuat di HP), kolom UNIQUE. Kiriman ulang dari antrean offline tidak membuat catatan baru.
3. **Transaksi pendek.** Endpoint pindai hanya membaca token kartu, memeriksa titik absen, dan menyisipkan satu baris. Target < 150 ms di server.
4. **Waitress multi-thread** (`--threads` 32-64). Pastikan kode thread-safe (tidak ada state global yang berubah). `CONN_MAX_AGE` sekitar 60 detik dan `CONN_HEALTH_CHECKS = True`.
5. **Endpoint pindai tidak menulis ke sesi** di setiap permintaan (hindari `SESSION_SAVE_EVERY_REQUEST`).
6. **Rekap diperbarui dengan polling** setiap 5 sampai 10 detik (tanpa WebSocket/Channels agar sederhana di Windows). Endpoint rekap ringan dan memakai indeks.
7. MariaDB: `max_connections` minimal 200, `innodb_buffer_pool_size` sesuai RAM (misalnya 1G), isolasi default (REPEATABLE READ) cukup asalkan kunci unik dipakai.
8. **Uji beban** sebelum 7 November: `python manage.py sigap_uji_beban` (atau skrip `httpx`/`asyncio` di `web\scripts\`) yang menyimulasikan 30 perangkat x 15 titik absen bersamaan, termasuk pindaian dobel yang disengaja. Hasil yang diharapkan: tidak ada catatan ganda, tidak ada error 500, waktu respons wajar.

## Tugas terjadwal di Windows

Tidak ada cron dan tidak ada Celery. Pakai **Windows Task Scheduler**:
- Setiap menit: `C:\sigap-jumbara\web\.venv\Scripts\python.exe C:\sigap-jumbara\web\manage.py sigap_jadwal` (satu perintah yang memeriksa dan menjalankan tugas yang jatuh tempo: cadangan harian, cadangan tiap 3 jam pada 12-15 November, bersih-bersih file sementara).
- Pembuatan PDF per kontingen dan Excel dilakukan **sinkron** saat diminta (ukurannya kecil). Untuk "semua kontingen sekaligus", buat ZIP secara bertahap dalam satu permintaan dengan batas waktu yang cukup, atau sediakan unduhan per kontingen.
- Sediakan `web\scripts\windows\daftar-task-scheduler.ps1`.

## HTTPS

Kamera di browser HP **hanya bisa dipakai lewat HTTPS** (atau localhost). Jadi produksi wajib HTTPS. Dua opsi didokumentasikan di `21-DEPLOY-WINDOWS.md`:

- **A. Cloudflare Tunnel (`cloudflared` sebagai Windows service):** tidak perlu membuka port router, HTTPS otomatis. Tunnel diarahkan ke Apache (`http://localhost:80`) atau langsung ke Waitress. Disarankan bila server tidak punya IP publik tetap.
- **B. Let's Encrypt lewat win-acme untuk Apache XAMPP:** butuh port 80/443 terbuka dan domain mengarah ke IP server.

Atur `SECURE_PROXY_SSL_HEADER`, `CSRF_TRUSTED_ORIGINS`, `ALLOWED_HOSTS`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` sesuai domain dari `.env`.

Untuk uji kamera di HP saat pengembangan: `cloudflared tunnel --url http://localhost:8000`.
