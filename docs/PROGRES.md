# Progres Pengerjaan

Claude Code memperbarui file ini di akhir setiap sesi kerja: centang yang selesai, tulis apa yang sedang dikerjakan, kendala, dan langkah berikutnya. Farhan membaca file ini untuk tahu posisi proyek.

## Status singkat

- Tahap aktif: **Tahap 1 (Biodata dan superadmin)**. Kode selesai dan teruji di laptop; **tinggal pemasangan di server produksi + HTTPS + uji 3 HP** (dikerjakan Farhan, lihat "Yang harus dikerjakan Farhan").
- Revisi R1-R5 dari Farhan (tingkat dulu + cari sekolah, foto wajib dan dicetak di kartu, nama kapital, tanpa pencocokan NIK, pemotong foto responsif) **selesai** 18 Okt; lihat `docs/REVISI.md`.
- Terakhir diperbarui: 18 Oktober 2026
- Tenggat terdekat: **25 Oktober 2026** (form biodata siap), dibuka 26 Oktober 00.00 WITA

## Tahap 0: Fondasi
- [x] Django 5.2.18 di `web/` (virtualenv Python 3.12.10, `requirements.txt` + `requirements-dev.txt` terkunci), terhubung MariaDB 10.11.19 (port 3307)
- [x] Tailwind CLI standalone 3.4.17 + Alpine 3.14.9 + Cropper.js 1.6.2 + qr-scanner 1.4.2 + idb-keyval 6.2.1 di `static/vendor`, font Inter/Poppins lokal, tema oranye, logo PMI + Jumbara V
- [x] Migrasi awal semua tabel Tahap 1 + kerangka tabel Tahap 2-5 yang berelasi ke peserta
- [x] Seeder `sigap_seed` idempoten (3 akun, 29 kontingen, 13 kegiatan, 60 titik absen, 6 sesi Anjangsana, pengaturan)
- [x] `sigap_cek_lingkungan`
- [x] Git + commit

## Tahap 1: Biodata dan superadmin (25 Okt)
- [x] Form biodata publik sesuai `11-FORM-BIODATA.md`, diuji di Chrome lebar 360 px (mode pengembangan dan mode produksi Waitress). **Safari iPhone belum diuji** (butuh HP sungguhan lewat HTTPS)
- [x] Jadwal otomatis + hitung mundur + pesan tutup dengan WhatsApp; sakelar Otomatis/Paksa buka/Paksa tutup; jadwal bisa diubah
- [x] Validasi lengkap di server; NIK 16 angka unik (database)
- [x] Foto 3:4, 600x800, tanpa EXIF, folder privat, hanya lewat rute superadmin
- [x] Halaman bukti + kode pendaftaran + PDF bukti
- [x] Login tiga akun, sesi mutlak 2 jam, ingat menu terakhir dan saringan per perangkat, ganti sandi mengeluarkan semua perangkat
- [x] Superadmin: dasbor + QR link form, daftar (cari/saring/urut/halaman), detail (lihat NIK tercatat log), ubah, tambah manual, tempat sampah/pulihkan/hapus permanen, Excel umum + lengkap (konfirmasi sandi), ZIP foto per kontingen, kontingen dan kuota, pengaturan form, akun dan sandi, log aktivitas (+Excel), cadangan
- [x] Tanda otomatis: kuota penuh, tingkat beda (superadmin), usia tidak wajar, foto duplikat, nama mirip (pencocokan NIK dihapus, REVISI R4)
- [x] Log aktivitas untuk setiap perubahan
- [~] Cadangan harian: perintah `sigap_jadwal` + cadangan + pemulihan **sudah diuji**; pendaftaran Task Scheduler (`daftar-task-scheduler.ps1`) butuh Admin, **belum dijalankan**
- [x] Tes otomatis: 156 tes lulus (`pytest`), `ruff check` bersih
- [ ] Terpasang di server Windows produksi dengan HTTPS, diuji dari minimal 3 HP (Farhan)

## Tahap 2: Kartu dan QR kontingen (3 Nov)
Belum dimulai. Kolom `qr_token`, `kode_kartu`, `versi_kartu`, `kartu_aktif`, `perlu_cetak_ulang` dan tabel `kartu_riwayat` sudah ada.

## Tahap 3: Absensi, rekap, poin, Anjangsana (7 Nov)
Belum dimulai. Tabel `kegiatan`, `kuota_kegiatan`, `titik_absen` (60 baris terisi), `kehadiran` (UNIQUE aktif + `client_uuid`), `pindaian_ditolak`, sesi/kunjungan/review Anjangsana sudah ada. Halaman `/panitia/` dan `/juri/` masih "segera hadir".

## Tahap 4: Form builder dan juri (7 Nov)

## Tahap 5: Piagam (14 Nov)

## Yang harus dikerjakan Farhan

