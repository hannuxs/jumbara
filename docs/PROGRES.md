# Progres Pengerjaan

Claude Code memperbarui file ini di akhir setiap sesi kerja: centang yang selesai, tulis apa yang sedang dikerjakan, kendala, dan langkah berikutnya. Farhan membaca file ini untuk tahu posisi proyek.

## Status singkat

- Tahap aktif: **Tahap 4 selesai di laptop (23 Okt), berikutnya Tahap 5** (piagam). Tahap 3 selesai 22 Okt. Tahap 2 selesai 22 Okt. Tahap 1 selesai di laptop; pemasangan di server produksi + HTTPS + uji 3 HP dikerjakan paling akhir bersama Farhan (keputusan Farhan 22 Okt; lihat "Yang harus dikerjakan Farhan").
- Revisi R1-R5 dari Farhan (tingkat dulu + cari sekolah, foto wajib dan dicetak di kartu, nama kapital, tanpa pencocokan NIK, pemotong foto responsif) **selesai** 18 Okt; lihat `docs/REVISI.md`.
- Terakhir diperbarui: 23 Oktober 2026
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
- [x] Token QR acak (SJP:, sekitar 128,8 bit) dan kode kartu 8 karakter; dibuat saat biodata masuk, diisi massal lewat migrasi `kartu.0002_isi_token`
- [x] PDF kartu B-2 dengan **foto + QR** (R2/R6), 4 per F4, garis potong, sampul daftar nama; per kontingen, satu orang, hanya cetak ulang, ZIP semua
- [x] Nonaktifkan dan terbitkan kartu baru (riwayat, versi naik, kartu lama dipindai -> nonaktif); nonaktif tanpa pengganti
- [x] PDF QR kontingen F4 (SJK:) per kontingen dan semua; ganti QR tenda
- [x] Kunci data biodata: form publik tertutup, perubahan isian tercetak ditandai perlu cetak ulang; tombol "Sudah dicetak"
- [x] Tes: 30 tes kartu (QR di PDF dirender dan dipindai), total 187 tes lulus
- [ ] Uji pindai kartu cetak dengan HP Android dan iPhone dari jarak 20-50 cm (saat uji coba)

## Tahap 3: Absensi, rekap, poin, Anjangsana (7 Nov)
- [x] API absensi: `POST /api/pindai` dan `/api/pindai/batch` (maks 50), idempoten menurut `client_uuid`, kunci UNIQUE (titik, peserta) pada data aktif, transaksi pendek, hasil HIJAU/KUNING/MERAH, pindaian ditolak dicatat untuk audit; daftar titik, ringkasan, daftar peserta ringan (hash token) untuk cache HP, cari nama
- [x] Halaman pemindai `/panitia/`: nama pemindai, pilih titik (berlangsung/akan datang/selesai), kamera qr-scanner, layar penuh hijau/kuning/merah + bunyi/getar, kunci QR 3 detik, **antrean offline IndexedDB** dikirim otomatis, cari nama/kode manual, ganti kamera, senter, layar tidak mati
- [x] Superadmin: kelola titik absen (tambah/ubah/salin/hapus, buka/tutup/otomatis), detail titik (batalkan/tambah kehadiran manual dengan alasan), **pantauan langsung** semua titik
- [x] Kegiatan dan kuota (bawaan + khusus per kontingen), poin kehadiran otomatis (hadir +1, kurang dari kuota -1, opsi batasi ke kuota), `rekap.poin_kehadiran()` siap dipakai Tahap 4
- [x] Rekap `/rekap/` (superadmin + panitia, tanpa data pribadi): per tingkat, harian, poin per kegiatan, per kontingen (bisa dicetak), daftar ulang, per orang, Anjangsana; semua bisa diunduh Excel; segar otomatis 10 detik
- [x] Anjangsana `/anjangsana/` tanpa login: pindai kartu (atau ketik kode), konfirmasi 1, pindai QR tenda, konfirmasi 2 (teks persis spesifikasi), kunjungan tercatat, review 1-5 + komentar, peringatan + riwayat bila review diganti, "Kunjungi kontingen lain" 30 menit; hanya aktif selama sesi, buka/tutup paksa, kelola sesi; peringkat gabungan dan per tingkat + Excel; daftar kunjungan dan review; hapus review iseng; poster QR link PDF F4
- [x] Uji beban `sigap_uji_beban` lulus di laptop (Waitress 48 thread): 30 HP x 15 titik, 1.200 pindaian, p95 44 ms, 0 galat, 0 baris ganda; ledakan tanpa jeda 155 pindaian/detik, p95 225 ms, 0 ganda
- [x] HTTPS sementara untuk uji kamera di HP: `jalankan.bat -Https` (`sigap_https_dev`, sertifikat self-signed, tanpa Cloudflare)
- [x] Tes: 245 tes lulus, `ruff` bersih; uji browser Chrome 360 px dengan kamera palsu (pemindai: hijau, kuning, offline lalu terkirim; Anjangsana: alur lengkap, penolakan kartu di langkah tenda, peringatan ganti review)
- [ ] Uji beban di PC server Windows sungguhan (`22-PENGUJIAN.md`) dan uji kamera dari HP Android + iPhone sungguhan (Farhan, saat pemasangan/uji coba)

