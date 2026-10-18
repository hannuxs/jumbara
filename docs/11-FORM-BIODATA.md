# 11. Form Biodata Publik (PRIORITAS UTAMA, Tahap 1)

Form ini harus online dan teruji pada **25 Oktober 2026** dan dibuka untuk umum **26 Oktober 2026**. Penggunanya anak SD sampai SMA, guru, dan orang tua, sebagian besar memakai HP Android kelas bawah. Buat sesederhana, sejelas, dan seringan mungkin.

## Alamat dan akses

- Satu link publik yang sama untuk semua orang, misalnya `https://<domain>/daftar`. Tanpa login.
- Halaman `/` (beranda) menampilkan nama acara, logo, tombol besar **"Isi Biodata"**, status form (dibuka/ditutup + jadwal), dan kontak superadmin.
- Buat juga QR menuju link form (di dasbor superadmin) agar panitia bisa membagikannya sebagai gambar.

## Jadwal buka dan tutup

- Bawaan: buka **26 Oktober 2026 00.00 WITA**, tutup **2 November 2026 23.59 WITA**. Disimpan di tabel `pengaturan`, bisa diubah superadmin.
- Superadmin punya sakelar: **Otomatis (ikut jadwal) / Paksa buka / Paksa tutup**. Paksa buka berguna untuk uji coba sebelum 26 Oktober dan untuk perpanjangan.
- Sebelum dibuka: tampilkan hitung mundur dan tanggal buka. Form tidak bisa dikirim.
- Setelah ditutup: tampilkan "Pendaftaran biodata sudah ditutup. Jika Anda belum terdaftar atau datanya perlu diperbaiki, hubungi superadmin" + tombol WhatsApp ke nomor superadmin (dari pengaturan).
- Pengecekan jadwal **dilakukan di server** saat menerima kiriman, bukan hanya di tampilan. Kiriman yang mulai diisi sebelum tutup tapi dikirim sesudah tutup: tolak dengan pesan ramah (draf tetap tersimpan di HP).
- Saat **data dikunci untuk cetak kartu** (Tahap 2), form publik otomatis tertutup.

## Isian form

Urutan di layar dibagi beberapa bagian dengan judul kecil. Semua label dalam Bahasa Indonesia yang mudah.

### Bagian 1: Kontingen

| Isian | Tipe | Aturan |
|---|---|---|
| **Utusan sekolah** | Dropdown yang bisa dicari (29 pilihan, dikelompokkan per tingkat: Mula, Madya, Wira) | Wajib. Isi dari tabel `kontingen` (sumber awal `data/kontingen.csv`). **Bukan ketikan bebas.** Di bawahnya tulis: "Sekolah Anda tidak ada? Hubungi superadmin" + link WhatsApp |
| **Tingkat** | Pilihan Mula / Madya / Wira | Wajib. **Otomatis terisi sesuai tingkat sekolah yang dipilih**, tetapi tetap bisa diubah. Jika diubah menjadi berbeda dari tingkat kontingen, tampilkan peringatan kuning "Tingkat ini berbeda dengan tingkat sekolah Anda. Pastikan sudah benar." Kiriman tetap diterima, superadmin melihat tanda TINGKAT_BEDA |
| **Peran** | Pilihan (kartu/tombol besar): Peserta, Pimpinan Kontingen, Pembina Pendamping, Peninjau | Wajib. Beri penjelasan singkat di bawah setiap pilihan: Peserta = anggota PMR yang ikut lomba/kegiatan; Pimpinan Kontingen = guru/pembina yang memimpin kontingen; Pembina Pendamping = guru/pembina yang mendampingi; Peninjau = pembina atau anggota PMR yang ikut mengamati |

Catatan: tingkat otomatis dari sekolah adalah improvisasi karena 1 sekolah = 1 kontingen = 1 tingkat menurut pedoman. Keputusan brief tetap dihormati: pengguna masih bisa memilih sendiri dan perbedaan ditandai.

