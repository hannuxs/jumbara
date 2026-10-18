# 17. Anjangsana (Tahap 3)

Kunjungan antarkontingen pada **Jumat 13 dan Sabtu 14 November 2026**. Pedoman: setiap kontingen disediakan QR untuk kehadiran tamu; tamu memindai dan mengisi buku tamu; setiap kontingen tamu punya satu hak suara untuk menilai tuan rumah.

## Link publik

- Satu link yang sama untuk semua peserta, misalnya `https://<domain>/anjangsana`. Dibagikan ke grup pimpinan kontingen dan dipajang sebagai QR di sekretariat (sediakan PDF poster QR link ini di menu superadmin).
- **Hanya aktif selama sesi** (`data/sesi_anjangsana.csv`, bisa diubah superadmin): 08.00-11.30, 13.30-17.30, 20.00-22.00 WITA, 13 dan 14 November. Di luar sesi: tampilkan "Anjangsana sedang tidak berlangsung. Sesi berikutnya: Sabtu 14 November pukul 08.00." Superadmin bisa buka/tutup paksa.
- Tanpa login. Kamera dipakai di HP pengunjung (wajib HTTPS). Sediakan juga isian manual `kode_kartu` untuk kartu yang QR-nya rusak.

## Alur (teks konfirmasi harus persis)

1. Pengunjung membuka link publik. Layar: judul Anjangsana, sesi yang sedang berlangsung, tombol "Pindai kartu saya".
2. **Pindai kartu sendiri** (QR `SJP:`). Jika kartu tidak dikenal/nonaktif -> pesan merah. Jika yang terpindai QR kontingen -> "Ini QR kontingen. Pindai kartu peserta Anda dulu."
3. **Konfirmasi pertama**, persis:
   > "Apakah benar Anda berasal dari Kontingen **{nama kontingen tamu}** dan akan mengisi review ke kontingen yang Anda kunjungi?"

   Tampilkan juga nama pengunjung (supaya ia yakin kartunya sendiri). Tombol "Ya, benar" dan "Bukan, ulangi".
4. **Pindai QR kontingen tuan rumah** yang ditempel di tenda (QR `SJK:`). Jika memindai QR kontingennya sendiri -> merah "Anda tidak bisa mengunjungi kontingen sendiri." Kunjungan **antartingkat diperbolehkan**.
5. **Konfirmasi kedua**, persis:
   > "Apakah benar Anda berasal dari Kontingen **{nama kontingen tamu}** dan akan mengisi review ke Kontingen **{nama kontingen tuan rumah}**?"
6. Setelah "Ya": **kunjungan tercatat** (`anjangsana_kunjungan`), lalu muncul form review.
7. Form review: nilai **1 sampai 5** (bintang atau tombol angka besar) untuk **Pengetahuan**, **Keterampilan**, dan **Sikap**, ditambah **Komentar** (opsional, maks 500 karakter). Beri penjelasan singkat tiap aspek dari pedoman:
   - Pengetahuan: pemahaman isu remaja yang dikampanyekan.
   - Keterampilan: pengemasan kampanye, suasana kontingen yang nyaman, bersih, dan rapi.
   - Sikap: kerja sama tim, keaktifan, cara menyambut tamu.
8. Kirim -> layar terima kasih + tombol "Kunjungi kontingen lain" (langsung ke langkah 4 dengan identitas yang sama, tanpa memindai kartu lagi selama 30 menit di perangkat itu; tetap tampilkan konfirmasi kedua).

## Aturan

- **Satu review per kontingen tamu untuk setiap tuan rumah** (UNIQUE `kontingen_tamu_id` + `kontingen_tuan_rumah_id`). Jika anggota lain dari kontingen tamu yang sama mengirim review lagi ke tuan rumah yang sama, tampilkan **peringatan** sebelum form review:
  > "Kontingen Anda sudah memberi review ke Kontingen {B} pada {jam}. Jika Anda lanjut, review sebelumnya akan diganti."

  Jika lanjut dan kirim, review lama disimpan di `riwayat` lalu diganti. Kunjungan tetap tercatat sebagai kunjungan baru.
- Peserta dengan peran apa pun boleh menjadi pengunjung (pedoman: kontingen memilih sendiri perwakilan yang memakai hak suara).
- Tidak menampilkan data pribadi selain nama pengunjung itu sendiri dan nama kontingen.
- Rate limit per kartu (misalnya maksimal 30 kunjungan per jam per kartu) dan per IP untuk mencegah iseng.

## Peringkat Anjangsana

- Per tuan rumah: **rata-rata nilai review** = rata-rata dari (pengetahuan + keterampilan + sikap) / 3 untuk semua review yang berlaku (satu per kontingen tamu).
- Diurutkan dari rata-rata tertinggi. Jika sama, kontingen yang **paling banyak dikunjungi** di atas. Definisi "paling banyak dikunjungi": jumlah **kontingen tamu berbeda** yang tercatat berkunjung; jika masih sama, jumlah total kunjungan tercatat. (Catat pilihan ini di IMPROVISASI.)
- Ada tampilan **gabungan semua tingkat** (karena kunjungan antartingkat boleh) dan tampilan **per tingkat tuan rumah** (untuk juara per tingkat sesuai keputusan "juara per tingkat").
- Hasil Anjangsana tersedia sebagai sumber data untuk form mode 2 (misalnya `REF("anjangsana", "rata_rata")` dan `REF("anjangsana", "jumlah_kunjungan")`), supaya bisa masuk juara umum dan piagam juara. Cara termudah: buat form mode 2 sistem bernama `anjangsana` per tingkat yang kolomnya otomatis dari data Anjangsana.

## Halaman superadmin dan panitia

- Daftar kunjungan (waktu, pengunjung, tamu -> tuan rumah), daftar review, komentar.
- Tabel peringkat (gabungan dan per tingkat), unduh Excel.
- Superadmin bisa menghapus review yang jelas iseng (tercatat di log).