## Tahap 4: Form builder dan juri (7 Nov)
- [x] App `penilaian`: Formulir, Kolom (15 jenis), Kiriman (isian JSON + riwayat), PemecahSeri
- [x] Mesin rumus sendiri tanpa `eval` (`apps/penilaian/rumus.py`): tokenizer + recursive descent; + - * / x ×, perbandingan, SUM AVG MIN MAX ROUND ABS IF COALESCE ISBLANK AND OR NOT REF PERINGKAT POIN_PERINGKAT; rumus melingkar ditolak (di dalam form dan antarform); bagi nol -> kosong + peringatan
- [x] Tabel hasil mode 2: agregasi antarjuri (rata-rata/jumlah/terakhir), kolom otomatis [poin_kehadiran] [jumlah_hadir] [kuota] [jumlah_juri], REF antarform per tingkat (kunci REF) dan `REF("anjangsana", ...)`, peringkat dengan seri + pemecah seri, penanda belum dinilai / juri kurang, rincian per juri, Excel, kunci form, buka kunci per kiriman
- [x] Form builder superadmin `/superadmin/form/`: pengaturan, editor kolom (seret untuk urutan), editor rumus dengan cek langsung + pratinjau, salin antartingkat, arsip, pratinjau sebagai pengisi, isi sebagai superadmin
- [x] Mode 1: kiriman, rekap + grafik batang, detail/ubah/hapus, berkas unggahan privat, Excel; form publik `/f/<slug>/`
- [x] Juri `/juri/`: daftar form per kegiatan, Nama Juri, status per subjek, isian besar untuk HP, draf localStorage, ringkasan + peringatan sebelum kirim, terkunci setelah kirim
- [x] `sigap_buat_template_penilaian`: 40 form DRAF dari pedoman (sudah dijalankan di DB laptop)
- [x] Tes: 340 tes lulus (77 tes mesin rumus), `ruff` bersih; uji browser Chrome 360 px (editor rumus, alur juri, tabel hasil)
- [ ] Aspek dan bobot final dari panitia (5 Nov), lalu sesuaikan 40 form draf dan aktifkan
- [ ] Rumus juara umum per tingkat disusun bersama panitia (template baru contoh Traveling)

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
11. **Sandi ketiga akun di laptop disetel ulang (22 Okt, 22.0x)** ke nilai `SIGAP_SANDI_AWAL_*` di `web\.env` laptop yang baru Farhan ubah, dengan `sigap_atur_sandi --semua --dari-env`. Sandi itu pendek (4-7 karakter): ganti dengan sandi kuat dari Superadmin > Akun dan kata sandi (aplikasi belum memaksa ganti sandi saat masuk). Sandi di `.env` hanya dipakai saat akun dibuat, jadi mengubah `.env` saja tidak mengubah sandi.
12. **Laptop sudah selalu HTTPS:** `jalankan.bat` lalu buka `https://IP-laptop:8000` di HP (Wi-Fi sama), terima peringatan sertifikat sekali per HP. Bila HP tidak bisa membuka, izinkan port 8000 di Windows Firewall.
13. **Panitia kirim kuota final per kegiatan** paling lambat 31 Okt, lalu isi di Superadmin > Kegiatan dan kuota.
14. Di laptop, status form biodata masih **Paksa buka** (untuk uji). Kembalikan ke **Otomatis** sebelum 26 Okt (`sigap_cek_lingkungan` mengingatkan).