### Bagian 2: Data diri

| Isian | Tipe | Aturan |
|---|---|---|
| **Nama lengkap** | Teks | Wajib. 3-100 karakter. Rapikan spasi ganda dan spasi di awal/akhir. Simpan sesuai ketikan (huruf besar-kecil asli); kartu menampilkan HURUF BESAR. Tolak angka dan simbol aneh, tapi izinkan titik, koma, apostrof, tanda hubung (contoh: "M. Fuad", "As'ad", "Sri Handayani, S.Pd") |
| **NIK** | Teks angka (`inputmode="numeric"`) | Wajib. Tepat 16 angka. Tidak boleh semua angka sama. **UNIK**: jika sudah terdaftar, tolak dengan pesan "NIK ini sudah terdaftar. Jika Anda merasa belum pernah mengisi atau ingin memperbaiki data, hubungi superadmin" + tombol WhatsApp. Teks bantuan: "NIK ada di Kartu Keluarga (KK)". Lihat cek NIK di bawah |
| **Nomor induk anggota** | Teks | Tidak wajib. Label: "Nomor Induk Anggota PMR (jika ada)". Teks bantuan: "Ada di KTA PMR. Kosongkan jika belum punya" |
| **Jenis kelamin** | Pilihan Laki-laki / Perempuan | Wajib |
| **Tempat lahir** | Teks | Wajib. 2-60 karakter |
| **Tanggal lahir** | Tanggal (tampilkan 3 dropdown hari-bulan-tahun atau date picker yang ramah HP; jangan memaksa format ketik) | Wajib. Tidak boleh di masa depan. Lihat cek usia di bawah |
| **Alamat rumah** | Paragraf | Wajib. 10-300 karakter |
| **Golongan darah** | Pilihan A, B, AB, O, Belum tahu | Wajib |
| **Telepon** | Teks angka | **Wajib untuk Pimpinan Kontingen dan Pembina Pendamping**, tidak wajib untuk Peserta dan Peninjau (banyak anak belum punya HP). Terima format `08...`, `+62...`, `62...`; simpan dinormalkan `62...`. 10-15 digit |

### Bagian 3: Orang tua atau wali

Tampilkan bagian ini **wajib untuk peran Peserta dan Peninjau**, dan **tidak wajib** (boleh dilewati) untuk Pimpinan Kontingen dan Pembina Pendamping (orang dewasa).

| Isian | Tipe | Aturan |
|---|---|---|
| **Nama ayah atau ibu (atau wali)** | Teks | Wajib sesuai peran di atas |
| **Telepon ayah atau ibu (atau wali)** | Teks angka | Wajib sesuai peran di atas. Format sama dengan telepon. Untuk kontak darurat |

### Bagian 4: Foto

| Isian | Tipe | Aturan |
|---|---|---|
| **Upload foto** | File gambar | **Wajib** (bisa dimatikan lewat pengaturan `biodata.foto_wajib`). Hanya JPG/JPEG atau PNG, **maksimal 5 MB** (ukuran file asli). Validasi tipe dari isi file (MIME sebenarnya), bukan hanya ekstensi |

Perilaku foto:
- Teks bantuan: "Foto wajah terbaru, tampak depan, latar polos jika ada. Foto hanya disimpan sebagai arsip panitia dan **tidak dicetak di kartu**."
- Setelah memilih foto, tampilkan **pemotong 3:4** (Cropper.js) dengan area potong otomatis di tengah; pengguna boleh menggeser/memperbesar. Tombol "Putar" untuk foto miring.
- Di browser, kecilkan dulu sebelum unggah (sisi terpanjang sekitar 1600 px, JPEG kualitas 0,85) agar unggahan ringan. Tetap kirim koordinat potong ke server.
- Di server (wajib, jangan percaya browser): baca orientasi EXIF dan luruskan, potong 3:4 sesuai koordinat (atau tengah jika tidak ada), ubah ukuran menjadi **600 x 800 px**, simpan JPEG kualitas 85, **hapus metadata EXIF** (termasuk lokasi GPS). Simpan di disk **privat** (`{SIGAP_FOLDER_PRIVAT}\foto\{tahun}\{kode_pendaftaran}.jpg`), bukan di folder `static` atau `media` publik. Pemrosesan dengan Pillow (`ImageOps.exif_transpose`).
- Foto hanya bisa dilihat superadmin lewat rute yang memeriksa login.
- Jika sha256 file asli sama dengan foto orang lain, beri tanda FOTO_DUPLIKAT (bukan ditolak).

