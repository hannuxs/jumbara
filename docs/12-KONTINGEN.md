# 12. Data Kontingen dan Kuota

## Sumber data

`data/kontingen.csv` dirapikan dari spreadsheet hasil Google Form pendaftaran panitia ("Formulir Pendaftaran JUMBARA PMR PMI Kabupaten Bulungan Ke V Tahun 2026 (Jawaban)"). Ini **satu-satunya** data awal dari panitia yang dipakai.

**Jangan memakai spreadsheet "Data Peserta Jumbara"** (daftar nama per orang) dalam bentuk apa pun. Keputusan Farhan: nama dan data pribadi diisi sendiri oleh setiap orang lewat form biodata.

Ringkasan isi:
- 29 kontingen: 3 Mula (SD), 17 Madya (SMP/MTs), 9 Wira (SMA/SMK).
- Peserta inti menurut GForm: 616. Peninjau: 69.
- Kuota awal total: 750 orang.

## Kolom CSV

| Kolom | Arti |
|---|---|
| `kode` | Kode kontingen buatan kita: MU-01..03, MA-01..17, WI-01..09 (urut abjad dalam tingkat). Dipakai di kartu, QR kontingen, dan Excel |
| `nama_resmi` | Nama sekolah yang sudah dirapikan. Dipakai di dropdown form, kartu, piagam |
| `tingkat` | MULA / MADYA / WIRA (diturunkan dari jenjang sekolah) |
| `nama_di_gform` | Ejaan asli di GForm (referensi) |
| `pimpinan_gform`, `pendamping_gform` | Nama yang ditulis sekolah di GForm. **Hanya referensi untuk superadmin**, tidak dipakai mengisi biodata dan tidak tampil di halaman publik |
| `jumlah_pendamping_tambahan` | Jumlah pembina pendamping selain pimpinan. 0 jika pimpinan merangkap pendamping atau kolom kosong |
| `peserta_inti_gform` | Jumlah peserta inti di GForm |
| `peninjau_gform_asli` | Isi asli kolom peninjau ("-", kosong, atau angka) |
| `peninjau_dihitung` | Angka peninjau yang dipakai ("-" dan kosong dianggap 0) |
| `kuota_awal` | `peserta_inti_gform + peninjau_dihitung + 1 (pimpinan) + jumlah_pendamping_tambahan` |
| `catatan` | Catatan perapian data |

Hal yang perlu diketahui superadmin (tampilkan di halaman kontingen sebagai catatan):
- **SD Negeri 006 Tanjung Palas Utara** mendaftarkan 25 peserta inti, padahal batas pedoman untuk Mula adalah 20. Perlu konfirmasi panitia.
- Beberapa sekolah menulis pimpinan dan pendamping orang yang sama (merangkap).
- SMA Negeri 1 Tanjung Palas Tengah tidak mengisi pendamping.
- Angka kuota adalah perkiraan. Kuota bisa diubah superadmin kapan saja, dan form tidak pernah menolak karena kuota.

## Fitur superadmin untuk kontingen

- Daftar kontingen: kode, nama, tingkat, kuota, sudah isi biodata (total dan per peran), sudah daftar ulang (Tahap 3), jumlah hadir per kegiatan (Tahap 3), tanda.
- Tambah/ubah/hapus kontingen (jika ada sekolah susulan atau salah nama). Mengubah nama kontingen tidak mengubah data biodata yang sudah terhubung (relasi pakai `kontingen_id`).
- Ubah kuota. Riwayat perubahan kuota di log.
- **Pindahkan peserta** ke kontingen lain (jika salah pilih sekolah).
- Impor ulang dari CSV (opsional): hanya menambah kontingen baru dan memperbarui kuota yang belum diubah manual; tidak pernah menghapus.
- Ringkasan per kontingen yang bisa dicetak/diunduh (berguna untuk evaluasi malam bersama pimpinan kontingen pukul 23.00).
