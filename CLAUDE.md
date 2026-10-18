# CLAUDE.md: SIGAP JUMBARA

Kamu (Claude Code) adalah pengembang utama aplikasi web **SIGAP JUMBARA** untuk **Jumbara PMR Tingkat Kabupaten Bulungan V 2026** (12-15 November 2026, Kebun Raya Bundayati, Tanjung Selor). Pemilik proyek: **Ahmad Farhan (HANS PROJECT)**. Klien: panitia Jumbara (PMI Kabupaten Bulungan).

## Baca dulu (urut)

1. `docs/00-KEPUTUSAN.md`: keputusan final. **Mengikat.** Jika ada konflik antardokumen, file ini yang benar.
2. `docs/01-TAHAPAN.md`: tahap, tenggat, kriteria selesai.
3. `docs/PROGRES.md`: posisi terakhir pekerjaan.
4. Spesifikasi modul yang sedang dikerjakan (`docs/10-...` sampai `docs/22-...`).
5. `docs/IMPROVISASI.md`: apa saja yang sudah ditambahkan di luar permintaan.

Referensi: `docs/JADWAL-ACARA.md`, `docs/referensi/` (Pedoman Jumbara V dan Jadwal Kegiatan PDF, plus teks pedoman), `data/` (data awal), `assets/brand/` (logo PMI, Jumbara V, HANS PROJECT + aturan pakai).

## Ringkasan produk

Web (bukan APK, bukan PWA yang dipasang) untuk:
1. **Form biodata publik** tanpa login (PRIORITAS: online dan teruji 25 Okt, dibuka 26 Okt-2 Nov 2026).
2. Data kontingen dan kuota (29 sekolah dari Google Form panitia).
3. Kartu peserta ber-QR ukuran B-2, 4 per F4, dan QR kontingen F4.
4. **Absensi QR oleh panitia dengan kamera HP. Banyak pemindai dan banyak titik absen harus bisa berjalan bersamaan** (catatan khusus panitia).
5. Rekap per tingkat (Mula, Madya, Wira), poin kehadiran.
6. Form builder mode 1 (input) dan mode 2 (penilaian dengan rumus, tarik data antarform, juri).
7. Anjangsana (link publik, pindai kartu sendiri, pindai QR tuan rumah, review).
8. Piagam peserta dan piagam juara (PDF).

## Lingkungan dan stack (tidak bisa ditawar)

- **Bahasa: Python** (keputusan Farhan). **Python 3.12 + Django 5.2 LTS**, Django Templates + Alpine.js + Tailwind CSS (CLI standalone, tanpa Node), MariaDB InnoDB `utf8mb4`.
- **Server produksi: Windows + XAMPP.** Apache XAMPP menjadi reverse proxy dan penyaji file statis; MariaDB sebagai database (wajib versi 10.5+, XAMPP lama membawa 10.4, cek di Tahap 0); PHP tidak dipakai. Django dijalankan oleh **Waitress** sebagai **Windows Service** (WinSW/NSSM) di `127.0.0.1:8000`.
- Aplikasi Django dibuat di folder **`web/`** dengan virtualenv `web\.venv`. Root repositori berisi dokumen dan data.
- Semua perintah dan skrip harus jalan di Windows (PowerShell/Git Bash/`python manage.py`). **Tidak ada** cron, systemd, supervisor, gunicorn, Celery, Redis, Docker, atau skrip khusus Linux. Penjadwal = Windows Task Scheduler + `python manage.py sigap_jadwal`.
- Semua aset (JS, CSS, font, pustaka pemindai QR, Cropper.js) **disimpan lokal** di `web/static/vendor` dan di-commit. Tidak ada CDN saat runtime.
- PDF dengan **ReportLab** (bukan WeasyPrint), gambar dengan **Pillow**, QR dengan **segno**, Excel dengan **XlsxWriter**, tes dengan **pytest-django**.
- Zona waktu **Asia/Makassar (WITA)** di Django (`TIME_ZONE`, `USE_TZ=True`) dan sesi MariaDB.
- Rincian dan daftar pustaka: `docs/02-ARSITEKTUR.md`. Pemasangan: `docs/21-DEPLOY-WINDOWS.md`.

## Aturan emas

1. **Tenggat 25 Oktober 2026 untuk Tahap 1 adalah yang terpenting.** Jangan mengerjakan fitur tahap lain sebelum Tahap 1 selesai dan terpasang, kecuali hal kecil yang mencegah bongkar ulang database nanti.
2. **Jangan memakai data peserta per orang dari panitia** (spreadsheet "Data Peserta Jumbara"). Satu-satunya data awal adalah `data/kontingen.csv` dan file lain di `data/`. Nama dan biodata diketik sendiri oleh setiap orang di form.
3. **Kebersamaan pemindai** dirancang dari awal: kunci UNIQUE di database, `client_uuid` idempoten, transaksi pendek, antrean offline di HP, polling untuk rekap. Lihat `docs/14-ABSENSI.md`.
4. **Data pribadi anak dilindungi** (UU 27/2022): NIK disamarkan, foto dan biodata lengkap hanya superadmin, foto disimpan di disk privat, tidak ada data orang lain di halaman publik. Lihat `docs/19-LOG-KEAMANAN-PDP.md`.
5. **Semua teks antarmuka dalam Bahasa Indonesia** yang sopan, singkat, mudah dipahami anak SD sampai guru. Mobile first. Tema oranye. **Logo PMI wajib tampil** berdampingan dengan logo Jumbara V (aturan di `assets/brand/README.md`).
6. Validasi selalu di server. Jangan percaya data dari browser.
7. **Jangan pernah memakai `eval`** atau sejenisnya untuk rumus form builder.
8. Jadwal, titik absen, kuota, sesi Anjangsana, jam buka form, kontak superadmin **disimpan di database dan bisa diubah superadmin**, tidak ditulis mati di kode.
9. Setiap aksi yang mengubah data dicatat di log aktivitas. Penghapusan memakai soft delete (tempat sampah).
10. Tulis tes otomatis untuk aturan penting (lihat `docs/22-PENGUJIAN.md`) dan jalankan sebelum commit besar.

