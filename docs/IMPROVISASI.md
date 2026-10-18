# Catatan Improvisasi

Semua hal yang **tidak diminta secara eksplisit** oleh panitia/Farhan tetapi ditambahkan karena dibutuhkan, dicatat di sini. Farhan membaca file ini untuk memutuskan apakah suatu tambahan dipertahankan.

**Aturan untuk Claude Code:**
- Boleh dan dianjurkan berimprovisasi untuk hal yang jelas meningkatkan keandalan, keamanan, kemudahan, atau menutup celah yang belum disebut di spesifikasi.
- **Tidak boleh** berimprovisasi yang bertentangan dengan `00-KEPUTUSAN.md` atau mengubah alur yang sudah diputuskan.
- Setiap improvisasi: tambahkan satu baris di tabel bawah (tanggal, tahap, apa, alasan, cara mematikan jika ada).
- Jika ragu dan keputusannya tidak bisa dibatalkan (misalnya menghapus data, mengubah alur publik), **tanya Farhan dulu**.

## Improvisasi yang sudah ditetapkan saat menyusun spesifikasi (oleh Claude di chat, 18 Oktober 2026)

| Tahap | Improvisasi | Alasan |
|---|---|---|
| 1 | ~~Tingkat otomatis terisi dari sekolah yang dipilih, tetap bisa diubah dengan peringatan~~ (diganti REVISI R1: tingkat dipilih dulu, sekolah disaring) | 1 sekolah = 1 kontingen = 1 tingkat menurut pedoman; mengurangi salah pilih. Keputusan brief (pilih sendiri + tanda beda) tetap dihormati |
| 1 | Telepon pribadi wajib hanya untuk Pimpinan Kontingen dan Pembina Pendamping; data orang tua wajib hanya untuk Peserta dan Peninjau | Banyak anak belum punya HP; orang dewasa tidak perlu data orang tua |
| 1 | Nomor induk anggota tidak wajib | Tidak semua punya KTA; pembina mungkin tidak punya |
| 1 | ~~Foto wajib, bisa dimatikan lewat pengaturan~~ (diganti REVISI R2: foto wajib mutlak, dicetak di kartu) | Pedoman meminta foto 3x4; dibuat bisa dimatikan jika menghambat |
| 1 | Pemotong foto 3:4 di browser + pengecilan sebelum unggah + pembersihan EXIF/GPS di server | Unggahan ringan, privasi anak |
| 1 | Kotak centang persetujuan data | Perlindungan data anak (UU 27/2022) |
| 1 | Cek NIK vs tanggal lahir/jenis kelamin, cek usia wajar per tingkat, nama mirip, foto duplikat -> hanya tanda, tidak menolak | Membantu superadmin menemukan salah isi tanpa menghambat pengisi |
| 1 | Draf otomatis, layar ringkasan sebelum kirim, kode pendaftaran + bukti, tombol "Isi untuk orang lain" | Pembina sering mengisikan untuk banyak anak |
| 1 | Honeypot, rate limit, token kiriman sekali pakai | Mencegah spam dan kiriman ganda |
| 1 | Sakelar paksa buka/tutup form | Uji coba sebelum 26 Okt dan perpanjangan |
| 1 | Excel versi umum (disamarkan) dan versi lengkap (konfirmasi sandi + log) | Perlindungan data |
| 1 | Superadmin juga mengisi nama per perangkat | Log jelas walau akun dipakai bersama |
| 2 | Kode kartu pendek tercetak di bawah QR | Input manual jika QR rusak |
| 2 | Warna tingkat di kartu (Mula hijau, Madya biru, Wira kuning) | Sesuai makna bulu enggang di logo Jumbara V |
| 2 | Kunci data biodata sebelum cetak + tanda perlu cetak ulang | Mencegah kartu tidak sama dengan data |
| 2 | Sampul daftar isi per kontingen di PDF kartu | Memudahkan pembagian saat daftar ulang |
| 3 | Titik absen otomatis aktif 60 menit sebelum mulai sampai 60 menit setelah selesai | Panitia sering memindai lebih awal |
| 3 | Info bentrok jika satu orang tercatat di dua kegiatan yang bersamaan (tidak memblokir) | Banyak peserta merangkap kegiatan |
| 3 | Cache daftar peserta ringan di HP pemindai untuk tampilan nama saat offline | Pemindai tetap bisa memastikan pemilik kartu |
| 3 | Screen Wake Lock, getar, bunyi, kunci QR 3 detik | Pemindaian beruntun lebih cepat dan jelas |
| 3 | Poin kehadiran: orang di atas kuota tidak menambah poin (bisa dimatikan) | Mencegah kontingen menambah poin dengan membawa orang lebih banyak |
| 3 | Pantauan langsung titik absen untuk superadmin, rekap harian untuk evaluasi 23.00 | Pedoman: evaluasi malam bersama pimpinan kontingen |
| 3 | Anjangsana: "kunjungi kontingen lain" tanpa pindai kartu ulang selama 30 menit | Mempercepat kunjungan beruntun |
| 3 | Anjangsana: pemecah seri = jumlah kontingen tamu berbeda, lalu total kunjungan | Brief hanya menyebut "paling banyak dikunjungi" |
| 3 | Anjangsana: peringkat gabungan dan per tingkat tuan rumah | Kunjungan antartingkat boleh, tapi juara per tingkat |
| 4 | Agregasi nilai antarjuri (rata-rata bawaan) | Got Talent punya 3 juri; lomba lain mungkin juga |
| 4 | Fungsi rumus `POIN_PERINGKAT`, `PERINGKAT`, `IF`, `ROUND`, koma desimal, `x` sebagai kali | Juara umum mengubah peringkat menjadi poin; pengguna awam |
| 4 | Pemecah seri manual di tabel hasil | Nilai sama sering terjadi |
| 4 | Template penilaian dari pedoman sebagai draf | Mempercepat penyiapan form |
| 5 | Nomor piagam otomatis, pengecualian peserta yang kena sanksi "tidak berhak piagam", syarat sudah daftar ulang | Pedoman BAB VI D (sanksi) |
| Umum | Perintah manajemen Django `sigap_seed`, `sigap_jadwal`, `sigap_cek_lingkungan`, `sigap_uji_beban`, `sigap_hapus_data_uji`, `sigap_anonimkan` | Operasional di Windows |
| Umum | Tailwind lewat CLI standalone dan pustaka JS disimpan di `static/vendor` (tanpa Node.js) | Lebih sedikit yang perlu dipasang di server Windows |
| Umum | Waitress sebagai Windows Service di belakang Apache XAMPP; MariaDB dinaikkan ke 10.5+ bila XAMPP masih 10.4 | Django tidak berjalan di Apache/PHP; Django 5.2 butuh MariaDB 10.5+ |
| Umum | Cadangan tiap 3 jam pada 12-15 November | Data acara paling berharga |

