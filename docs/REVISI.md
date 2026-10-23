# Revisi Permintaan

Catatan revisi dari Farhan setelah Tahap 1 selesai di laptop. Setiap revisi punya nomor, isi permintaan, dampak, rencana pengerjaan, dan status. Jika revisi mengubah keputusan, `docs/00-KEPUTUSAN.md` ikut diperbarui saat revisi dikerjakan.

## Daftar ringkas

| No | Tanggal | Revisi | Status |
|---|---|---|---|
| R1 | 18 Okt 2026 | Tingkat dipilih paling atas, daftar sekolah hanya menampilkan sekolah tingkat itu | **Selesai** 18 Okt (opsi A: server menolak) |
| R2 | 18 Okt 2026 | Perubahan manual Farhan: foto dicetak di kartu, bantuan nomor anggota (SIAMO), bantuan nama huruf kapital | **Selesai** 18 Okt (foto wajib mutlak; desain kartu berfoto di Tahap 2) |
| R3 | 18 Okt 2026 | Semua nama disimpan dan ditampilkan dalam HURUF KAPITAL, termasuk gelar | **Selesai** 18 Okt (nama lengkap + nama orang tua/wali) |
| R1b | 18 Okt 2026 | Laporan Farhan: tingkat Wira dipilih tetapi sekolah Mula/Madya masih muncul, kotak cari sekolah hilang. Pencarian harus tetap ada | **Selesai** 18 Okt |
| R1c | 18 Okt 2026 | Laporan Farhan: setelah R1b halaman rusak (ikon kaca pembesar raksasa menutupi form, tidak bisa cari/pilih sekolah, banyak galat) | **Selesai** 18 Okt |
| R4 | 18 Okt 2026 | Tidak boleh ada pencocokan NIK dengan tanggal lahir/jenis kelamin | **Selesai** 18 Okt |
| R5 | 18 Okt 2026 | Bagian menyesuaikan (memotong) foto terlalu kecil; harus responsif di HP, laptop, dan perangkat lain | **Selesai** 18 Okt |
| R6 | 22 Okt 2026 | Kartu peserta yang dibuat sistem menampilkan QR + foto peserta | **Selesai** 22 Okt (bersama Tahap 2) |

---

## R1. Tingkat dipilih dulu, sekolah disaring sesuai tingkat

**Permintaan:** di bagian "1. Kontingen", pilihan **Tingkat (Mula, Madya, Wira)** berada paling atas. Setelah tingkat dipilih, pilihan **Utusan sekolah** hanya menampilkan sekolah dengan tingkat tersebut. Sekolah dari tingkat lain tidak terlihat.

**Kondisi sekarang:** sekolah dipilih dulu (semua 29 sekolah, dikelompokkan per tingkat), tingkat terisi otomatis dari sekolah dan masih bisa diubah. Jika tingkat berbeda, kiriman diterima dengan tanda `TINGKAT_BEDA`.

**Dampak:**
- Urutan bagian 1 menjadi: Tingkat → Utusan sekolah → Peran.
- Dropdown sekolah dan kotak cari sekolah hanya berisi sekolah tingkat terpilih. Sebelum tingkat dipilih, dropdown sekolah nonaktif dengan teks "Pilih tingkat dulu".
- Mengganti tingkat setelah memilih sekolah akan mengosongkan pilihan sekolah bila sekolahnya tidak sesuai.
- Improvisasi lama "tingkat otomatis terisi dari sekolah" dan peringatan kuning "Tingkat ini berbeda dengan tingkat sekolah Anda" tidak dipakai lagi di form publik.
- Lewat form, tingkat dan tingkat sekolah selalu sama, sehingga tanda `TINGKAT_BEDA` praktis tidak muncul dari form publik.
- Tanpa JavaScript (fallback): dropdown tetap berisi semua sekolah per kelompok tingkat; server yang menjaga kecocokan (lihat keputusan di bawah).
- Form tambah/ubah superadmin tetap menampilkan semua sekolah (superadmin perlu memindahkan orang antar kontingen).
- "Isi untuk orang lain" tetap mengisi tingkat lalu sekolah.