### Bagian 5: Persetujuan

- Kotak centang wajib: "Saya menyatakan data ini benar. Saya (atau orang tua/wali saya) menyetujui data ini dipakai panitia Jumbara PMR Kabupaten Bulungan V 2026 untuk keperluan acara, termasuk kartu peserta, absensi, dan piagam." Simpan waktu persetujuan.
- Ini improvisasi untuk perlindungan data pribadi anak (UU 27/2022).

## Cek NIK dan usia (memberi tanda, bukan menolak)

- **NIK vs tanggal lahir dan jenis kelamin:** digit ke-7 dan 8 = tanggal lahir (ditambah 40 untuk perempuan), digit 9-10 = bulan, digit 11-12 = dua digit tahun. Jika tidak cocok dengan tanggal lahir atau jenis kelamin yang diisi, kiriman **tetap diterima** tetapi diberi tanda NIK_TGL_LAHIR_BEDA / NIK_JK_BEDA. Di form, tampilkan peringatan lembut sebelum kirim: "Tanggal lahir atau jenis kelamin tidak cocok dengan NIK. Periksa lagi. Jika sudah benar, lanjutkan."
- **Usia wajar per tingkat untuk peran Peserta** (dihitung per 12 November 2026): Mula 8-13 tahun, Madya 11-16, Wira 14-19. Di luar itu: tanda USIA_TIDAK_WAJAR + peringatan lembut. Untuk peran lain tidak dicek, kecuali usia di bawah 17 untuk Pimpinan Kontingen/Pembina Pendamping (tanda).
- **Kuota kontingen:** jika jumlah biodata kontingen itu sudah mencapai kuota, kiriman **tetap diterima**, dan kontingen ditandai KUOTA_PENUH di dasbor superadmin. Pengisi tidak perlu melihat pesan apa pun tentang kuota.
- **Nama mirip dalam kontingen yang sama** (misalnya beda spasi/huruf besar): tanda NAMA_MIRIP untuk dicek superadmin.

## Pengalaman pengguna (UX)

- Satu halaman yang dibagi per bagian (bukan wizard panjang). Tombol **Kirim** besar di bawah.
- Validasi langsung saat isian ditinggalkan (blur), dengan pesan jelas di bawah isian. Saat kirim gagal, gulir ke isian pertama yang salah.
- **Draf otomatis** di `localStorage` untuk semua isian teks (termasuk NIK, karena tersimpan di perangkat pengisi sendiri), **kecuali foto**. Saat membuka lagi: "Lanjutkan isian sebelumnya?" Draf dihapus setelah kiriman berhasil dan setelah "Isi untuk orang lain".
- Tombol kirim dikunci setelah ditekan sampai ada respons (cegah kiriman ganda). Server juga menolak kiriman ganda dengan token kiriman sekali pakai.
- Tampilkan **ringkasan sebelum kirim** (layar konfirmasi singkat berisi semua isian kecuali NIK yang disamarkan) dengan tombol "Perbaiki" dan "Ya, kirim".
- Indikator unggah foto (persen) dan pesan jika gagal karena ukuran.
- Pembina sering mengisikan untuk anak yang tidak punya HP. Setelah berhasil, sediakan tombol **"Isi untuk orang lain"** yang mengosongkan form (kecuali utusan sekolah dan tingkat yang tetap terisi).
- Teks ramah dan pendek. Hindari istilah teknis.
- Halaman tetap bisa dipakai bila JavaScript gagal dimuat (form HTML biasa + validasi server), walaupun tanpa pemotong foto.

