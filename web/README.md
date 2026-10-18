# web/ (aplikasi Django SIGAP JUMBARA)

Python 3.12 + Django 5.2 + MariaDB 10.5+. Pemasangan lengkap: `../docs/21-DEPLOY-WINDOWS.md`.

## Mulai cepat (laptop, PowerShell, dari folder ini)

```powershell
py -3.12 -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
copy .env.example .env          # lalu isi
powershell -ExecutionPolicy Bypass -File scripts\windows\unduh-alat.ps1
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py sigap_seed
powershell -ExecutionPolicy Bypass -File scripts\windows\bangun-css.ps1
.venv\Scripts\python manage.py runserver 0.0.0.0:8000
```

## Struktur

| Folder | Isi |
|---|---|
| `sigap/` | settings, urls, wsgi |
| `apps/inti/` | pengaturan, log aktivitas, soft delete, cadangan, middleware, perintah `sigap_seed`, `sigap_jadwal`, `sigap_cek_lingkungan` |
| `apps/akun/` | tiga akun, masuk/keluar, sesi mutlak 2 jam, ganti sandi |
| `apps/kontingen/` | kontingen dan kuota |
| `apps/biodata/` | form publik, NIK terenkripsi, foto, tanda, halaman superadmin, ekspor |
| `apps/kartu/`, `apps/absensi/`, `apps/anjangsana/` | tabel untuk Tahap 2-3 (halaman belum dibuat) |
| `templates/` | template Django (publik, akun, superadmin, galat) |
| `static/` | `css/app.css` (hasil Tailwind, di-commit), `js/`, `vendor/`, `fonts/`, `img/` |
| `tailwind/` | `input.css` + `tailwind.config.js` |
| `scripts/windows/` | `.ps1` pasang service, Task Scheduler, perbarui, bangun CSS, unduh alat; contoh vhost Apache |
| `tests/` | pytest |
| `privat/`, `logs/`, `staticfiles/`, `tools/*.exe` | dibuat saat jalan, tidak di-commit |

## Perintah

```powershell
.venv\Scripts\pytest                       # tes (database sigap_jumbara_test)
.venv\Scripts\ruff check . ; .venv\Scripts\ruff format .
.venv\Scripts\python manage.py sigap_cek_lingkungan
.venv\Scripts\python manage.py sigap_jadwal --paksa-cadangan
```