**Perlu keputusan Farhan (bertentangan dengan `00-KEPUTUSAN.md` bagian Form biodata: "Tingkat yang dipilih berbeda dengan tingkat kontingen: superadmin melihat tanda"):**
- **Opsi A (saran):** server **menolak** kiriman bila tingkat tidak sama dengan tingkat sekolah, dengan pesan "Sekolah ini bukan tingkat Madya. Pilih lagi tingkat atau sekolah." Konsisten dengan tampilan baru. `00-KEPUTUSAN.md` diperbarui.
- **Opsi B:** server tetap menerima dan memberi tanda `TINGKAT_BEDA` (hanya bisa terjadi bila JavaScript mati atau kiriman dimanipulasi). Keputusan lama tidak berubah.

**Tes yang perlu disesuaikan/ditambah:** `test_tingkat_beda_diterima_dan_ditandai` (diubah sesuai opsi), tes urutan isian dan penyaringan sekolah di browser 360 px.

---

## R2. Perubahan manual oleh Farhan (diperiksa Claude, 18 Okt 2026)

Ditemukan lewat `git diff` (belum di-commit) di 4 file:

| No | File | Sebelum | Sesudah |
|---|---|---|---|
| R2.1 | `docs/00-KEPUTUSAN.md` (Form biodata) | "**Foto hanya arsip, tidak dicetak di kartu.**" | "**Foto hanya arsip, dicetak di kartu.**" |
| R2.2 | `docs/11-FORM-BIODATA.md` (Perilaku foto) | teks bantuan "...arsip panitia dan **tidak dicetak di kartu**." | "...arsip panitia dan **dicetak di kartu**." |
| R2.3 | `web/templates/biodata/form.html` (bagian Foto) | "...arsip panitia dan **tidak dicetak di kartu**." | "...arsip panitia dan **dicetak di kartu**." |
| R2.4 | `web/apps/biodata/forms.py` dan `form.html` (Nomor Induk Anggota) | "Ada di KTA PMR.." | "Terdapat pada aplikasi SIAMO" |
| R2.5 | `web/templates/biodata/form.html` (Nama lengkap) | "Tulis nama lengkap sesuai Kartu Keluarga, beserta gelar jika ada." | "Tulis nama lengkap dengan **huruf KAPITAL/Huruf Besar,** beserta gelar jika ada." |

### R2.1-R2.3 Foto dicetak di kartu

Keputusan baru: **foto peserta dicetak di kartu B-2.**

Hal yang masih bertentangan dan perlu dirapikan saat revisi ini dikerjakan:
- `docs/00-KEPUTUSAN.md` bagian **Kartu dan QR** masih menulis "Isi kartu: nama, kontingen, tingkat, peran, QR. **Tanpa foto.**" (baris 77).
- `docs/13-KARTU-QR.md` masih menulis "**Tanpa foto.**" (baris 29) dan belum mengatur letak foto di desain kartu.
- Kalimat "Foto hanya arsip, dicetak di kartu" saling bertentangan ("hanya arsip" vs dicetak). Usulan teks: "Foto dipakai di kartu peserta dan disimpan sebagai arsip panitia."
- Teks bantuan di form: usulan "Foto wajah terbaru, tampak depan, latar polos jika ada. Foto akan **dicetak di kartu peserta** dan disimpan sebagai arsip panitia."

Dampak teknis:
- **Tahap 2 (kartu):** desain B-2 perlu ruang foto 3x4 (usulan sekitar 24 x 32 mm di samping/atas nama), QR tetap minimal 45 x 45 mm. Foto 600x800 yang sudah disimpan cukup tajam untuk cetak ukuran itu (sekitar 635 dpi).
- **Foto wajib:** jika foto dicetak di kartu, sakelar `biodata.foto_wajib` sebaiknya tetap aktif. Untuk biodata tanpa foto (ditambah superadmin), kartu menampilkan kotak "FOTO" kosong untuk ditempel manual. Perlu konfirmasi.
- **Kualitas foto:** superadmin perlu daftar "tanpa foto" dan bisa mengganti foto (sudah ada di menu ubah). Usulan tambahan: tanda "foto perlu diganti" sebelum cetak kartu.
- **Perlindungan data:** foto anak akan terlihat di kartu yang dipakai di area kegiatan. Ini keputusan panitia; halaman web publik tetap tidak menampilkan foto. Tidak ada perubahan pada penyimpanan foto (tetap folder privat).
- **Perubahan foto setelah kartu dicetak** harus ikut menandai `perlu_cetak_ulang` (Tahap 2).
- `docs/IMPROVISASI.md` baris "Foto wajib, bisa dimatikan" dan alasan pemotong 3:4 tetap berlaku.

### R2.4 Nomor Induk Anggota dari aplikasi SIAMO