## Improvisasi tambahan oleh Claude Code

| Tanggal | Tahap | Improvisasi | Alasan | Cara mematikan |
|---|---|---|---|---|
| 18 Okt 2026 | 0 | MariaDB 10.11.19 dipasang **berdampingan di port 3307** (bukan menggantikan XAMPP 10.4). Di laptop memakai paket ZIP tanpa installer karena hak admin tidak tersedia | XAMPP 10.4 menyimpan database proyek lain (sik, sikayan, dll.). Keputusan Farhan 18 Okt (varian opsi A) | Pakai port 3306 jika MariaDB XAMPP dimatikan; ubah `DB_PORT` |
| 18 Okt 2026 | 0 | Python 3.12.10 dipasang via winget (per pengguna), berdampingan dengan 3.11 | Keputusan stack Python 3.12; disetujui Farhan | - |
| 18 Okt 2026 | 0 | **NIK disimpan terenkripsi** (Fernet/`cryptography`, kunci `SIGAP_KUNCI_NIK`) + `nik_hash` HMAC-SHA256 (`SIGAP_KUNCI_HASH_NIK`) yang UNIQUE untuk data aktif, + `nik_samar` dan `nik_akhir4` untuk tampilan/pencarian | Dump database yang bocor tidak membuka NIK anak (UU 27/2022). Cek dobel tetap di database | Tidak bisa dimatikan tanpa migrasi data; kunci wajib dicadangkan |
| 18 Okt 2026 | 0 | Kunci UNIQUE hanya untuk data aktif memakai kolom `aktif_key` (1 = aktif, NULL = di tempat sampah) pada peserta (NIK), kontingen (kode), kehadiran, review | MariaDB tidak punya partial index; NIK orang yang biodatanya dihapus boleh dipakai lagi | - |
| 18 Okt 2026 | 0 | `DATABASES.TIME_ZONE = Asia/Makassar`: jam di database tersimpan WITA, Django tidak memakai `CONVERT_TZ` | Tabel zona waktu MariaDB di Windows biasanya kosong sehingga `CONVERT_TZ` menghasilkan NULL (grafik per hari, saringan tanggal) | Jangan diubah setelah ada data |
| 18 Okt 2026 | 0 | Kolom Tahap 2-5 sudah ada sejak migrasi awal: `peserta.qr_token`, `kode_kartu`, `versi_kartu`, `kartu_aktif`, `perlu_cetak_ulang`, `tidak_berhak_piagam`; tabel `kegiatan`, `titik_absen`, `kehadiran`, `pindaian_ditolak`, `kartu_riwayat`, sesi/kunjungan/review Anjangsana | Agar tabel berisi biodata asli tidak perlu dibongkar | - |
| 18 Okt 2026 | 0 | WhiteNoise sebagai cadangan penyaji `/static/` (Apache tetap penyaji utama), dengan nama file ber-hash | Tetap jalan bila diakses langsung lewat Waitress/tunnel; cache browser aman setelah pembaruan | Hapus dari `MIDDLEWARE` |
| 18 Okt 2026 | 0 | CSP ketat (`script-src 'self' 'unsafe-eval'`), semua JS di file statis (tanpa skrip inline), header `Permissions-Policy` hanya izinkan kamera, `Cache-Control: no-store` untuk halaman yang butuh login | Semua aset lokal; halaman superadmin berisi data pribadi. `unsafe-eval` dibutuhkan Alpine versi standar (ini JavaScript browser, bukan rumus form builder) | `HeaderKeamananMiddleware` |
| 18 Okt 2026 | 0 | Baris `sourceMappingURL` dihapus dari berkas vendor JS | `collectstatic` dengan manifest gagal karena file `.map` tidak disertakan | - |
| 18 Okt 2026 | 1 | Batas kiriman form: **30 kiriman berhasil per 10 menit per IP** (yang gagal validasi tidak dihitung), 5 NIK dobel per menit per IP, 5 percobaan masuk per menit per IP+akun | Satu sekolah dan operator seluler (CGNAT) sering berbagi satu IP; spesifikasi meminta tidak terlalu ketat | Konstanta `BATAS_KIRIM`, `BATAS_NIK_DOBEL` di `apps/biodata/views.py` |
| 18 Okt 2026 | 1 | Waktu minimal pengisian 10 detik (bukan 20), bisa diubah di Pengaturan form | Pengisi yang memakai draf tersimpan bisa mengirim < 20 detik. Ditolak dengan pesan ramah, bukan diblokir | Isi 0 di pengaturan |
| 18 Okt 2026 | 1 | Token kiriman sekali pakai ditandatangani + tabel `TokenKiriman`: kiriman ganda (tombol ditekan dua kali/koneksi putus) langsung diarahkan ke bukti yang sama | Mencegah dua biodata dari satu pengisian | - |
| 18 Okt 2026 | 1 | Foto: browser mengecilkan ke sisi 1.600 px dan mengirim koordinat potong; server tetap meluruskan EXIF, memotong 3:4, 600x800, JPEG tanpa EXIF, nama file = kode pendaftaran di folder privat. Bom gambar dibatasi 60 MP | Sesuai spesifikasi + perlindungan dari file berbahaya | - |
| 18 Okt 2026 | 1 | Pencarian sekolah: kotak cari di atas dropdown asli (dropdown tetap ada, dikelompokkan per tingkat) | Pilihan bawaan HP paling ramah; tetap jalan tanpa JavaScript | - |
| 18 Okt 2026 | 1 | Bukti pendaftaran memakai tautan bertanda tangan (berlaku 7 hari), bukan URL dengan kode pendaftaran | Orang lain tidak bisa menebak alamat bukti dan melihat nama/sekolah orang lain | `UMUR_BUKTI` di `apps/biodata/views.py` |
| 18 Okt 2026 | 1 | Bukti PDF ukuran A6 dengan logo PMI + Jumbara V (ReportLab) | Mudah disimpan dan dicetak | - |
| 18 Okt 2026 | 1 | Nama mirip: dibandingkan setelah membuang gelar sesudah koma, huruf besar/kecil, spasi, tanda baca; kemiripan >= 90% dalam kontingen yang sama. Tanda dipasang pada kedua orang | Menangkap salah ketik dan kiriman ganda | - |
| 18 Okt 2026 | 1 | Kuota penuh ditandai pada orang ke-(kuota+1) dan seterusnya menurut urutan masuk; dihitung ulang saat kuota diubah | Superadmin langsung tahu siapa yang di luar kuota | - |
| 18 Okt 2026 | 1 | Hapus permanen biodata wajib mengetik ulang kode pendaftaran (konfirmasi ganda) dan ditolak bila sudah punya kehadiran | Mencegah salah hapus | - |
| 18 Okt 2026 | 1 | Kontingen yang masih punya biodata tidak bisa dihapus; nama/kode kontingen tidak boleh dobel | Mencegah biodata kehilangan kontingen | - |
| 18 Okt 2026 | 1 | Login admin bawaan Django (`/django-admin/login/`) dialihkan ke halaman masuk SIGAP | Halaman masuk SIGAP punya batas percobaan | `sigap/urls.py` |
| 18 Okt 2026 | 1 | Ganti sandi akun sendiri: perangkat yang sedang dipakai tetap masuk, perangkat lain keluar. Ada tombol "Keluarkan semua perangkat" tanpa mengganti sandi | Superadmin tidak perlu masuk ulang setelah mengganti sandinya | - |
| 18 Okt 2026 | 1 | Pengingat "kata sandi masih bawaan" di setiap halaman superadmin sampai diganti | Daftar periksa 25 Okt | - |
| 18 Okt 2026 | 1 | Halaman perantara setelah masuk meminta nama pemakai perangkat (superadmin) lalu kembali ke menu terakhir; saringan tabel diingat per perangkat; tombol "Ganti nama" dan "Lupakan perangkat ini" | Spesifikasi 10-AKUN-SESI | - |
| 18 Okt 2026 | 1 | Jam sesi berakhir dihitung dari sisa detik di server (bukan jam HP) dan ditulis dalam WITA | Jam HP sering salah atau zona lain | - |
| 18 Okt 2026 | 1 | Mode perawatan dan halaman galat 400/403/404/500/429/CSRF dalam Bahasa Indonesia | Spesifikasi 19 dan 21 | Pengaturan form > Sistem |
| 18 Okt 2026 | 1 | Pengaturan tambahan: waktu minimal pengisian, tanggal acuan usia (12 Nov 2026), tanggal acara untuk cadangan 3 jam | Tidak ditulis mati di kode (aturan emas 8) | - |
| 18 Okt 2026 | 1 | Cadangan berupa satu ZIP (database.sql + foto + BACA-SAYA.txt), sandi database lewat file opsi sementara, kunci berkas agar tidak dobel, cadangan otomatis sebelum `perbarui.ps1` | Pemulihan sederhana dan aman | - |
| 18 Okt 2026 | 1 | Service Waitress memakai WinSW (bergantung pada service MariaDB, restart otomatis, log bergulir) | Spesifikasi 21 | `pasang-service.ps1 -Hapus` |
| 18 Okt 2026 | 1 | Playwright (hanya di virtualenv laptop, tidak di `requirements.txt`) untuk uji tampilan 360 px dengan Chrome terpasang | Memeriksa tampilan HP dan alur JavaScript secara otomatis | `pip uninstall playwright` |
| 18 Okt 2026 | 1 | Daftar sekolah dibangun ulang (opsi dihapus/ditambah) saat tingkat berganti, bukan disembunyikan | `<option hidden>` tidak berlaku di Safari iPhone | - |
| 18 Okt 2026 | 1 | Teks bantuan tingkat: "Mula = SD/MI, Madya = SMP/MTs, Wira = SMA/SMK/MA" | Membantu anak/guru memilih tingkat sebelum sekolah | Ubah teks di `form.html` |
| 18 Okt 2026 | 1 | Superadmin tetap boleh menyimpan tingkat yang beda dengan sekolah (diberi tanda TINGKAT_BEDA); hanya form publik yang menolak | Superadmin perlu memindahkan orang antar kontingen dan menangani kasus khusus | Tambahkan cek di `BiodataForm.clean` untuk mode superadmin |
| 18 Okt 2026 | 1 | Teks bantuan SIAMO ditambah "Kosongkan jika belum punya."; teks foto dirapikan menjadi "Foto akan dicetak di kartu peserta dan disimpan sebagai arsip panitia." | Teks lama "Foto hanya arsip, dicetak di kartu" bertentangan; anak tanpa nomor SIAMO tidak bingung | Ubah teks di `form.html`/`forms.py` |
| 18 Okt 2026 | 1 | Isian nama tampil kapital saat diketik (`uppercase`, `autocapitalize=characters`) dan ringkasan sebelum kirim menampilkan kapital | Pengisi melihat bentuk yang akan disimpan | - |
| 18 Okt 2026 | 1 | Migrasi `biodata.0002_nama_kapital` mengubah nama yang sudah ada ke kapital | Data lama (saat ini hanya data uji) seragam | - |
| 18 Okt 2026 | 1 | Mode pengembangan: statis dilayani WhiteNoise dengan `max-age=0` | Browser memakai JS lama dari cache saat uji di laptop (R1b) | Hapus `whitenoise.runserver_nostatic` dari `INSTALLED_APPS` |
| 18 Okt 2026 | 1 | Kotak cari sekolah selalu tampil; disentuh menampilkan semua sekolah tingkat terpilih, Enter memilih hasil teratas, jumlah sekolah per tingkat ditampilkan | Permintaan Farhan: pencarian harus tetap ada; memudahkan di HP | - |
