# 15. Rekap Kehadiran dan Poin Kehadiran (Tahap 3)

## Rekap

Tersedia untuk superadmin dan panitia (panitia tanpa data pribadi). Semua tabel bisa difilter, diurutkan, dan **diunduh Excel**. Diperbarui otomatis (polling 10 detik) saat sedang dibuka.

1. **Per tingkat (Mula, Madya, Wira):** ringkasan setiap kegiatan dan sesi pada tingkat itu: jumlah hadir, jumlah kontingen hadir, persentase terhadap kuota.
2. **Per titik absen/sesi:** daftar orang hadir (nama, kontingen, peran, jam, pemindai, metode) dan daftar kontingen yang belum hadir atau kurang dari kuota.
3. **Per kegiatan:** gabungan semua sesi kegiatan itu, dipecah per tingkat.
4. **Per kontingen:** untuk satu kontingen, tabel kegiatan x sesi berisi jumlah hadir / kuota, plus daftar ulang (sudah/belum, siapa saja yang belum). Cocok untuk evaluasi malam pukul 23.00 bersama pimpinan kontingen. Sediakan versi cetak 1 halaman.
5. **Per orang:** riwayat kehadiran satu orang.
6. **Rekap harian:** ringkasan satu tanggal untuk semua kontingen (bahan evaluasi malam).
7. **Daftar ulang:** siapa saja yang sudah/belum daftar ulang per kontingen, dengan jumlah kartu yang belum diambil.

Excel: satu file per jenis rekap, nama file jelas dengan tanggal dan jam unduh, judul di baris pertama, kolom dengan lebar wajar.

## Kuota per kegiatan

- Tabel `kuota_kegiatan`. Bawaan dari `data/kegiatan.csv` (`kuota_default_per_kontingen`): Traveling 8 (1 pembina + 7 anggota), Jurnalistik 3, Ranking 1: 1, Sarasehan Sehat Bermedia Sosial 3, Sarasehan Menjaga Diri 3, Ngobrol Bareng 3, Bakti Masyarakat 2, Kewirausahaan 3, Wahana 5 (Bakiak 1, Voli Tutup Terpal 2, Gobak Sodor 2). Drama dan Got Talent kosong (diisi superadmin). Panitia akan mengirim kuota final paling lambat 31 Oktober.
- Superadmin bisa mengubah kuota umum per kegiatan dan menimpa kuota untuk kontingen tertentu (misalnya kontingen kecil).
- Kontingen hanya dihitung pada titik absen yang tingkatnya sama dengan tingkat kontingen (atau titik SEMUA).

## Poin kehadiran

Aturan keputusan: **setiap orang hadir +1, setiap orang yang tidak hadir dari kuotanya -1**, dihitung per kontingen per kegiatan.

Per titik absen (sesi) `s` untuk kontingen `k` dengan kuota `q`:

```
hadir_s   = jumlah orang kontingen k yang tercatat di titik s
dihitung  = min(hadir_s, q)          // orang di atas kuota tidak menambah poin (lihat catatan)
absen_s   = max(q - hadir_s, 0)
poin_s    = dihitung - absen_s
```

Poin kehadiran kegiatan = **jumlah `poin_s` dari semua sesi kegiatan itu** pada tingkat kontingen tersebut (keputusan 4a). Contoh: Traveling kuota 8, Jumat hadir 7 (poin 6), Sabtu hadir 8 (poin 8) -> poin kehadiran Traveling = 14.

Catatan:
- Contoh di brief: kuota 8, hadir 7, tidak hadir 1 -> 7 - 1 = 6. Rumus di atas menghasilkan angka yang sama.
- Pembatasan `min(hadir, q)` adalah improvisasi agar kontingen tidak menambah poin dengan membawa orang lebih banyak dari kuota. Buat sebagai pengaturan (`poin.batasi_ke_kuota`, bawaan **ya**) dan tampilkan tanda "lebih dari kuota" di rekap.
- Titik absen dengan `hitung_poin = false` (misalnya daftar ulang) tidak dihitung.
- Jika kuota kosong (null), poin kehadiran = jumlah hadir (tanpa pengurangan) dan tampilkan peringatan "kuota belum diatur".
- Tampilkan tabel poin kehadiran per kegiatan per tingkat: kontingen, rincian per sesi (hadir/kuota/poin), total.
- Poin ini tersedia di form penilaian mode 2 sebagai kolom otomatis `[poin_kehadiran]` (lihat `16-FORM-BUILDER.md`), juga `[jumlah_hadir]` dan `[kuota]`.