- Teks bantuan sudah diubah di `forms.py` dan `form.html`. Isian tetap **tidak wajib** dan label masih "Nomor Induk Anggota PMR (jika ada)".
- Kalimat "Kosongkan jika belum punya" ikut terhapus. Usulan: "Terdapat pada aplikasi SIAMO." agar anak yang belum terdaftar tidak bingung.
- Perlu diperbarui juga: `docs/11-FORM-BIODATA.md` tabel Bagian 2 (masih "Ada di KTA PMR").
- Pertanyaan: apakah format nomor SIAMO tertentu (misalnya hanya angka, panjang tetap)? Jika ya, bisa ditambahkan validasi.

### R2.5 Nama ditulis huruf kapital

- Teks bantuan sudah diubah. Frasa "sesuai Kartu Keluarga" terhapus; usulan dikembalikan: "Tulis nama lengkap sesuai Kartu Keluarga, beserta gelar jika ada. Huruf besar/kecil tidak masalah, sistem otomatis menyimpannya dalam HURUF KAPITAL." (lihat R3, karena sistem yang mengubah ke kapital, pengisi tidak wajib mengetik kapital).

### Catatan

- Keempat file tersebut belum di-commit. Saat R2 dikerjakan, perubahan Farhan di-commit terpisah dengan pesan yang jelas.
- Tidak ada perubahan manual lain yang ditemukan (di luar 4 file di atas, folder kerja sama dengan commit terakhir `88f5c79`).

---

## R3. Semua nama dalam HURUF KAPITAL

**Permintaan:** nama tercatat sebagai HURUF KAPITAL di seluruh sistem (database, tampilan, Excel, PDF, kartu, piagam) walaupun pengisi menulis huruf kecil. Berlaku juga untuk gelar (contoh `Sri Handayani, S.Pd` → `SRI HANDAYANI, S.PD`).

**Kondisi sekarang:** nama disimpan sesuai ketikan (spasi dirapikan). Hanya bukti PDF yang menampilkan nama dalam huruf besar.

**Rencana:**
- Form (publik dan superadmin): `clean_nama_lengkap` mengubah ke kapital sebelum disimpan. Validasi huruf/titik/koma/apostrof/tanda hubung tetap.
- Isian nama di form diberi gaya huruf kapital saat diketik (`text-transform: uppercase`, `autocapitalize="characters"`) agar pengisi melihat hasilnya; ringkasan sebelum kirim dan bukti menampilkan kapital.
- Data yang sudah ada: migrasi data aman (`UPPER(nama_lengkap)`), dicatat di log. Sebelum 26 Oktober hanya ada data uji, jadi tidak ada risiko ke data asli.
- Excel, PDF bukti, halaman superadmin otomatis ikut karena membaca dari database. Tahap 2 (kartu) dan Tahap 5 (piagam) memakai nilai yang sama.
- Pencarian nama di superadmin tetap tidak membedakan huruf besar/kecil.
- Cek "nama mirip" tidak terpengaruh (sudah membandingkan tanpa huruf besar/kecil).
- Tes: nama huruf kecil tersimpan kapital; gelar ikut kapital; apostrof tetap (`AS'AD`).

**Perlu konfirmasi Farhan:**
- Apakah **nama ayah/ibu/wali** juga dibuat kapital? (Saran: **ya**, agar seragam.)
- **Tempat lahir** dan **alamat**: saran tetap sesuai ketikan (bukan nama orang). Atau ikut kapital?
- **Nama kontingen/sekolah** sudah dikelola superadmin; saran tidak diubah otomatis (kartu sudah menampilkan huruf besar sesuai desain).

---

## Urutan pengerjaan yang disarankan

1. Commit perubahan manual Farhan (R2) apa adanya.
2. R3 (nama kapital) dan R1 (tingkat dulu): kecil, menyentuh form publik, harus selesai dan diuji di HP sebelum 25 Oktober.
3. Rapikan dokumen yang bertentangan (R2.1-R2.5) dan perbarui `00-KEPUTUSAN.md`.
4. Desain kartu dengan foto (R2.1) dikerjakan di Tahap 2.

---

## Keputusan Farhan dan hasil pengerjaan (18 Okt 2026)

Jawaban Farhan: (1) ikut saran: server **menolak** tingkat yang tidak cocok dengan sekolah; (2) nama ayah/ibu/wali **ikut kapital**, tempat lahir dan alamat tetap sesuai ketikan; (3) **foto wajib mutlak**; (4) format nomor SIAMO tetap bebas.

