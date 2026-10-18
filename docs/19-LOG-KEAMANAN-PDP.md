# 19. Riwayat Aktivitas, Keamanan, dan Perlindungan Data Pribadi

## Riwayat aktivitas (log)

- Setiap pemindaian, pengisian nilai, perubahan, penghapusan, pemulihan, penggantian kata sandi, pembukaan kunci nilai, penonaktifan kartu, ekspor data lengkap, dan pembukaan NIK utuh **tercatat** dengan nama pelaku (nama pemindai/juri/superadmin per perangkat), akun, waktu, IP, perangkat, data sebelum dan sesudah.
- Halaman log untuk superadmin: filter per aksi, akun, nama, tanggal, subjek; unduh Excel.
- Log tidak bisa dihapus dari aplikasi.

## Tempat sampah

- Biodata, kontingen, kehadiran, kiriman form, review Anjangsana yang dihapus masuk tempat sampah (soft delete).
- Superadmin bisa memulihkan atau menghapus permanen (konfirmasi ganda).
- Memulihkan biodata yang NIK-nya sudah dipakai biodata lain -> tolak dengan pesan jelas.

## Cadangan otomatis

- Setiap hari pukul 02.00 WITA (dan setiap 3 jam pada 12-15 November): `mysqldump` (dari `C:\xampp\mysql\bin\mysqldump.exe`, path di `web\.env`) + arsip folder foto, disimpan di folder cadangan (path di `web\.env`, sebaiknya disk lain), dikompres, simpan 14 hari terakhir.
- Tombol "Buat cadangan sekarang" dan daftar cadangan di menu superadmin (unduh oleh superadmin saja).
- Panduan memulihkan cadangan di `21-DEPLOY-WINDOWS.md`. Uji pemulihan sekali sebelum 25 Oktober.

## Keamanan aplikasi

- HTTPS wajib di produksi; cookie `secure`, `httponly`, `samesite=lax`.
- `DJANGO_DEBUG=False` di produksi dan `python manage.py check --deploy` bersih. Halaman galat ramah dalam Bahasa Indonesia, tanpa jejak teknis.
- Throttle login dan endpoint publik (form biodata, Anjangsana).
- Validasi semua input di server. Unggahan: periksa MIME asli, ukuran, simpan di luar `public`, nama file acak.
- Header keamanan dasar (X-Content-Type-Options, X-Frame-Options/frame-ancestors, Referrer-Policy). CSP sederhana karena semua aset lokal.
- Jangan pernah mencatat kata sandi atau token di log.
- Folder privat (foto, unggahan, cadangan), `web\.env`, dan kode sumber tidak boleh bisa diakses dari web. Apache hanya menyajikan `web\staticfiles\` di `/static/`, selebihnya diteruskan ke Waitress.

## Perlindungan data pribadi (UU No. 27 Tahun 2022)

Sebagian besar peserta adalah anak di bawah umur. Web menyimpan NIK, tanggal lahir, alamat, kontak orang tua, dan foto.

- **NIK disamarkan** di layar dan di unduhan umum: tampilkan 4 digit awal dan 4 digit akhir, contoh `6501********0003`. NIK utuh hanya di detail superadmin setelah klik "Lihat NIK" (tercatat di log) dan di Excel versi lengkap.
- Pertimbangkan enkripsi NIK di database (lihat `03-DATA-MODEL.md`).
- **Biodata lengkap dan foto hanya untuk superadmin.** Akun panitia dan juri hanya melihat nama, kontingen, tingkat, peran.
- **Halaman publik tidak pernah menampilkan data pribadi orang lain**: pesan NIK dobel tidak menyebut nama; halaman Anjangsana hanya menampilkan nama pengunjung itu sendiri dan nama kontingen.
- Persetujuan pengisi (kotak centang) disimpan waktunya.
- Setelah acara selesai dan laporan diserahkan, data pribadi diarsipkan atau dihapus sesuai kesepakatan dengan panitia. Sediakan perintah `python manage.py sigap_anonimkan` yang menghapus NIK, alamat, kontak, dan foto tetapi mempertahankan nama, kontingen, kehadiran, dan nilai untuk laporan. Perintah ini **tidak** dijalankan otomatis.
