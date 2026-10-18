# 01. Tahapan Pengerjaan dan Kriteria Selesai

Hari ini (saat zip dibuat) adalah 18 Oktober 2026. Form biodata harus **sudah online dan diuji di HP sungguhan pada 25 Oktober 2026**, dibuka untuk umum 26 Oktober 2026. Ini satu-satunya tenggat yang tidak bisa mundur.

Kerjakan tahap secara berurutan. **Jangan mulai tahap berikutnya sebelum kriteria selesai tahap sebelumnya terpenuhi**, kecuali Farhan meminta. Tapi rancang database dari awal agar tahap berikutnya tidak perlu membongkar tabel yang sudah berisi data biodata asli.

## Tahap 0: Fondasi (target 19 Oktober)

- Django 5.2 di `web/` dengan virtualenv dan `requirements.txt` terkunci, terhubung ke MariaDB 10.5+ (cek versi MariaDB XAMPP dulu, lihat `02-ARSITEKTUR.md`), `web\.env.example` lengkap dengan penjelasan.
- Tailwind CSS (CLI standalone) + Alpine.js + pustaka JS di `static/vendor`, font lokal, tema oranye (lihat `20-TAMPILAN.md`), layout dasar HP dan laptop.
- Migrasi awal semua tabel Tahap 1 **dan** kerangka tabel tahap berikutnya yang memengaruhi biodata (misalnya kolom token QR di `peserta`). Lihat `03-DATA-MODEL.md`.
- Seeder: tiga akun (kata sandi awal dari `web\.env`, wajib diganti), kontingen dari `data/kontingen.csv`, kegiatan dari `data/kegiatan.csv`, titik absen dari `data/titik_absen.csv`, sesi Anjangsana dari `data/sesi_anjangsana.csv`, pengaturan bawaan.
- `python manage.py sigap_cek_lingkungan`.
- Git diinisialisasi, commit pertama.

## Tahap 1: Biodata dan superadmin (wajib selesai 25 Oktober)

Kriteria selesai:
- [ ] Halaman publik form biodata sesuai `11-FORM-BIODATA.md`, nyaman di HP layar 360 px, berjalan di Chrome Android dan Safari iPhone.
- [ ] Form otomatis tertutup di luar jadwal (sebelum buka: hitung mundur; setelah tutup: pesan dan kontak superadmin). Superadmin bisa membuka/menutup manual dan mengubah jadwal.
- [ ] Validasi lengkap di server (bukan hanya di browser). NIK 16 angka unik.
- [ ] Foto dipotong 3:4, dikecilkan, disimpan di folder privat, tidak bisa diakses publik.
- [ ] Halaman bukti pendaftaran dengan kode pendaftaran.
- [ ] Login tiga akun, sesi mutlak 2 jam, ingat menu terakhir per perangkat, ganti kata sandi mengeluarkan semua perangkat.
- [ ] Superadmin: dasbor progres per kontingen dan kuota, daftar biodata (cari, saring, urut), detail, ubah, hapus ke tempat sampah, pulihkan, unduh Excel (versi disamarkan dan versi lengkap), kelola kontingen dan kuota, pengaturan form, kelola kata sandi akun.
- [ ] Tanda (flag) otomatis: kuota penuh/terlampaui, tingkat beda dengan kontingen, NIK tidak cocok dengan tanggal lahir/jenis kelamin, usia tidak wajar untuk tingkat.
- [ ] Log aktivitas untuk setiap perubahan oleh superadmin.
- [ ] Cadangan database harian berjalan lewat Task Scheduler.
- [ ] Tes otomatis untuk validasi form, NIK unik, jadwal buka/tutup, hak akses.
- [ ] Terpasang di server Windows produksi dengan HTTPS. Diuji mengisi dari minimal 3 HP berbeda.

## Tahap 2: Kartu dan QR kontingen (3 November)

- [ ] Setiap biodata punya token QR acak dan kode pendek.
- [ ] PDF kartu B-2 per kontingen, 4 per F4, garis potong, sesuai `13-KARTU-QR.md`. Juga PDF satu orang (cetak ulang).
- [ ] Nonaktifkan kartu dan terbitkan token baru.
- [ ] PDF QR kontingen ukuran F4 per kontingen dan sekaligus semua.
- [ ] Kunci data biodata (superadmin) sebelum cetak; perubahan setelah dikunci dicatat dan ditandai "perlu cetak ulang".

## Tahap 3: Absensi, rekap, poin, Anjangsana (7 November)

- [ ] Halaman pemindai untuk akun panitia sesuai `14-ABSENSI.md`, termasuk antrean offline dan pemindaian bersamaan.
- [ ] Kelola titik absen (superadmin): buat, ubah, aktif/nonaktif, jadwal.
- [ ] Rekap per tingkat, kegiatan, sesi, kontingen, orang + unduh Excel (`15-REKAP-POIN.md`).
- [ ] Kuota per kegiatan per kontingen dan poin kehadiran otomatis.
- [ ] Anjangsana publik lengkap (`17-ANJANGSANA.md`).
- [ ] Uji beban lulus.

## Tahap 4: Form builder dan juri (7 November)

- [ ] Mode 1 dan mode 2 sesuai `16-FORM-BUILDER.md`.
- [ ] Mesin rumus aman dengan tes unit lengkap.
- [ ] Tarik data antarform, poin kehadiran otomatis, peringkat otomatis, kunci nilai.
- [ ] Akun juri: daftar form yang ditugaskan, isi nilai dengan Nama Juri, tidak bisa ubah setelah kirim.
- [ ] Template penilaian dari `data/template_penilaian.json` tersedia sebagai draf.

## Tahap 5: Piagam (14 November)

- [ ] Unggah template piagam, atur posisi teks, pratinjau.
- [ ] Piagam peserta untuk semua orang, piagam juara dari tabel hasil mode 2.
- [ ] Unduh per orang, per kontingen (satu PDF atau ZIP), dan semua.

## Setelah acara

- Laporan akhir (rekap kehadiran, hasil lomba, jumlah peserta) dalam Excel/PDF.
- Arsip atau hapus data pribadi sesuai kesepakatan dengan panitia (`19-LOG-KEAMANAN-PDP.md`).