| Revisi | Yang dikerjakan |
|---|---|
| R1 | Urutan bagian 1: Tingkat → Utusan sekolah → Peran. Sebelum tingkat dipilih, dropdown sekolah nonaktif ("Pilih tingkat dulu"). Daftar sekolah dan kotak cari hanya berisi sekolah tingkat terpilih; ganti tingkat mengosongkan sekolah yang tidak sesuai. Draf HP dan "Isi untuk orang lain" mengisi tingkat dulu lalu sekolah. Server menolak di form publik: "[sekolah] bukan sekolah tingkat [X]. Pilih lagi tingkat atau sekolah." Superadmin tetap boleh berbeda (tanda TINGKAT_BEDA). Peringatan kuning lama dihapus. |
| R2 | Pengaturan `biodata.foto_wajib` dihapus dari kode dan menu Pengaturan form; foto wajib di form publik dan tambah biodata superadmin (ubah biodata boleh memakai foto lama). Teks foto: "Foto akan dicetak di kartu peserta dan disimpan sebagai arsip panitia." Teks SIAMO: "Terdapat pada aplikasi SIAMO." `00-KEPUTUSAN.md` (isi kartu dengan foto) dan `13-KARTU-QR.md` (foto 3x4 di kartu) diperbarui. Desain kartu dikerjakan di Tahap 2. |
| R3 | `nama_lengkap` dan `nama_orang_tua` disimpan kapital di server (form publik dan superadmin); isian tampil kapital saat diketik; ringkasan kapital. Migrasi `biodata.0002_nama_kapital` mengubah data yang sudah ada. Excel, PDF bukti, ZIP foto, halaman superadmin otomatis kapital. |

Pengujian: 154 tes otomatis lulus (tes baru: tingkat beda ditolak, urutan isian, foto wajib mutlak walau pengaturan lama masih ada di database, nama dan gelar kapital, tambah superadmin tanpa foto ditolak, ubah tanpa foto baru). Uji browser Chrome 360 px: sekolah tersaring per tingkat (Mula 3, Wira 9), cari "sma" saat Madya tidak menemukan apa pun, ganti tingkat mengosongkan sekolah, draf dipulihkan, kiriman tersimpan `DEWI KARTIKA SARI` / `BUDI SANTOSO, S.PD`, lebar halaman 360 px, tanpa galat konsol.

---

## R1b. Sekolah tingkat lain masih muncul dan kotak cari hilang (laporan Farhan, 18 Okt 2026)

**Laporan:** setelah memilih Wira, dropdown sekolah masih berisi kelompok "Tingkat Mula" dan "Tingkat Madya", dan kotak cari sekolah tidak ada (tangkapan layar Farhan, teks dropdown "Pilih sekolah").

**Penyebab:** browser Farhan memakai `biodata.js` **versi lama dari cache**, sementara template sudah versi baru. Server pengembangan (`runserver`) mengirim file statis dengan nama yang sama tanpa `Cache-Control`, sehingga browser boleh memakai salinan lama. Dengan JS lama, kode penyaring sekolah tidak ada, jadi yang tampil adalah daftar cadangan (semua sekolah per kelompok tingkat, untuk HP tanpa JavaScript), dan kotak cari ikut tersembunyi. Di server produksi masalah ini tidak terjadi karena nama file statis ber-hash (`biodata.<hash>.js`), tetapi tetap diperbaiki agar uji di laptop dapat dipercaya.

**Perbaikan:**
1. Mode pengembangan: statis dilayani WhiteNoise (`whitenoise.runserver_nostatic`) dengan `WHITENOISE_MAX_AGE = 0` (header `Cache-Control: max-age=0`), sehingga browser selalu mengambil JS/CSS terbaru. Produksi tetap 30 hari dengan nama ber-hash.
2. Kotak cari sekolah **selalu tampil** (dengan ikon cari). Sebelum tingkat dipilih: nonaktif, tulisan "Pilih tingkat dulu". Setelah tingkat dipilih: "Cari sekolah tingkat Wira…".
3. Menyentuh kotak cari langsung menampilkan **semua sekolah dari tingkat terpilih saja** (Mula 3, Madya 17, Wira 9); mengetik menyaring per kata; tombol Enter memilih hasil teratas; sekolah yang sedang terpilih disorot.
4. Jika kata yang dicari tidak ada di tingkat itu (misalnya "smp" saat Mula): "Tidak ditemukan di tingkat Mula. Periksa lagi tingkat yang dipilih, atau hubungi superadmin."
5. Di bawah dropdown: "9 sekolah tingkat Wira. Ketik di kotak cari atau pilih dari daftar."
6. Dropdown asli tetap ada di bawah kotak cari dan juga hanya berisi sekolah tingkat terpilih.

