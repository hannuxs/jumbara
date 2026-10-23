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
| 1 | ~~Cek NIK vs tanggal lahir/jenis kelamin~~ (dihapus REVISI R4), cek usia wajar per tingkat, nama mirip, foto duplikat -> hanya tanda, tidak menolak | Membantu superadmin menemukan salah isi tanpa menghambat pengisi |
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
| 18 Okt 2026 | 1 | Tag template `{% aset %}`: alamat CSS/JS diberi versi otomatis (`?v=` waktu ubah file) saat pengembangan | Browser tidak pernah memadukan halaman baru dengan CSS/JS lama (R1c) | Ganti kembali ke `{% static %}` |
| 18 Okt 2026 | 1 | Ikon kaca pembesar di kotak cari sekolah dihapus | Ikon tanpa CSS menutupi form (R1c); tulisan petunjuk sudah cukup | - |
| 18 Okt 2026 | 1 | Migrasi `biodata.0003_hapus_tanda_nik` menghapus tanda lama NIK_TGL_LAHIR_BEDA/NIK_JK_BEDA dari database (data turunan, bukan biodata); tes otomatis memastikan pencocokan itu tidak muncul lagi | Permintaan Farhan: tidak boleh ada pencocokan NIK (REVISI R4) | - |
| 18 Okt 2026 | 1 | Pemotong foto dipasang setelah wadah tampil + `ResizeObserver`; tinggi `clamp(280px, 65vh, 600px)` | Foto tampil kecil 200x100 bila Cropper dipasang saat wadah tersembunyi (R5) | - |
| 18 Okt 2026 | 1 | Tombol Perbesar/Perkecil di pemotong foto | Laptop tidak bisa mencubit layar (R5) | Hapus tombol di `form.html` |
| 18 Okt 2026 | 1 | Pemuatan foto bertingkat (blob URL, FileReader, lalu kirim foto asli tanpa pratinjau) | Pengisi tidak pernah terhalang bila browser gagal menampilkan foto tertentu (R5) | - |
| 18 Okt 2026 | 1 | Mesin WebKit dan Firefox untuk Playwright dipasang di laptop (`%LOCALAPPDATA%\ms-playwright`), hanya untuk uji | Menguji tampilan Safari/iPhone dan Firefox tanpa perangkat fisik (R5) | `python -m playwright uninstall` |
| 22 Okt 2026 | 1 | Skrip `scripts/windows/mariadb-dev.ps1` (nyalakan MariaDB pengembangan, cek status, pasang sebagai service) dan petunjuk di `sigap_cek_lingkungan` saat database tidak bisa dihubungi | MariaDB laptop mati setelah restart sehingga `runserver` gagal | Hapus skrip |
| 22 Okt 2026 | 1 | `jalankan.bat` + `web/scripts/windows/jalankan.ps1`: satu perintah memeriksa kesiapan (Python, paket, .env, MariaDB dinyalakan bila mati, versi database, migrasi, data awal, CSS, collectstatic, sigap_cek_lingkungan, port, IP untuk HP) lalu menjalankan server; pilihan -CekSaja, -Port, -Produksi, -Tes | Permintaan Farhan: satu perintah untuk cek menyeluruh dan menjalankan server dengan mudah | Hapus kedua file |
| 22 Okt 2026 | 1 | Pesan peringatan `sigap_cek_lingkungan` menyebut masalahnya (misal "Sandi akun superadmin MASIH BAWAAN"), bukan kondisi yang diharapkan | Pesan lama terbaca terbalik dan membingungkan | - |
| 22 Okt 2026 | 1 | Header `Cross-Origin-Opener-Policy` hanya dikirim lewat HTTPS (bawaan Django dimatikan) | Browser memberi peringatan konsol saat diuji lewat http://IP-laptop | `SECURE_CROSS_ORIGIN_OPENER_POLICY` di settings |
| 22 Okt 2026 | 2 | Token kartu 26 karakter dari 31 huruf/angka tanpa 0/O/1/I/L (sekitar 128,8 bit); `kode_kartu` = 8 karakter pertama token; dicek unik juga terhadap kartu lama | Spesifikasi 13 (>= 128 bit, kode bagian dari token); kode lama tidak dipakai ulang agar tidak membingungkan | - |
| 22 Okt 2026 | 2 | QR digambar sebagai vektor (bukan gambar), koreksi galat Q, tepi putih 2 modul (kartu) dan 3 modul (QR tenda) | Tajam di printer apa pun; tetap terbaca bila sedikit kotor | - |
| 22 Okt 2026 | 2 | Sampul PDF kartu berisi tabel No, Nama, Peran, Kode kartu, Lembar-Posisi, dan kolom centang | Memudahkan pembagian kartu saat daftar ulang | - |
| 22 Okt 2026 | 2 | Kaki kartu menampilkan kode kontingen dan versi kartu (v1, v2, ...) | Panitia bisa membedakan kartu lama dan kartu pengganti | - |
| 22 Okt 2026 | 2 | Nonaktifkan kartu tanpa kartu pengganti (orang batal ikut) dan aktifkan lagi | Kasus yang tidak disebut spesifikasi tetapi pasti terjadi | - |
| 22 Okt 2026 | 2 | Tanda perlu cetak ulang dihapus dengan tombol "Sudah dicetak" (per orang, per kontingen), bukan otomatis saat unduh | Unduhan bisa gagal/tidak jadi dicetak; tanda hanya hilang bila superadmin yakin sudah dicetak | - |
| 22 Okt 2026 | 2 | Perubahan yang menandai cetak ulang setelah data dikunci: nama, peran, kontingen, tingkat, foto (bukan alamat/kontak); biodata baru saat terkunci langsung ditandai perlu dicetak | Hanya isian yang tercetak di kartu | `ISIAN_TERCETAK` di `apps/kartu/services.py` |
| 22 Okt 2026 | 2 | Ukuran kartu disimpan di pengaturan (`kartu.lebar_mm`, `kartu.tinggi_mm`, bawaan 88 x 125) | Spesifikasi: ukuran mudah diganti | - |
| 22 Okt 2026 | 2 | Fungsi `kenali()` (isi QR/kode ketikan -> BERHASIL, KARTU_NONAKTIF, KARTU_TIDAK_DIKENAL, BUKAN_KARTU_PESERTA, QR_ASING) dibuat sekarang | Dipakai pemindai Tahap 3; diuji bersama Tahap 2 | - |
| 22 Okt 2026 | 2 | Tes otomatis merender PDF dan memindai QR di dalamnya (pypdfium2 + OpenCV, hanya `requirements-dev.txt`) | Memastikan QR yang tercetak benar-benar terbaca dan isinya tepat | - |
| 22 Okt 2026 | 2 | Perbaikan: tombol "Cetak ringkasan" di detail kontingen memakai `onclick` yang diblokir CSP; diganti Alpine `@click` | Tombol sebelumnya tidak berfungsi | - |
| 22 Okt 2026 | 3 | Pindaian tidak ditulis ke log aktivitas satu per satu; jejaknya ada di tabel kehadiran (pemindai, perangkat, jam pindai dan jam diterima) dan pindaian ditolak. Pembatalan, tambah manual, dan perubahan titik tetap masuk log | Ribuan pindaian akan membanjiri log dan memperlambat transaksi pindai | Panggil `catat()` di `absensi/services.pindai` |
| 22 Okt 2026 | 3 | Titik absen berstatus Otomatis terbuka 60 menit sebelum mulai sampai 60 menit setelah selesai (`absensi.menit_sebelum/sesudah` di pengaturan); superadmin tetap bisa memindai di titik tertutup | Peserta sering datang lebih awal/terlambat; superadmin perlu memperbaiki | Ubah angka di pengaturan |
| 22 Okt 2026 | 3 | Pindaian offline dinilai menurut jam pindai di HP (bukan jam tiba di server), jam HP yang meleset > 10 menit ke depan atau > 2 hari ke belakang tidak dipercaya | Antrean yang terkirim setelah titik tutup tetap sah | `baca_permintaan` di `absensi/services.py` |
| 22 Okt 2026 | 3 | HP menyimpan daftar ringan peserta per titik (id, hash 16 karakter token, kode kartu, nama, kontingen) agar nama tetap tampil saat offline; token asli tidak dikirim | Pemindai tetap informatif tanpa sinyal, tanpa membocorkan token kartu | - |
| 22 Okt 2026 | 3 | Halaman rekap segar otomatis setiap 10 detik (kecuali yang untuk dicetak/diunduh) dengan posisi gulir dipertahankan | Spesifikasi meminta polling; tanpa WebSocket | Hapus `data-segar` di template |
| 22 Okt 2026 | 3 | qr-scanner disimpan di `static/vendor/qr-scanner/` dengan nama file asli | Pustaka memuat worker dengan alamat relatif | - |
| 22 Okt 2026 | 3 | Anjangsana memakai tiket bertanda tangan Django (`signing`), tanpa sesi server: identitas 30 menit, tiket kunjungan 60 menit | Tanpa login dan tanpa menyimpan sesi untuk ratusan pengunjung; tiket tidak bisa dipalsukan | - |
| 22 Okt 2026 | 3 | Batas Anjangsana: 30 kunjungan per jam per kartu, dan 240 permintaan per menit per IP (longgar karena CGNAT operator seluler) | Spesifikasi meminta batas per kartu dan per IP | `BATAS_KUNJUNGAN_PER_JAM` dan `BATAS_IP` |
| 22 Okt 2026 | 3 | Peringkat Anjangsana seri: jumlah kontingen tamu berbeda, lalu jumlah kunjungan, lalu kode kontingen; peringkat sama bila ketiganya sama. Review yang dihapus (iseng) tidak dihitung dan kontingen tamu itu boleh mengirim review baru | Diminta spesifikasi untuk dicatat | `peringkat()` di `anjangsana/services.py` |
| 22 Okt 2026 | 3 | Kirim review bersamaan dari dua anggota kontingen yang sama: yang kedua mendapat peringatan "baru saja" dan bisa mengirim lagi untuk mengganti | Kunci UNIQUE mencegah dua review, pengguna tetap mendapat pesan jelas | - |
| 22 Okt 2026 | 3 | Kelola sesi Anjangsana menolak sesi yang bertumpuk pada tanggal yang sama dan jam selesai sebelum mulai; menghapus sesi tidak menghapus kunjungan | Mencegah salah ketik jadwal | - |
| 22 Okt 2026 | 3 | Uji beban memakai data uji tersembunyi (kontingen "UJI-BEBAN" berstatus terhapus, titik `UB-xxxx-..`) di database server yang diuji, lalu menghapusnya lagi hanya berdasarkan ID buatannya; memakai akun panitia yang ada lewat sesi sementara (sandi tidak diubah); wajib `--ya` bila DEBUG=False. Berbeda dari `22-PENGUJIAN.md` (database terpisah) | Menguji server sungguhan (Apache + Waitress + MariaDB yang sama) tanpa harus memasang instans kedua; data uji tidak terlihat di form publik/rekap | Opsi `--simpan-data` untuk menahan data; jangan jalankan setelah acara dimulai |
| 22 Okt 2026 | 3 | `sigap_https_dev` + `jalankan.bat -Https`: server uji HTTPS dengan sertifikat self-signed untuk localhost dan IP laptop (dibuat ulang otomatis bila IP berubah, berlaku 30 hari, disimpan di folder privat) | Kamera HP butuh HTTPS; Cloudflare Tunnel tidak dipakai (keputusan Farhan) | Hapus perintah dan opsi `-Https` |
| 22 Okt 2026 | 1 | Perintah `sigap_atur_sandi` (`<akun>` ketik sandi tersembunyi, atau `--semua --dari-env`): setel ulang sandi dari server, ditandai perlu diganti (diingatkan `sigap_cek_lingkungan`), semua perangkat dikeluarkan, tercatat di log | Mengubah `SIGAP_SANDI_AWAL_*` di `.env` tidak mengubah sandi akun yang sudah ada; superadmin yang lupa sandi tidak punya jalan lain | Hapus perintah |
| 22 Okt 2026 | 3 | Pemindai: pindaian yang sedang dikirim (kurang dari 10 detik dan belum gagal) tidak dihitung "menunggu" sehingga spanduk kuning "tersimpan di HP" hanya muncul bila benar-benar tertahan | Uji HP sungguhan Farhan: spanduk sempat muncul sesaat untuk pindaian yang sebenarnya berhasil terkirim | `BATAS_SEDANG_KIRIM_MS` di `pemindai.js` |
| 22 Okt 2026 | 3 | Pemindai: kartu yang sama di titik yang sama yang masih tertahan di antrean tidak ditambahkan lagi; tampil "Sudah tersimpan di HP" | Saat offline, kamera yang terus melihat kartu yang sama menambah antrean ganda setiap 3 detik (server tetap aman karena UNIQUE, tetapi angka menunggu membingungkan) | `cariDiAntrean` di `pemindai.js` |
| 23 Okt 2026 | 4 | Isian kiriman disimpan sebagai JSON {kode: nilai}; Excel memakai kode kolom sebagai kepala | Form bisa diubah superadmin tanpa migrasi; data tetap mudah diekspor (rencana aspek statis setelah acara) | - |
| 23 Okt 2026 | 4 | Kunci REF bersama (`kunci_ref`) untuk form yang sama di tingkat berbeda | Spesifikasi meminta REF mencari form sesuai tingkat subjek | Isi REF dengan slug lengkap |
| 23 Okt 2026 | 4 | Angka berkoma tanpa spasi di dalam fungsi (`MAX(1,2)`) ditolak dengan saran | Menghindari salah tafsir diam-diam antara koma desimal dan pemisah argumen | - |
| 23 Okt 2026 | 4 | Fungsi tambahan AND, OR, NOT, nama Indonesia JUMLAH/RATA/BULAT/JIKA, `:` dan `÷` sebagai bagi | Memudahkan superadmin awam | - |
| 23 Okt 2026 | 4 | Satu kiriman per juri per subjek dikenali dari Nama Juri (tanpa membedakan huruf besar); kiriman ulang setelah dibuka superadmin mengganti nilai dengan riwayat | Akun juri dipakai bersama sehingga nama adalah identitas juri | - |
| 23 Okt 2026 | 4 | Subjek yang belum dinilai juri tidak diberi peringkat akhir | Tanpa ini, kontingen yang belum dinilai ikut berperingkat dari poin kehadiran saja | Logika di `hasil.py` langkah 4 |
| 23 Okt 2026 | 4 | Form publik tidak boleh subjek per orang dan tidak boleh mode penilaian | Daftar nama anak tidak boleh tampil di halaman publik (UU PDP) | `FormPengaturan.clean` |
| 23 Okt 2026 | 4 | Berkas unggahan: daftar jenis yang dilarang (exe, html, svg, js, ...), batas 20 MB, isi file dicek sesuai jenis, disimpan privat dengan nama acak, unduh hanya superadmin (tercatat log) | Keamanan unggahan publik | `forms.py` |
| 23 Okt 2026 | 4 | Kiriman form memakai `client_uuid` | Tombol kirim ditekan dua kali / sinyal putus tidak membuat kiriman ganda | - |
| 23 Okt 2026 | 4 | Semua 40 form template ditandai "perlu konfirmasi panitia" | Aspek dan bobot final dari panitia menyusul 5 Nov | Ubah centang di database |
| 23 Okt 2026 | 4 | Tabel hasil di HP menampilkan nilai kolom peringkat di bawah nama subjek | Kolom nilai akhir tersembunyi di kanan tabel pada layar 360 px | Hapus baris `sm:hidden` di `admin_hasil.html` |
| 23 Okt 2026 | 2 | Desain kartu R7: gradasi tingkat, kapsul logo, foto berbingkai, pita kaki; foto diperkecil ke 20 x 26,7 mm agar QR tetap 45 mm | Permintaan desain modern; spesifikasi QR minimal 45 mm | `gambar_kartu` di `apps/kartu/pdf.py` |
| 23 Okt 2026 | 2 | Baris Nomor Induk Anggota tidak dicetak bila kosong | Kartu tidak menampilkan isian kosong | - |
| 23 Okt 2026 | 4 | Halaman form juri otomatis memakai Nama Juri yang tersimpan di perangkat | Juri tidak perlu mengetik ulang setelah keluar/sesi habis (R8) | `namaJuri` di `isian.js` |
| 23 Okt 2026 | 1 | Tempat sampah umum (`apps/inti/sampah.py`) dengan pemeriksaan bentrok sebelum memulihkan | Semua data soft delete bisa dipulihkan dari satu halaman (R9) | - |
