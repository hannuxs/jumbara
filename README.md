# SIGAP JUMBARA

Sistem Informasi, Absensi, dan Penilaian untuk **Jumbara PMR Tingkat Kabupaten Bulungan V 2026**.
Dikembangkan oleh **Ahmad Farhan, HANS PROJECT**.

Folder ini adalah wadah proyek yang siap dibuka di VS Code dan dikerjakan oleh Claude Code. Kode aplikasinya belum ada; Claude Code yang akan membangunnya di folder `web/` dengan **Python (Django)** mengikuti spesifikasi di `docs/`.

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
| `web/` | Kosong. Aplikasi Python/Django akan dibuat di sini |

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
