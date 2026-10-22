# SIGAP JUMBARA

Sistem Informasi, Absensi, dan Penilaian untuk **Jumbara PMR Tingkat Kabupaten Bulungan V 2026**.
Dikembangkan oleh **Ahmad Farhan, HANS PROJECT**.

Folder ini berisi dokumen proyek dan aplikasinya. Aplikasi **Python (Django)** ada di folder `web/`, dibangun oleh Claude Code mengikuti spesifikasi di `docs/`. Posisi pekerjaan terakhir: `docs/PROGRES.md`.

## Yang perlu dipasang dulu di laptop Windows

1. **XAMPP** di `C:\xampp`. Yang dipakai hanya **Apache** (meneruskan ke aplikasi Python dan menyajikan file statis) dan **MariaDB** (database). PHP tidak dipakai.
2. **MariaDB 10.5 atau lebih baru.** Cek dengan `mysql --version`. XAMPP lama membawa 10.4 yang tidak didukung Django 5.2; Claude Code akan memandu menggantinya (disarankan MariaDB 10.11 LTS).
3. **Python 3.12** untuk Windows dari python.org. Saat instalasi centang **"Add python.exe to PATH"**.
4. **Git for Windows**.
5. **VS Code** dan **Claude Code** (ekstensi VS Code atau versi terminal), plus ekstensi Python.
6. Tambahkan `C:\xampp\mysql\bin` ke PATH Windows, lalu buka ulang VS Code.

Node.js tidak wajib. Tailwind CSS memakai program standalone yang akan diunduh Claude Code.

## Cara mulai

1. Ekstrak zip ini, misalnya ke `C:\sigap-jumbara`. Sebaiknya **bukan** di dalam `C:\xampp\htdocs`; Apache nanti hanya meneruskan permintaan ke aplikasi Python.
2. Buka folder `sigap-jumbara` di VS Code (File > Open Folder).
3. Buka Claude Code di folder itu.
4. Buka `PROMPT_TAHAP_1.md`, salin teks di dalam kotak, tempel ke Claude Code, lalu kirim.
5. Claude Code akan memeriksa laptop Anda, menulis rencana, lalu mulai bekerja. Jawab jika ia bertanya. Pantau `docs/PROGRES.md` untuk melihat kemajuan.
6. Setelah Tahap 1 selesai, pakai prompt berikutnya di `PROMPT_TAHAP_2-5.md` satu per satu.

## Menjalankan di laptop (satu perintah)

Dari folder proyek (`D:\sigap-jumbara`), klik dua kali **`jalankan.bat`** atau ketik di terminal:

```
jalankan.bat
```

Perintah ini memeriksa semuanya lalu menjalankan server:
1. Python 3.12 dan virtualenv `web\.venv` (dibuat bila belum ada), paket `requirements` (dipasang ulang bila berubah).
2. `web\.env` ada dan isian wajibnya terisi.
3. **MariaDB menyala** (dinyalakan otomatis bila mati) dan bisa dimasuki, versi 10.5+.
4. Migrasi database, tabel cache, data awal (`sigap_seed`, aman diulang).
5. CSS Tailwind dibangun ulang; `collectstatic` bila `DJANGO_DEBUG=False`.
6. `manage.py check` dan `sigap_cek_lingkungan` (laporan lengkap: kunci NIK, folder, akun, jadwal form).
7. Port bebas, alamat untuk laptop dan HP (IP Wi-Fi harus ada di `DJANGO_ALLOWED_HOSTS`).

Pilihan:

| Perintah | Fungsi |
|---|---|
| `jalankan.bat` | Periksa semua lalu jalankan server pengembangan di port 8000 |
| `jalankan.bat -CekSaja` | Hanya periksa, tidak menjalankan server |
| `jalankan.bat -Port 8080` | Pakai port lain |
| `jalankan.bat -Produksi` | Jalankan dengan Waitress (seperti di server) |
| `jalankan.bat -Tes` | Jalankan juga `ruff` dan `pytest` sebelum server |
| `jalankan.bat -Https` | Server uji dengan HTTPS sementara di port 8443, agar **kamera HP** bisa diuji |

Tanda `[OK]` = beres, `[!]` = peringatan (server tetap jalan), `[X]` = harus diperbaiki (ada baris "Solusi"). Hentikan server dengan **Ctrl+C**. Dari HP (Wi-Fi yang sama) buka **http://IP-laptop:8000**; untuk kamera (pemindai, Anjangsana) pakai `jalankan.bat -Https` lalu buka **https://IP-laptop:8443** dan terima peringatan sertifikat (Chrome: Lanjutan > Lanjutkan; Safari: Tampilkan Detail > kunjungi situs web ini).

## Daftar semua perintah

Kecuali `jalankan.bat`, semua perintah dijalankan dari folder **`web`** di terminal (PowerShell atau Git Bash). Aktifkan virtualenv dulu:

```
cd D:\sigap-jumbara\web
.venv\Scripts\activate
```