## Catatan sesi

### 23 Oktober 2026 (Claude Code): HTTPS menjadi bawaan jalankan.bat

Pertanyaan Farhan: kenapa setelah uji kamera berhasil `jalankan.bat` masih `http://`. Benar, seharusnya digabung. `jalankan.bat` kini selalu HTTPS di port 8000 (sertifikat buatan sendiri), `http://` ke port yang sama dialihkan 301 ke `https://`, opsi `-Https` dihapus (diganti `-Http` bila perlu tanpa HTTPS), `sigap_uji_beban` menerima `https://` dengan sertifikat buatan sendiri. Diuji: HTTPS dari localhost dan IP Wi-Fi 200, pengalihan http -> https, form masuk (CSRF) lewat browser, uji beban kecil lewat HTTPS lulus. Server produksi tetap HTTPS lewat Apache + sertifikat asli (docs/21).

### 23 Oktober 2026 (Claude Code): revisi R7-R9

Permintaan Farhan: tempat sampah, Nama Juri diingat, desain kartu modern per warna tingkat + Nomor Induk Anggota. Semua dikerjakan, diuji, dan dicatat di `REVISI.md` (R7, R8, R9). Temuan sendiri saat mengerjakan: desain pertama membuat QR kurang dari 45 mm (melanggar spesifikasi 13), tata letak diubah sehingga QR tetap 45 mm. **Kartu yang sudah dicetak dengan desain lama** tetap berlaku (QR sama); cetak ulang hanya bila panitia ingin desain baru.

### 23 Oktober 2026 (Claude Code): Tahap 4

Farhan menguji pemindai di HP Android sungguhan lewat `jalankan.bat -Https` (hijau, kuning, merah tingkat beda): lancar, lalu meminta lanjut. Dikerjakan Tahap 4 (commit `41b82f9`, `576dae3`). Sintaks REF final dicatat di `16-FORM-BUILDER.md`.

Ditemukan dan diperbaiki saat uji browser: batas angka di HP tidak muncul karena angka di atribut HTML ditulis format Indonesia (`100,0`); subjek yang belum dinilai ikut mendapat peringkat dari poin kehadiran saja (sekarang tanpa peringkat bila form punya isian juri); kotak pesan berisi tautan terpotong.

Catatan: kiriman/form yang dihapus masuk tempat sampah (soft delete) tetapi belum tampil di halaman Tempat sampah; pemulihan sementara lewat django-admin.

**Langkah berikutnya:** Tahap 5 (piagam peserta dan juara, termasuk "buat piagam juara" dari tabel hasil), lalu pemasangan di server produksi bersama Farhan.

### 22 Oktober 2026 (Claude Code): Tahap 3

Dikerjakan Tahap 3 dalam 7 langkah (commit `e1b28cb` sampai `4fa15d9`): inti absensi + API, halaman pemindai, kelola titik + pantauan, kuota + poin + rekap, Anjangsana, uji beban, HTTPS sementara. Semua aturan kebersamaan pemindai dari `14-ABSENSI.md` dibuktikan dengan tes thread nyata di MariaDB (20 HP memindai kartu sama -> 1 baris, 1 hijau 19 kuning) dan uji beban lewat HTTP.

**Insiden (laptop, sudah dipulihkan):** saat uji coba pertama perintah `sigap_uji_beban`, kode pembersihnya masih berisi penghapusan "akun sementara", padahal perintah sudah diubah memakai akun `panitia` yang ada (akun per peran bersifat tunggal). Akibatnya **akun `panitia` di database laptop terhapus**. Dipulihkan dengan `sigap_seed` (akun dibuat ulang dengan sandi awal dari `.env`). Log aktivitas lama tetap ada. Kode diperbaiki (tidak ada lagi penghapusan akun) dan ditambah tes `test_uji_beban.py` yang memastikan akun panitia dan sandinya tidak tersentuh. Tidak ada biodata yang terdampak.