**Pengujian (Chrome 360 px, browser baru):** header `Cache-Control: max-age=0` terkirim; Mula: kotak cari 3 dan dropdown 3, Madya 17/17, Wira 9/9, tidak ada sekolah dari tingkat lain; Mula + "smp" kosong dengan pesan; Mula + "006" + Enter memilih SD Negeri 006 Tanjung Palas Utara; lebar halaman 360 px; tanpa galat konsol. 154 tes otomatis lulus.

**Untuk Farhan:** tekan **Ctrl+F5** sekali di halaman form (atau tutup lalu buka lagi tab) agar browser membuang `biodata.js` lama yang sudah terlanjur tersimpan.

---

## R1c. Halaman rusak setelah R1b (laporan Farhan, 18 Okt 2026)

**Laporan:** ikon kaca pembesar sangat besar menutupi bagian Kontingen dan Peran, kotak cari tidak bisa dipakai, pilihan sekolah tidak bisa diklik, dan banyak galat.

**Penyebab (diakui, kesalahan Claude):** perbaikan cache di R1b hanya berlaku untuk file yang diambil *setelah* perbaikan. Browser Farhan masih menyimpan `app.css` dan `biodata.js` lama, lalu memadukannya dengan halaman baru:
- `app.css` lama belum punya kelas `h-5`, `w-5`, `pointer-events-none` (diperiksa dari commit sebelumnya), sehingga ikon SVG tampil seukuran kolom dan menghalangi klik.
- `biodata.js` lama belum punya fungsi `labelTingkat`/`jumlahSekolah` yang dipanggil halaman baru, sehingga Alpine menampilkan galat dan kotak cari tidak berfungsi.
- Uji sebelumnya hanya memakai browser bersih (tanpa cache), jadi masalah ini tidak tertangkap.

**Perbaikan:**
1. Semua CSS/JS di template memakai tag `{% aset '...' %}` yang menambahkan versi otomatis dari waktu ubah file (`/static/js/biodata.js?v=1792324869`). Setiap kali file berubah, alamatnya berubah, sehingga browser **pasti** mengambil file baru tanpa Ctrl+F5. Produksi tetap memakai nama file ber-hash dari `collectstatic`.
2. Ikon kaca pembesar dihapus (kotak cari cukup dengan tulisan "Cari sekolah tingkat …"), sehingga tidak ada lagi elemen yang bisa menutupi form.

**Pengujian:** profil Chrome yang menyimpan cache (seperti browser Farhan): halaman dimuat, `biodata.js` diubah, halaman dimuat ulang biasa → alamat `biodata.js?v=` berganti dan file baru diambil dari server (status 200), kotak cari aktif ("Cari sekolah tingkat Wira…"), 9 sekolah Wira, cari "smk 2" + Enter memilih SMK Negeri 2 Tanjung Selor, dropdown bisa dipilih, tanpa galat konsol. Alur form lengkap (draf, ringkasan, kirim, bukti, isi untuk orang lain) lulus di 360 px. 156 tes otomatis lulus (tambahan: tes alamat aset berversi).

**Pelajaran untuk sesi berikutnya:** setiap perubahan CSS/JS diuji juga dengan profil browser yang sudah punya cache versi sebelumnya, bukan hanya browser bersih.

---

## R4. Hapus pencocokan NIK dengan tanggal lahir dan jenis kelamin (18 Okt 2026)

**Permintaan:** peringatan "Tanggal lahir atau jenis kelamin tidak cocok dengan NIK. Periksa lagi. Jika sudah benar, lanjutkan." tidak boleh ada. Tidak boleh ada protokol pencocokan seperti itu di mana pun.

**Yang dihapus (diperiksa dengan pencarian di seluruh repositori):**