Perintah yang ditandai **(Admin)** harus dijalankan di PowerShell "Run as Administrator".

### Menjalankan server

| Perintah | Fungsi |
|---|---|
| `jalankan.bat` (dari folder proyek) | Cek menyeluruh lalu jalankan server (lihat pilihan di atas) |
| `python manage.py runserver 0.0.0.0:8000` | Server pengembangan saja, tanpa pemeriksaan |
| `python manage.py sigap_https_dev` | Server uji HTTPS di port 8443 (sertifikat buatan sendiri, dibuat otomatis). Bisa diberi alamat lain: `sigap_https_dev 0.0.0.0:9443`. **Hanya untuk uji**, bukan produksi |
| `.venv\Scripts\waitress-serve.exe --listen=0.0.0.0:8000 --threads=48 sigap.wsgi:application` | Waitress seperti di server produksi |

### Database dan data awal

| Perintah | Fungsi |
|---|---|
| `powershell -ExecutionPolicy Bypass -File scripts\windows\mariadb-dev.ps1` | Nyalakan MariaDB pengembangan laptop (port 3307) |
| `... mariadb-dev.ps1 -Status` | Cek MariaDB laptop menyala atau tidak |
| `... mariadb-dev.ps1 -PasangService` **(Admin)** | Jadikan MariaDB laptop Windows Service (menyala otomatis setelah restart). Cukup sekali |
| `python manage.py migrate` | Terapkan perubahan struktur database |
| `python manage.py makemigrations` | Buat file migrasi setelah model diubah (pengembang) |
| `python manage.py createcachetable` | Buat tabel cache (pembatas percobaan login) |
| `python manage.py sigap_seed` | Isi data awal dari folder `data/`: 3 akun, 29 kontingen, kegiatan, 60 titik absen, sesi Anjangsana, pengaturan. **Aman diulang**, tidak menimpa data yang sudah ada. Pilihan: `--folder-data <folder>` |

### Akun dan kata sandi

| Perintah | Fungsi |
|---|---|
| `python manage.py sigap_atur_sandi superadmin` | Setel ulang sandi satu akun (`superadmin`, `panitia`, atau `juri`). Sandi diketik dua kali dan tidak tampil di layar |
| `python manage.py sigap_atur_sandi --semua --dari-env` | Setel sandi ketiga akun sesuai `SIGAP_SANDI_AWAL_*` di `web\.env` |

Penting: sandi di `web\.env` **hanya dipakai saat akun pertama kali dibuat** oleh `sigap_seed`. Mengubah `.env` sesudahnya tidak mengubah sandi; pakai `sigap_atur_sandi`. Setelah disetel ulang, akun wajib mengganti sandi saat masuk, dan semua perangkat yang memakai akun itu dikeluarkan. Sandi juga bisa diganti dari menu **Superadmin > Akun dan kata sandi**.

### Pemeriksaan, jadwal, dan cadangan

| Perintah | Fungsi |
|---|---|
| `python manage.py sigap_cek_lingkungan` | Laporan kesiapan: database, kunci NIK, folder privat/cadangan, akun dan sandi bawaan, jadwal form, WhatsApp superadmin |
| `python manage.py check --deploy` | Pemeriksaan keamanan Django untuk produksi |
| `python manage.py sigap_jadwal` | Tugas berkala: cadangan harian 02.00 WITA, cadangan tiap 3 jam saat acara, bersih-bersih sesi (dijalankan Task Scheduler tiap menit) |
| `python manage.py sigap_jadwal --paksa-cadangan` | Buat cadangan database sekarang juga |
| `powershell -ExecutionPolicy Bypass -File scripts\windows\daftar-task-scheduler.ps1` **(Admin)** | Daftarkan tugas "SIGAP jadwal" di Task Scheduler. Copot dengan `-Hapus` |

Memulihkan cadangan: ikuti `docs/21-DEPLOY-WINDOWS.md` bagian 10.

### Uji

| Perintah | Fungsi |
|---|---|
| `pytest` | Semua tes otomatis (memakai database terpisah `sigap_jumbara_test`) |
| `pytest tests/test_absensi.py -q` | Tes satu file saja |
| `ruff check .` | Periksa kerapian dan kesalahan kode |
| `ruff format .` | Rapikan format kode |
| `python manage.py sigap_uji_beban --url http://127.0.0.1:8000 --ya` | Uji beban absensi: 30 HP x 15 titik memindai bersamaan ke server yang sedang berjalan, lalu periksa tidak ada data dobel. Data uji dihapus otomatis. **Jangan dijalankan saat acara berlangsung** |

Pilihan `sigap_uji_beban`: `--perangkat 30`, `--titik 15`, `--pindaian 40`, `--jeda 0.5` (detik), `--dobel 0.10`, `--ulang 0.05`, `--simpan-data` (data uji tidak dihapus), `--ya` (wajib bila `DJANGO_DEBUG=False`). Hasil yang benar: "Uji beban LULUS" dengan 0 pasangan ganda.

### Tampilan (CSS) dan file statis

