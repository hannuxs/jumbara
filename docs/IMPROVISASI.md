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
| 1 | Tingkat otomatis terisi dari sekolah yang dipilih, tetap bisa diubah dengan peringatan | 1 sekolah = 1 kontingen = 1 tingkat menurut pedoman; mengurangi salah pilih. Keputusan brief (pilih sendiri + tanda beda) tetap dihormati |
| 1 | Telepon pribadi wajib hanya untuk Pimpinan Kontingen dan Pembina Pendamping; data orang tua wajib hanya untuk Peserta dan Peninjau | Banyak anak belum punya HP; orang dewasa tidak perlu data orang tua |
| 1 | Nomor induk anggota tidak wajib | Tidak semua punya KTA; pembina mungkin tidak punya |
| 1 | Foto wajib, bisa dimatikan lewat pengaturan | Pedoman meminta foto 3x4; dibuat bisa dimatikan jika menghambat |
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
| | | | | |
