# Data Awal

| File | Isi | Dipakai untuk |
|---|---|---|
| `kontingen.csv` | 29 kontingen dari Google Form pendaftaran panitia, sudah dirapikan, dengan kode, tingkat, dan kuota awal | Dropdown "Utusan sekolah", kuota, kartu, QR kontingen. Lihat `docs/12-KONTINGEN.md` |
| `kegiatan.csv` | 13 kegiatan (termasuk daftar ulang) dengan kuota bawaan dari pedoman | Kegiatan, kuota, poin kehadiran |
| `titik_absen.csv` | 60 titik absen (kegiatan x tingkat x hari/sesi) dari Jadwal Kegiatan PDF | Seeder titik absen. Lihat `docs/JADWAL-ACARA.md` |
| `sesi_anjangsana.csv` | 6 sesi Anjangsana (13 dan 14 Nov, 3 sesi per hari) | Kapan link Anjangsana aktif |
| `template_penilaian.json` | Contoh form penilaian mode 2 dari aspek penilaian pedoman | Draf form penilaian. Lihat `docs/16-FORM-BUILDER.md` |

Semua file UTF-8 dengan baris judul. Seeder harus **idempoten** (dijalankan ulang tidak membuat data ganda; cocokkan berdasarkan `kode`).

**Tidak ada data peserta per orang di sini, dan memang tidak boleh ada.** Keputusan Farhan: nama dan biodata setiap orang diisi sendiri lewat form. Jangan meminta atau mengimpor daftar nama peserta dari panitia.

Kolom `pimpinan_gform` dan `pendamping_gform` di `kontingen.csv` hanya referensi superadmin (nama guru yang ditulis sekolah di GForm). Jangan ditampilkan di halaman publik dan jangan dipakai untuk mengisi biodata.