| Tempat | Yang dihapus |
|---|---|
| `web/templates/biodata/form.html` | Kotak peringatan kuning di bawah tanggal lahir |
| `web/static/js/biodata.js` | Perhitungan digit 7-12 NIK di browser (`peringatanNik`) dan baris peringatan di layar ringkasan sebelum kirim |
| `web/apps/biodata/nik.py` | Fungsi `info_dari_nik`, `cocok_tanggal_lahir`, `cocok_jenis_kelamin` |
| `web/apps/biodata/forms.py` | Metode `peringatan()` (pencocokan di server) |
| `web/apps/biodata/services.py` | Tanda `NIK_TGL_LAHIR_BEDA` dan `NIK_JK_BEDA` di `hitung_tanda` (fungsi tidak lagi menerima NIK sama sekali) |
| `web/apps/biodata/models.py` | Dua jenis tanda itu dari pilihan `JenisPenanda` (halaman superadmin, saringan tanda, Excel ikut tidak menampilkannya) |
| Database | Migrasi `biodata.0003_hapus_tanda_nik`: tanda lama dua jenis itu dihapus (data turunan, biodata tidak berubah) |
| Dokumen | `00-KEPUTUSAN.md` (aturan baru), `01-TAHAPAN.md`, `03-DATA-MODEL.md`, `11-FORM-BIODATA.md`, `IMPROVISASI.md`, `PROGRES.md` |

**Yang tetap ada (bukan pencocokan NIK):** NIK wajib 16 angka, tidak boleh semua angka sama, dan tidak boleh dobel; NIK disimpan terenkripsi dan disamarkan. Tanda lain tetap: kuota penuh, usia tidak wajar per tingkat (dari tanggal lahir saja), foto duplikat, nama mirip, tingkat beda (dari superadmin).

**Sisa yang sengaja tidak diubah:** `migrations/0001_initial.py` masih menyebut dua jenis tanda itu karena migrasi yang sudah diterapkan tidak boleh diubah (aturan `CLAUDE.md`); migrasi 0003 yang menghapusnya.

**Pengujian:** tes baru `test_nik_tidak_dicocokkan_dengan_tanggal_lahir_dan_jk` (NIK yang digitnya tidak sesuai tanggal lahir dan jenis kelamin diterima tanpa tanda apa pun; halaman form dan `biodata.js` tidak berisi kalimat pencocokan; jenis tanda tidak ada lagi). Tes tanda di superadmin dipindah ke tanda usia tidak wajar. 156 tes lulus; uji browser 360 px tanpa peringatan NIK.

---

## R5. Pemotong foto terlalu kecil dan harus responsif (laporan Farhan, 18 Okt 2026)

**Laporan:** setelah memilih foto, foto di area "Geser dan perbesar…" tampil sangat kecil di pojok kiri atas, sementara area gelapnya besar (tangkapan layar Farhan di laptop).

**Penyebab:** pemotong (Cropper.js) dipasang sebelum wadahnya selesai tampil (masih tersembunyi, lebar 0). Pada kondisi itu Cropper memakai ukuran minimum bawaan 200 x 100 piksel. Kejadiannya acak (tergantung kecepatan browser), terutama saat foto dipilih atau diganti. Diulang dengan uji otomatis: 4 dari 21 kombinasi perangkat/foto menghasilkan kontainer 200 x 100. Selain itu tinggi area tetap 360 px membuat pemotong terasa kecil di laptop.

**Perbaikan:**
1. Pemotong baru dipasang setelah wadahnya benar-benar tampil dan punya ukuran (ditunggu per frame layar).
2. Pemotong ikut menyesuaikan bila ukuran wadah berubah (HP diputar mendatar/tegak, jendela laptop diubah) memakai `ResizeObserver`.
3. Tinggi area mengikuti layar: `clamp(280px, 65vh, 600px)` (minimal 280 px, sekitar 65% tinggi layar, maksimal 600 px); lebar penuh kolom form.
4. Tombol baru **− Perkecil** dan **+ Perbesar** (laptop tidak bisa mencubit layar), selain **↻ Putar** dan **Ganti foto**; 2 kolom di HP, 4 kolom di layar lebar. Petunjuk: "Di HP: geser dengan satu jari, cubit dengan dua jari untuk memperbesar."
5. Pemuatan foto bertingkat: `blob:` URL → `FileReader` → bila browser tetap tidak bisa menampilkan pratinjau, foto asli tetap dikirim tanpa galat dengan pesan "Pratinjau tidak bisa ditampilkan di HP ini, tetapi foto tetap dikirim dan otomatis dipotong di bagian tengah." Server tetap meluruskan EXIF dan memotong 3:4.