## Setelah kirim: halaman bukti

- Tampilkan centang besar, "Biodata berhasil dikirim", **kode pendaftaran** (contoh `SJ-7KQ2M4`), nama, sekolah, tingkat, peran, dan waktu kirim.
- Tombol "Simpan bukti" yang mengunduh gambar/PDF kecil bukti (tanpa NIK). Sarankan juga untuk tangkapan layar.
- Pesan: "Jika ada data yang salah, hubungi superadmin dan sebutkan kode pendaftaran ini."
- Tidak ada fitur publik untuk mengubah biodata (keputusan: perbaikan lewat superadmin).

## Perlindungan dari penyalahgunaan

- Rate limit: misalnya 10 kiriman per 10 menit per IP (sekolah bisa memakai satu wifi, jangan terlalu ketat), 3 percobaan gagal NIK dobel per menit.
- Kolom honeypot tersembunyi + waktu minimal pengisian (misalnya kurang dari 20 detik dianggap bot).
- CSRF bawaan Django.
- Jangan pernah membocorkan data orang lain: pesan NIK dobel **tidak** boleh menyebut nama pemilik NIK.

## Halaman superadmin untuk biodata (Tahap 1)

- **Dasbor:** total biodata masuk, per tingkat, per peran, grafik masuk per hari; tabel kontingen dengan kolom kuota, terisi, sisa/lebih, jumlah per peran, jumlah tanda. Warna: hijau sesuai, kuning hampir penuh, merah lebih dari kuota.
- **Daftar biodata:** tabel dengan pencarian (nama, kode pendaftaran, 4 digit terakhir NIK), filter (kontingen, tingkat, peran, jenis kelamin, punya tanda), urutan, paginasi. Kolom: nama, kontingen, tingkat, peran, JK, umur, tanda, waktu masuk. NIK tampil disamarkan.
- **Detail biodata:** semua isian, foto, riwayat perubahan, tanda. Tombol "Lihat NIK lengkap" (tercatat di log).
- **Ubah biodata:** semua isian bisa diubah superadmin, termasuk mengganti foto. Validasi sama dengan form publik (NIK tetap unik). Simpan riwayat di log.
- **Tambah biodata manual** oleh superadmin (untuk yang terlambat atau tidak bisa mengisi).
- **Hapus** -> tempat sampah; **pulihkan** dari tempat sampah; **hapus permanen** dengan konfirmasi ganda.
- **Unduh Excel:**
  - versi umum: tanpa NIK utuh (disamarkan), tanpa alamat dan kontak orang tua;
  - versi lengkap: semua kolom, hanya dengan konfirmasi ulang kata sandi superadmin, tercatat di log.
  - satu sheet per tingkat atau satu sheet gabungan + filter yang sedang aktif.
- **Unduh foto** per kontingen dalam ZIP (nama file = nama orang + kode pendaftaran).
- **Pengaturan form:** jadwal buka/tutup, sakelar paksa, foto wajib, nomor WhatsApp dan nama superadmin, teks pengumuman di halaman form.

## Tes yang wajib ada

- Kiriman valid tersimpan dan foto 600x800.
- NIK bukan 16 digit ditolak; NIK dobel ditolak tanpa membocorkan data.
- Form tertutup menolak kiriman di server.
- Tingkat beda, kuota penuh, NIK tidak cocok -> diterima + tanda.
- Peran dewasa tanpa data ortu diterima; peran Peserta tanpa data ortu ditolak.
- File bukan gambar atau > 5 MB ditolak.
- Akun panitia/juri tidak bisa membuka halaman biodata superadmin.
