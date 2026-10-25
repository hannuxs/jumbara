# 13. Kartu Peserta dan QR Kontingen (Tahap 2)

## Token QR peserta

- Setiap biodata mendapat `qr_token` acak, **minimal 128 bit entropi**, dikodekan base32/base62 tanpa karakter membingungkan. Contoh isi QR: `SJP:K7Q2M4XA9T3RZ8WC` (awalan `SJP:` = peserta).
- QR **tidak boleh** berisi NIK, nama, ID database berurutan, atau URL yang membocorkan data.
- `kode_kartu` 8 karakter (contoh `K7Q2-M4XA`) dicetak di bawah QR, untuk diketik manual oleh pemindai jika QR rusak. Kode ini bagian dari token tapi lebih pendek; tetap unik.
- Kartu hilang/rusak: superadmin menekan "Nonaktifkan dan terbitkan kartu baru" -> token lama masuk `kartu_riwayat`, `versi_kartu` naik, token baru dibuat. Token lama yang dipindai -> merah "Kartu sudah dinonaktifkan. Gunakan kartu terbaru."
- Token dibuat saat biodata masuk (atau massal saat Tahap 2 dimulai). Perubahan nama/peran/kontingen setelah kartu dicetak -> tanda `perlu_cetak_ulang`.

## Token QR kontingen

- Setiap kontingen punya `qr_token` sendiri dengan awalan `SJK:` (kontingen). Contoh: `SJK:9XQ4T2...`.
- Bisa diganti superadmin (misalnya QR tenda rusak/disalahgunakan).
- Pemindai absensi yang menangkap QR kontingen -> merah "Ini QR kontingen, bukan kartu peserta." Halaman Anjangsana yang menangkap kartu peserta saat meminta QR tuan rumah -> pesan sebaliknya.

## Desain kartu B-2

- Ukuran **88 x 125 mm potret** (B-2, sekitar 8,8 x 12,5 cm). Simpan ukuran di konfigurasi agar mudah diganti jika panitia memakai ukuran B-2 yang sedikit berbeda.
- **4 kartu per lembar F4** (215 x 330 mm): 2 kolom x 2 baris, jarak antar kartu kecil, **garis potong** (crop marks) di sudut dan garis putus-putus tipis di antara kartu. Pastikan skala cetak 100% (beri catatan di PDF: "Cetak dengan skala 100%/Actual size, kertas F4").
- **Desain terbaru: REVISI R7b (23 Okt 2026)**: seluruh kartu berlatar gradasi warna tingkat, QR 45 mm + kode kartu di pelat putih, logo di kapsul putih, foto 24 x 32 mm, lencana tingkat kecil, Nomor Induk Anggota di bawah nama. Rincian di `REVISI.md`. Daftar di bawah adalah rancangan awal.
- Isi kartu (atas ke bawah):
  1. Kepala berlatar putih: **logo PMI (wajib, permintaan panitia)** di kiri (`assets/brand/pmi-logo-2026.png`, mendatar berlatar putih, sejak R13) dan logo Jumbara V di kanan (`assets/brand/jumbara-v-logo.jpg`), di antaranya teks "JUMBARA PMR TINGKAT KABUPATEN BULUNGAN V 2026" dan tema "Unggul - Responsif - Berkarakter". Ikuti aturan logo di `assets/brand/README.md` (logo PMI tidak boleh diubah warna/bentuk, latar terang, ruang kosong di sekeliling).
  2. Pita warna peran/tingkat (lihat warna di bawah) bertuliskan PERAN (PESERTA / PIMPINAN KONTINGEN / PEMBINA PENDAMPING / PENINJAU).
  3. **Foto 3x4** peserta (REVISI R2; sekitar 24 x 32 mm, dari foto 600x800 di folder privat, bingkai tipis) di samping atau di atas nama.
  4. **NAMA** (huruf besar, tebal, ukuran otomatis mengecil agar muat maksimal 2 baris).
  5. Kontingen (nama sekolah) dan tingkat.
  6. **QR besar** (minimal 45 x 45 mm, error correction level M atau Q, margin putih cukup).
  7. `kode_kartu` di bawah QR, huruf monospace.
  8. Kaki kecil: "Kartu wajib dipakai selama kegiatan" dan kode kontingen.
- **Dengan foto** (REVISI R2, 18 Okt 2026; sebelumnya tanpa foto). Foto wajib mutlak di form, jadi setiap biodata punya foto. Penggantian foto setelah kartu dicetak menandai `perlu_cetak_ulang`. Tata letak harus tetap memberi QR minimal 45 x 45 mm.
- Warna tingkat diambil dari makna logo Jumbara V: **Mula hijau, Madya biru, Wira kuning**. Warna peran boleh dibedakan dengan pita kedua atau ikon. Pastikan tetap terbaca bila dicetak hitam putih (teks tingkat dan peran tetap tertulis).
- Tidak ada data pribadi lain di kartu.

## Pencetakan

- Superadmin memilih: satu kontingen, beberapa kontingen, atau semua. Hasil: satu PDF per kontingen (nama file `Kartu_{kode}_{nama}.pdf`), dan opsi ZIP semua.
- Urutan dalam satu kontingen: Pimpinan Kontingen, Pembina Pendamping, Peserta (urut nama), Peninjau.
- Halaman pertama setiap PDF kontingen boleh berupa sampul daftar isi (nama kontingen, jumlah kartu, daftar nama) untuk memudahkan pembagian saat daftar ulang.
- Cetak satu kartu (cetak ulang) untuk satu orang, diletakkan di posisi 1 dari 4.
- Opsi "hanya yang perlu cetak ulang".
- Sebelum cetak massal, superadmin menekan **Kunci data biodata**: form publik tertutup, perubahan selanjutnya ditandai `perlu_cetak_ulang`.

## Lembar QR kontingen (F4)

- Satu lembar F4 potret per kontingen: logo PMI dan logo Jumbara V di atas, nama kontingen besar, kode, tingkat (dengan warna tingkat), **QR sangat besar** (sekitar 150 x 150 mm), instruksi singkat: "ANJANGSANA: Tamu, pindai QR ini lewat link Anjangsana untuk mengisi buku tamu dan review", dan alamat link Anjangsana.
- Unduh per kontingen atau semua dalam satu PDF.

## Uji

- Pindai hasil cetak (atau PDF di layar laptop) dengan beberapa HP Android dan iPhone dari jarak 20-50 cm.
- Pastikan nama terpanjang di data tetap muat.