**Pengujian (otomatis, Playwright):**
- 3 mesin browser: Chromium (Chrome/Edge/Android), **WebKit (Safari, semua browser di iPhone/iPad)**, Firefox.
- 7 ukuran layar: HP 320x568, HP 360x780, iPhone 390x844, Pixel 412x915, tablet 768x1024, laptop 1366x768, monitor 1920x1080.
- 3 jenis foto: potret (logo Jumbara asli), lanskap besar 2400x1800, foto kecil 240x320.
- Syarat lulus: kontainer pemotong sama dengan wadah, foto memakai >= 90% wadah, kotak potong cukup besar, tidak ada geser horizontal halaman, wadah tidak lebih tinggi dari layar, tanpa galat. Hasil: **63/63 lulus** (sebelum perbaikan 4 gagal di Chromium).
- Tombol Perbesar/Perkecil/Putar berfungsi; HP diputar mendatar lalu tegak, pemotong tetap memenuhi wadah; kirim lewat mode tanpa pratinjau berhasil (foto tersimpan 600x800).
- Catatan uji: WebKit versi Windows dari Playwright kadang gagal membaca berkas yang dipilih dari drive D: (`NotFoundError`), sedangkan berkas yang sama dari drive C: 10/10 berhasil. Ini kendala alat uji, bukan aplikasi; aplikasi tetap menanganinya dengan mode tanpa pratinjau. **Uji di iPhone dan Android sungguhan tetap wajib** sebelum 25 Oktober.

---

## R6. Kartu peserta menampilkan QR dan foto peserta (22 Okt 2026)

**Permintaan Farhan:** kartu peserta yang dibuat sistem menampilkan QR dan foto peserta.

**Hasil:** sudah sesuai rancangan sejak R2 dan diterapkan di Tahap 2. Setiap kartu B-2 memuat foto 3x4 (24 x 32 mm, bingkai tipis) di samping nama, dan QR besar (kotak 52 mm, simbol sekitar 46 mm) di bawahnya beserta kode kartu. Biodata tanpa foto (seharusnya tidak ada karena foto wajib mutlak) tetap dicetak dengan kotak "FOTO 3x4" kosong agar bisa ditempel manual. Dicatat juga di `00-KEPUTUSAN.md` bagian Kartu dan QR.

---

## R7. Desain kartu peserta lebih modern + Nomor Induk Anggota (permintaan panitia lewat Farhan, 23 Okt 2026)

**Permintaan:** desain ID card lebih modern (gradasi, dan lainnya diimprovisasi); setiap tingkat dibedakan warna dominan memakai warna yang sudah ada di sistem: **Mula hijau, Madya biru, Wira kuning**; QR tetap hitam putih agar mudah dipindai. Tambahan: **Nomor Induk Anggota tampil di bawah nama**.

