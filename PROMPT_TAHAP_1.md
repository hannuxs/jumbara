# Prompt Tahap 0 + 1 (salin semua teks di dalam kotak ke Claude Code)

```
Halo. Kamu adalah pengembang utama proyek SIGAP JUMBARA. Bahasa pemrogramannya Python (Django), server produksi Windows + XAMPP. Sebelum menulis kode apa pun:

1. Baca CLAUDE.md, lalu docs/00-KEPUTUSAN.md, docs/01-TAHAPAN.md, docs/02-ARSITEKTUR.md, docs/03-DATA-MODEL.md, docs/10-AKUN-SESI.md, docs/11-FORM-BIODATA.md, docs/12-KONTINGEN.md, docs/19-LOG-KEAMANAN-PDP.md, docs/20-TAMPILAN.md, docs/21-DEPLOY-WINDOWS.md, docs/IMPROVISASI.md, data/README.md, dan assets/brand/README.md. Baca sekilas juga docs/13 sampai docs/18 supaya rancangan database tidak perlu dibongkar di tahap berikutnya.
2. Periksa lingkungan Windows saya: versi Python (py --list dan python --version), pip, Git, apakah Apache dan MariaDB XAMPP berjalan, dan versi MariaDB (mysql --version). Django 5.2 butuh MariaDB 10.5 atau lebih baru; jika XAMPP saya masih 10.4, jelaskan pilihan di docs/02-ARSITEKTUR.md, sarankan satu, dan beri langkah persisnya. Laporkan juga apa yang kurang (misalnya Python belum terpasang atau belum masuk PATH) beserta cara memperbaikinya. Jangan lanjut ke langkah yang butuh sesuatu yang belum siap.
3. Tuliskan rencana singkat Tahap 0 dan Tahap 1 (daftar langkah, urutan, perkiraan), termasuk keputusan teknis yang kamu ambil (versi paket yang dikunci, cara menyimpan NIK, struktur app Django, cara menyajikan statis) beserta alasannya. Setelah menulis rencana, LANGSUNG kerjakan tanpa menunggu persetujuan, kecuali ada hal yang benar-benar butuh keputusan saya; untuk itu tanyakan dengan asumsi dan pilihan.

Kerjakan Tahap 0 (fondasi) lalu Tahap 1 (form biodata publik + data kontingen + tiga akun + halaman superadmin) sampai semua kriteria selesai di docs/01-TAHAPAN.md terpenuhi. Hal penting:
- Aplikasi Django dibuat di folder web/ dengan virtualenv web\.venv dan requirements.txt yang dikunci. Di produksi dijalankan Waitress sebagai Windows Service di belakang Apache XAMPP.
- Tenggat: form biodata online dan teruji 25 Oktober 2026, dibuka 26 Oktober 2026 00.00 WITA, ditutup 2 November 2026 23.59 WITA.
- Dropdown utusan sekolah dari data/kontingen.csv. Jangan pakai data peserta per orang dari panitia.
- Logo PMI wajib tampil bersama logo Jumbara V (aturan di assets/brand/README.md).
- Semua teks Bahasa Indonesia, mobile first, tema oranye. Tailwind lewat CLI standalone, pustaka JS disimpan lokal di static/vendor (tanpa CDN).
- Kalau ada yang dibutuhkan tapi belum tertulis di dokumen, improvisasi sendiri dan catat di docs/IMPROVISASI.md.
- Commit git per langkah yang berfungsi. Jalankan pytest dan ruff. Periksa tampilan di lebar 360 px.
- Di akhir, perbarui docs/PROGRES.md, lengkapi docs/21-DEPLOY-WINDOWS.md dengan langkah yang sudah kamu uji (termasuk skrip .ps1 untuk memasang service Waitress dan Task Scheduler), dan buat daftar hal yang harus saya kerjakan sendiri (misalnya mengisi web\.env, memasang MariaDB baru jika perlu, mengaktifkan HTTPS, mengganti kata sandi).
```

## Setelah Tahap 1 berjalan

- Minta Claude Code: "Buat data contoh 30 biodata palsu di database terpisah untuk uji tampilan, lalu tunjukkan cara menghapusnya."
- Uji isi form dari beberapa HP lewat HTTPS sebelum 25 Oktober.
- Jika ada perubahan permintaan panitia, tulis dulu di `docs/00-KEPUTUSAN.md`, lalu minta Claude Code membaca ulang dan menyesuaikan.