| Perintah | Fungsi |
|---|---|
| `tools\tailwindcss.exe -c tailwind\tailwind.config.js -i tailwind\input.css -o static\css\app.css --minify` | Bangun CSS sekali (versi produksi, commit hasilnya) |
| `tools\tailwindcss.exe -c tailwind\tailwind.config.js -i tailwind\input.css -o static\css\app.css --watch` | Bangun CSS otomatis setiap template diubah (pengembangan) |
| `powershell -ExecutionPolicy Bypass -File scripts\windows\bangun-css.ps1` | Sama dengan `--minify` di atas. Tambah `-Pantau` untuk mode otomatis |
| `python manage.py collectstatic --noinput` | Kumpulkan file statis ke `staticfiles` (wajib bila `DJANGO_DEBUG=False`) |
| `powershell -ExecutionPolicy Bypass -File scripts\windows\unduh-alat.ps1` | Unduh Tailwind CLI dan WinSW ke `web\tools` (tidak ikut di-commit) |

### Server produksi (Windows + XAMPP)

Urutan lengkap ada di `docs/21-DEPLOY-WINDOWS.md`.

| Perintah | Fungsi |
|---|---|
| `powershell -ExecutionPolicy Bypass -File scripts\windows\pasang-service.ps1` **(Admin)** | Pasang Waitress sebagai Windows Service (WinSW). Pilihan: `-Threads 48`, `-Port 8000`, `-Hapus` (copot service) |
| `powershell -ExecutionPolicy Bypass -File scripts\windows\perbarui.ps1` **(Admin)** | Perbarui aplikasi setelah ada perubahan kode (paket, migrasi, tabel cache, file statis, lalu restart service). Hindari jam sibuk |
| `scripts\windows\apache-sigap.conf` | Contoh konfigurasi Apache XAMPP sebagai reverse proxy (bukan perintah, disalin ke konfigurasi Apache) |

### Sengaja tidak dijalankan Claude Code

`git push`, `python manage.py flush`, dan `sigap_anonimkan` diblokir untuk Claude Code; Farhan yang menjalankannya sendiri. **Jangan pernah** menjalankan `flush` pada database yang berisi biodata asli.

## Isi folder

| Folder/File | Isi |
|---|---|
| `CLAUDE.md` | Aturan kerja yang otomatis dibaca Claude Code setiap sesi |
| `PROMPT_TAHAP_1.md`, `PROMPT_TAHAP_2-5.md` | Prompt yang Anda tempel ke Claude Code |
| `docs/00-KEPUTUSAN.md` | Semua keputusan final dengan panitia. **Ubah file ini dulu** jika ada perubahan permintaan |
| `docs/01` sampai `docs/22` | Spesifikasi lengkap per bagian |
| `docs/JADWAL-ACARA.md` | Jadwal dari PDF panitia, titik absen, dan kegiatan yang berjalan bersamaan |
| `docs/IMPROVISASI.md` | Daftar tambahan di luar permintaan (diisi juga oleh Claude Code). Periksa berkala |
| `docs/PROGRES.md` | Posisi pekerjaan, diperbarui Claude Code setiap sesi |
| `docs/referensi/` | Pedoman Jumbara V dan Jadwal Kegiatan (PDF asli) |
| `data/` | Data awal: 29 kontingen dari Google Form, kegiatan, 60 titik absen, sesi Anjangsana, contoh form penilaian |
| `assets/brand/` | Logo PMI (wajib tampil), logo Jumbara V, logo HANS PROJECT, dan aturan pakainya |
| `web/` | Aplikasi Python/Django (kode, template, tes, `scripts\windows\` untuk perintah Windows) |
| `jalankan.bat` | Satu perintah untuk cek kesiapan dan menjalankan server |

## Tenggat penting

| Tanggal | Hal |
|---|---|
| **25 Okt 2026** | Form biodata online di server Windows dengan HTTPS dan sudah diuji di HP |
| **26 Okt-2 Nov** | Form biodata dibuka |
| 3 Nov | Kartu dan QR kontingen siap cetak |
| 7 Nov | Absensi, rekap, Anjangsana, form penilaian siap; uji coba 7-8 Nov |
| 10 Nov | Pelatihan panitia dan juri |
| 12-15 Nov | Jumbara V |

## Yang masih ditunggu dari panitia

- Kuota peserta per kegiatan per kontingen (31 Okt). Sementara memakai angka pedoman.
- Jadwal final per jam jika ada perubahan dari PDF (31 Okt).
- Aspek dan bobot penilaian final setiap lomba (5 Nov). Bobot Got Talent di pedoman tidak lengkap.
- Template piagam serta nama dan jabatan penanda tangan (5 Nov).
- Konfirmasi peserta inti SD Negeri 006 Tanjung Palas Utara (25, batas Mula 20).
- Nama domain final `sigapjumbara.<tld>`.

## Catatan keamanan

Jangan unggah folder ini ke repositori publik setelah ada data asli. File `web\.env`, folder privat foto, dan cadangan database berisi data pribadi anak.