**Desain baru (88 x 125 mm, `apps/kartu/pdf.py` `gambar_kartu`):**
1. Kepala bergradasi diagonal warna tingkat (Mula #14532D -> #16A34A -> #4ADE80, Madya #1E3A8A -> #2563EB -> #60A5FA, Wira #B45309 -> #EAB308 -> #FDE68A) dengan tepi bawah melengkung dan lingkaran transparan sebagai hiasan. Teks di atas Wira berwarna gelap agar terbaca.
2. Logo PMI dan Jumbara V di kapsul putih (logo PMI tetap di latar terang, tidak diubah).
3. Foto 3x4 (20 x 26,7 mm) berbingkai putih, sudut membulat, bayangan halus, menimpa batas kepala.
4. Di samping foto: "TINGKAT" + nama tingkat besar, lencana peran, nama kontingen.
5. Nama besar di bawah foto (ukuran huruf otomatis, maksimal 2 baris), lalu **No. Induk Anggota** (tidak dicetak bila kosong).
6. QR hitam putih **45 x 45 mm** (sesuai minimal spesifikasi 13) di pelat putih berbingkai warna tingkat, kode kartu di bawahnya.
7. Pita kaki bergradasi: "KARTU WAJIB DIPAKAI SELAMA KEGIATAN", kode kontingen, versi kartu.
- Tetap bisa dibedakan bila dicetak hitam putih: tulisan "TINGKAT ..." dan peran tetap ada.
- Nomor Induk Anggota masuk daftar isian tercetak: mengubahnya setelah data dikunci menandai kartu **perlu cetak ulang**.

**Pengujian:** PDF 4 kartu (3 tingkat, nama terpanjang 2 baris + nomor induk) dirender dan dipindai OpenCV: 4/4 QR terbaca dan cocok. Tes kartu (31) lulus, termasuk tes baru penanda cetak ulang untuk Nomor Induk Anggota.

---

## R8. Nama Juri diingat seperti nama pemindai (laporan Farhan, 23 Okt 2026)

**Laporan:** setelah keluar atau sesi habis lalu masuk lagi, juri diminta menulis ulang Nama Juri; seharusnya tidak perlu (seperti nama panitia pemindai).

**Penyebab:** nama pemindai disimpan di perangkat (localStorage per akun) dan dibaca langsung oleh halaman pemindai. Halaman juri tidak pernah menyimpan Nama Juri ke perangkat dan hanya membaca nama dari cookie, padahal cookie itu dihapus saat keluar dan baru dipasang lagi setelah halaman pertama terbuka.

**Perbaikan:** Nama Juri yang dipakai (tombol "Pakai" atau saat mengirim nilai) disimpan di perangkat untuk akun juri. Setelah masuk lagi, halaman form juri langsung memakai nama itu (status sudah/belum dinilai ikut tampil) dan isian Nama Juri di form nilai terisi otomatis. Superadmin tidak terpengaruh (nama pelakunya untuk log tidak diganti).

**Pengujian (Chrome 360 px):** isi nama -> keluar (cookie dihapus, sesi baru) -> buka halaman form juri sebagai halaman pertama: nama langsung terisi, header menampilkan nama, form nilai terisi.

---

## R9. Tempat sampah untuk data lain (temuan Claude, 23 Okt 2026)

Halaman **Superadmin > Tempat sampah** sekarang juga memuat form, kiriman form, kehadiran yang dibatalkan, dan review Anjangsana, masing-masing dengan **Pulihkan** dan **Hapus permanen** (tercatat di log). Pemulihan yang bentrok ditolak dengan pesan jelas (slug form sudah dipakai, orang sudah tercatat hadir lagi, review aktif sudah ada, juri yang sama sudah mengirim ulang, form kiriman masih di tempat sampah). Form yang masih punya kiriman tidak bisa dihapus permanen; berkas unggahan ikut dihapus saat kiriman dihapus permanen.

---

## R7b. Kartu: tingkat lebih kecil, latar penuh warna tingkat (permintaan panitia lewat Farhan, 23 Okt 2026)

**Permintaan:** tulisan Mula/Madya/Wira tidak perlu sebesar sebelumnya; warna dominan menjadi latar **seluruh kartu** kecuali QR dan sekitarnya yang tetap hitam putih; susunan dan estetika ditinjau ulang.

**Desain akhir (`gambar_kartu`):**
1. Seluruh kartu berlatar gradasi diagonal warna tingkat (Mula #14532D -> #16A34A, Madya #1E3A8A -> #2563EB, Wira #FACC15 -> #FDE047 -> #FEF08A, kuning cerah sesuai R7c) dengan lingkaran transparan dan garis gelombang tipis sebagai hiasan.
2. Kapsul putih logo PMI + Jumbara V, judul acara dan tema di bawahnya.
3. Foto 24 x 32 mm (sesuai spesifikasi) berbingkai putih dan bayangan di kiri.
4. Di kanan foto: lencana kecil **"TINGKAT MADYA"** (putih, teks gelap) dan lencana peran (garis), nama besar (maksimal 3 baris, huruf menyesuaikan), No. Induk Anggota (bila ada), garis tipis, kontingen.
5. **Pelat putih** berisi QR hitam putih 45 x 45 mm dengan margin 3 mm dan kode kartu di dalamnya, berbayang halus.
6. Kaki: "KARTU WAJIB DIPAKAI SELAMA KEGIATAN" dan kode kontingen + versi.
- Teks putih di atas hijau/biru, teks navy di atas kuning (kontras cukup). Lencana tingkat Wira memakai teks navy.

**Pengujian:** 4 kartu contoh (3 tingkat, nama 3 baris, peran panjang yang turun ke baris baru) dirender dan QR dipindai OpenCV: 4/4 terbaca; seluruh tes lulus.

---

## R7c. Kuning Wira lebih cerah dan bergradasi (permintaan Farhan, 23 Okt 2026)

Latar kartu Wira diganti dari kuning gelap (#CA8A04 -> #FACC15) menjadi **kuning cerah bergradasi** #FACC15 (kiri atas) -> #FDE047 -> #FEF08A (kanan bawah). Teks tetap navy agar terbaca. QR 4/4 terbaca pada render uji; tes kartu lulus.