1. **Server produksi** (PC lain): ikuti `docs/21-DEPLOY-WINDOWS.md` bagian 1-7. Langkah yang butuh Admin dan belum bisa diuji Claude: memasang MSI MariaDB 10.11 sebagai service, `pasang-service.ps1`, `daftar-task-scheduler.ps1`, konfigurasi Apache vhost, Cloudflare Tunnel.
2. **Isi `web\.env` server** (bagian 3.1): `DJANGO_DEBUG=False`, kunci rahasia baru, domain di `DJANGO_ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`/`SIGAP_URL`, `DB_PASSWORD`, **kunci NIK baru** (jangan pakai kunci laptop), folder cadangan di disk lain, path `mariadb-dump.exe`, sandi awal 3 akun.
3. **Catat kunci NIK** (`SIGAP_KUNCI_NIK`, `SIGAP_KUNCI_HASH_NIK`) di tempat aman. Tanpa kunci, NIK tidak bisa dibaca dari database maupun cadangan.
4. **Tentukan domain final** dan aktifkan HTTPS (Cloudflare Tunnel disarankan).
5. **Ganti kata sandi tiga akun** dari menu Superadmin > Akun setelah login pertama.
6. **Isi nomor WhatsApp dan nama superadmin** di Superadmin > Pengaturan form; pastikan status **Otomatis** dan jadwal 26 Okt 00.00 - 2 Nov 23.59 WITA.
7. **Uji dari 3 HP** (Android murah, Android baru, iPhone Safari) lewat HTTPS sebelum 25 Okt: isi form lengkap dengan foto dari kamera dan galeri. Untuk uji sebelum 26 Okt pakai "Paksa buka", lalu kembalikan ke "Otomatis" dan hapus biodata uji.
8. **Uji pemulihan cadangan sekali di server** (bagian 10).
9. Laptop: MariaDB 10.11 pengembangan belum menjadi service (lihat bagian 13 dokumen deploy) dan perlu dinyalakan ulang setelah laptop restart. Sandi root-nya ada sebagai komentar di `web\.env` laptop.
10. Konfirmasi panitia: kuota SD Negeri 006 Tanjung Palas Utara (25 peserta inti, batas Mula 20).

## Catatan sesi

### 22 Oktober 2026 (Claude Code)

`runserver` gagal `(2002, "Can't connect to server on '127.0.0.1' (10061)")`: MariaDB 10.11 pengembangan (port 3307) mati karena belum menjadi service dan ikut mati saat sesi/laptop berhenti. Dinyalakan ulang. Ditambah `web/scripts/windows/mariadb-dev.ps1` (nyalakan, `-Status`, `-PasangService` sebagai Admin) dan petunjuk di `sigap_cek_lingkungan`. **Farhan disarankan menjalankan `-PasangService` sekali** agar tidak terulang.

### 18 Oktober 2026 (Claude Code, sesi 1 lanjutan: revisi R1-R3)

Perubahan manual Farhan (foto dicetak di kartu, teks SIAMO, teks nama kapital) di-commit terpisah. Dikerjakan R1 (tingkat dulu, sekolah disaring, server menolak tingkat beda), R2 (foto wajib mutlak, dokumen kartu berfoto), R3 (nama + nama orang tua kapital, migrasi data). 154 tes lulus, uji browser 360 px lulus. Catatan untuk Tahap 2: desain kartu B-2 sekarang memuat foto 3x4 (`13-KARTU-QR.md`).

### 18 Oktober 2026 (Claude Code, sesi 1: Tahap 0 + Tahap 1)

**Lingkungan laptop yang ditemukan:** Python 3.11.4 saja, Git 2.50, XAMPP dengan Apache dan MariaDB **10.4.32** berjalan sebagai service, MariaDB XAMPP berisi database proyek lain, `mysql` tidak ada di PATH.

**Tindakan:** (disetujui Farhan) Python 3.12.10 dipasang via winget. MariaDB 10.11.19 dipasang berdampingan di port 3307; pemasangan MSI sebagai service ditolak oleh sistem izin (butuh Admin), sehingga di laptop dipakai paket ZIP resmi (SHA256 diverifikasi) di `C:\Users\USER\sigap-mariadb` yang dijalankan manual. Database `sigap_jumbara` dan user `sigap` dibuat; database tes `sigap_jumbara_test` dibuat otomatis oleh pytest.

**Dikerjakan:** seluruh Tahap 0 dan kode Tahap 1 (lihat centang). Diuji: 151 tes otomatis; uji browser Chrome 360 px dan 1280 px (form lengkap dengan foto, ringkasan, bukti, isi untuk orang lain, login, dasbor, detail, lihat NIK, ubah, Excel, menu terakhir); mode produksi Waitress `DEBUG=False` + `collectstatic`; `check --deploy`; cadangan dan pemulihan ke database terpisah.

**Bug yang ditemukan dan diperbaiki saat pengujian:**
- Galat 500 saat sesi 2 jam habis (middleware sesi berjalan sebelum MessageMiddleware).
- Halaman form melebar 392 px di HP (input foto tersembunyi tetap `w-full`), membuat HP memperkecil tampilan.
- `collectstatic` gagal karena referensi `sourceMappingURL` di berkas vendor.
- Lencana tingkat tidak berwarna (kelas dinamis dibuang Tailwind) dan urutan kontingen Mula-Madya-Wira.

**Kendala/temuan dokumen:**
- `CLAUDE.md` menulis perintah Tailwind tanpa `-c tailwind\tailwind.config.js`; tanpa itu CSS keluar kosong. Sudah dikoreksi di `CLAUDE.md`.
- `20-TAMPILAN.md` menyebut `web/public/images/` untuk logo HANS PROJECT; di Django dipakai `web/static/img/`.
- Batas kiriman form per IP dibuat longgar (30 berhasil/10 menit) karena CGNAT operator seluler; lihat `IMPROVISASI.md`.

**Langkah berikutnya:** Farhan memasang di server produksi + HTTPS dan menguji dari 3 HP. Setelah Tahap 1 terpasang: buat data contoh 30 biodata palsu di database terpisah (prompt di `PROMPT_TAHAP_1.md`), lalu mulai Tahap 2 (kartu dan QR kontingen).