## Improvisasi

- Farhan **mengizinkan dan meminta** kamu berimprovisasi: jika ada hal yang dibutuhkan tetapi belum disebut di dokumen (validasi, pesan galat, kasus tepi, kemudahan pakai, keamanan, operasional di Windows), **tambahkan sendiri**.
- Syarat: tidak bertentangan dengan `docs/00-KEPUTUSAN.md`, dan **setiap improvisasi dicatat** di `docs/IMPROVISASI.md` (tanggal, tahap, apa, alasan, cara mematikan).
- **Tanya Farhan dulu** hanya untuk keputusan yang tidak bisa dibatalkan atau mengubah alur yang sudah diputuskan (misalnya menghapus data asli, mengubah isian form biodata yang sudah dibuka, mengubah aturan penilaian). Untuk hal lain, pilih opsi paling masuk akal, kerjakan, dan catat asumsinya.
- Saat bertanya, sertakan **asumsi kamu dan beberapa pilihan beserta saran**, dalam Bahasa Indonesia.

## Cara kerja

- Kerjakan per tahap sesuai `docs/01-TAHAPAN.md`. Pecah menjadi langkah kecil, commit git per langkah yang berfungsi, pesan commit dalam Bahasa Indonesia yang jelas.
- Di akhir setiap sesi kerja: perbarui `docs/PROGRES.md` (centang, catatan sesi, langkah berikutnya, kendala) dan `docs/IMPROVISASI.md`.
- Setelah fitur selesai, **jalankan dan periksa sendiri**: `pytest` dan `ruff check`, buka halaman di browser (kecilkan ke lebar HP 360 px), uji kasus galat. Jangan menyatakan selesai sebelum diuji.
- Jika menemukan konflik atau kejanggalan di dokumen (misalnya jadwal berbeda), ikuti urutan prioritas: `00-KEPUTUSAN.md` > `JADWAL-ACARA.md` > dokumen modul > pedoman. Catat temuanmu di `PROGRES.md` bagian kendala.
- Kode: Django standar dan rapi, mengikuti struktur app di `docs/02-ARSITEKTUR.md`. View tipis, logika bisnis di `services.py`, validasi dengan Django Form, `TextChoices` untuk nilai tetap, decorator/middleware peran untuk hak akses. Type hints dan docstring singkat berbahasa Indonesia. Format dan lint dengan `ruff`. Nama domain dalam Bahasa Indonesia (Kontingen, Peserta, TitikAbsen, Kehadiran), konsisten.
- Jangan menaruh rahasia di repositori. `web\.env` tidak di-commit; `web\.env.example` lengkap dengan komentar Bahasa Indonesia.
- **Jangan pernah** menjalankan `flush`, `reset_db`, menghapus file migrasi yang sudah diterapkan, atau menghapus massal pada database yang berisi biodata asli (server produksi, atau database apa pun setelah 26 Oktober). Perubahan skema setelah ada data asli selalu lewat migrasi baru yang aman. Tes otomatis memakai database terpisah (`sigap_jumbara_test`).
- `git push`, `manage.py flush`, dan `sigap_anonimkan` sengaja diblokir di `.claude/settings.json`; Farhan yang menjalankannya.
- Jika butuh paket baru, pilih yang aktif dirawat, punya wheel untuk Windows, dan tidak butuh layanan tambahan (hindari Redis, Celery, WeasyPrint/GTK, uvloop). Kunci versi di `requirements.txt`.

## Perintah yang sering dipakai (Windows, dari folder `web`)

```
.venv\Scripts\activate
python manage.py runserver 0.0.0.0:8000
python manage.py makemigrations
python manage.py migrate
python manage.py sigap_seed
python manage.py sigap_cek_lingkungan
python manage.py sigap_jadwal --paksa-cadangan
pytest
ruff check . ; ruff format .
tools\tailwindcss.exe -c tailwind\tailwind.config.js -i tailwind\input.css -o static\css\app.css --watch    (pengembangan)
tools\tailwindcss.exe -c tailwind\tailwind.config.js -i tailwind\input.css -o static\css\app.css --minify   (produksi, commit hasilnya)
```

Untuk uji kamera di HP saat pengembangan, butuh HTTPS: pakai `cloudflared tunnel --url http://localhost:8000` (lihat `docs/21-DEPLOY-WINDOWS.md`).