**Penyimpangan dari `22-PENGUJIAN.md`:** uji beban tidak memakai database terpisah `sigap_jumbara_uji`, tetapi membuat data uji tersembunyi di database server yang diuji lalu menghapusnya lagi berdasarkan ID (alasan di `IMPROVISASI.md`).

**Data uji di laptop dibersihkan:** titik `TA-UJI` (2 kehadiran) dan kunjungan/review uji Anjangsana dihapus; status Anjangsana dikembalikan ke Otomatis.

**Uji HP sungguhan oleh Farhan (22 Okt, 22.11-22.14, Android Chrome lewat `jalankan.bat -Https`):** kamera membaca QR kartu dari layar laptop; titik Daftar Ulang (12 Nov) ditolak merah "sedang tertutup" (benar); setelah superadmin membuka paksa titik itu, pindaian hijau lalu kuning "Sudah tercatat pukul 22.14 oleh hans" (benar). Temuan: spanduk "1 pindaian tersimpan di HP" sempat muncul untuk pindaian yang sedang dikirim; diperbaiki, beserta pencegahan antrean ganda saat offline. Di laptop, titik **TA-001 Daftar Ulang masih berstatus BUKA** dan berisi 1 kehadiran uji (AHMAD FARHAN) serta 3 pindaian ditolak dari uji ini; kembalikan ke Otomatis dan batalkan kehadiran uji itu sebelum acara.

**Langkah berikutnya:** Tahap 4 (form builder mode 1 dan 2, mesin rumus aman tanpa `eval`, tarik data antarform, poin kehadiran dari `rekap.poin_kehadiran()`, Anjangsana sebagai sumber data, akun juri), lalu Tahap 5 (piagam), terakhir pemasangan di server produksi bersama Farhan.

### 22 Oktober 2026 (Claude Code): Tahap 2

Keputusan Farhan: Cloudflare Tunnel tidak dipakai; pemasangan di server dikerjakan paling akhir; kerjakan tahap berikutnya dulu karena panitia ingin uji coba menyeluruh secepatnya. Revisi R6: kartu menampilkan QR + foto (sudah sesuai rancangan).

Dikerjakan Tahap 2 lengkap (lihat centang). Diuji: QR di PDF dirender lalu dipindai (OpenCV) dan cocok dengan token di database, termasuk nama terpanjang; halaman kartu di HP 360 px dan laptop; unduhan PDF/ZIP lewat browser. Ditemukan dan diperbaiki: nama kontingen menimpa pita tingkat di lembar QR tenda; nama panjang terpotong di sampul; tombol "Cetak ringkasan" diblokir CSP.

**Langkah berikutnya:** Tahap 3 (pemindai absensi dengan antrean offline dan pemindaian bersamaan, titik absen, rekap dan poin, Anjangsana). Catatan: kamera HP butuh HTTPS; untuk uji di HP sebelum pemasangan perlu cara HTTPS sementara (Cloudflare Tunnel tidak dipakai).

### 22 Oktober 2026 (Claude Code)

`runserver` gagal `(2002, "Can't connect to server on '127.0.0.1' (10061)")`: MariaDB 10.11 pengembangan (port 3307) mati karena belum menjadi service dan ikut mati saat sesi/laptop berhenti. Dinyalakan ulang. Ditambah `web/scripts/windows/mariadb-dev.ps1` (nyalakan, `-Status`, `-PasangService` sebagai Admin) dan petunjuk di `sigap_cek_lingkungan`. **Farhan disarankan menjalankan `-PasangService` sekali** agar tidak terulang.

Lanjutan: browser membuka server pengembangan lewat `https://` (log "You're accessing the development server over HTTPS"): server pengembangan hanya `http://`, aplikasi tidak memaksa HTTPS. `.env` laptop memakai `DJANGO_DEBUG=False`, sehingga `staticfiles` lama (sebelum R1b-R5) dipakai; `collectstatic` dijalankan ulang. Dibuat **`jalankan.bat`** (satu perintah cek menyeluruh + jalankan server; diuji: semua langkah OK, MariaDB mati dinyalakan otomatis, server pengembangan dan mode `-Produksi` (Waitress) menjawab 200 lewat IP laptop, port bentrok terdeteksi). Peringatan `sigap_cek_lingkungan` diperjelas. Header COOP hanya lewat HTTPS. 157 tes lulus.

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
