# Prompt Tahap 2 sampai 5

Pakai satu per satu, setelah tahap sebelumnya selesai. Setiap prompt dimulai di sesi Claude Code baru (atau setelah `/clear`) supaya konteksnya bersih.

## Tahap 2: Kartu dan QR kontingen (siap 3 November)

```
Baca CLAUDE.md, docs/PROGRES.md, docs/00-KEPUTUSAN.md, docs/13-KARTU-QR.md, docs/03-DATA-MODEL.md, dan assets/brand/README.md. Kerjakan Tahap 2 sampai semua kriteria di docs/01-TAHAPAN.md terpenuhi: token QR acak dan kode kartu, kunci data biodata, PDF kartu B-2 4 per F4 dengan garis potong per kontingen (logo PMI dan logo Jumbara V di kepala kartu, warna tingkat Mula hijau, Madya biru, Wira kuning), cetak ulang satu orang, nonaktifkan kartu, dan lembar QR kontingen F4. Buat PDF contoh dari data uji dan periksa ukurannya benar (88 x 125 mm, kertas 215 x 330 mm) dengan mengukur koordinat di PDF. Improvisasi bila perlu dan catat di docs/IMPROVISASI.md. Perbarui docs/PROGRES.md di akhir.
```

## Tahap 3: Absensi bersamaan, rekap, poin, Anjangsana (siap 7 November)

```
Baca CLAUDE.md, docs/PROGRES.md, docs/00-KEPUTUSAN.md, docs/14-ABSENSI.md, docs/15-REKAP-POIN.md, docs/17-ANJANGSANA.md, docs/JADWAL-ACARA.md, docs/02-ARSITEKTUR.md (bagian kebersamaan), dan docs/22-PENGUJIAN.md. Catatan panitia yang wajib dipenuhi: "pemindai harus dapat berjalan secara bersamaan karena ada acara/kegiatan yang berjalan bersama". Kerjakan Tahap 3: halaman pemindai akun panitia (mode layar penuh, hijau/kuning/merah, cari manual, antrean offline IndexedDB, idempoten client_uuid), kelola titik absen, rekap per tingkat/kegiatan/sesi/kontingen/orang + Excel, kuota dan poin kehadiran per sesi yang dijumlah, pantauan langsung superadmin, dan Anjangsana publik dengan dua konfirmasi persis seperti di dokumen. Buat dan jalankan uji beban (30 perangkat x 15 titik bersamaan) di database uji, laporkan hasilnya, dan perbaiki sampai tidak ada catatan ganda atau galat. Improvisasi bila perlu dan catat. Perbarui docs/PROGRES.md.
```

## Tahap 4: Form builder dan juri (siap 7 November)

```
Baca CLAUDE.md, docs/PROGRES.md, docs/00-KEPUTUSAN.md, docs/16-FORM-BUILDER.md, docs/15-REKAP-POIN.md, dan data/template_penilaian.json. Kerjakan Tahap 4: form builder mode 1 dan mode 2, mesin rumus aman tanpa eval (tes unit lengkap: operator, koma desimal, fungsi SUM/AVG/MIN/MAX/ROUND/IF/PERINGKAT/POIN_PERINGKAT, REF antarform, referensi melingkar, bagi nol), kolom otomatis poin_kehadiran, agregasi antarjuri, tabel hasil yang bisa diurutkan dengan peringkat dan nilai seri, kunci/buka nilai, halaman juri dengan Nama Juri wajib, dan perintah untuk membuat template penilaian dari data/template_penilaian.json sebagai draf per tingkat. Buat juga form sistem Anjangsana agar hasilnya bisa ditarik dengan REF. Improvisasi bila perlu dan catat. Perbarui docs/PROGRES.md.
```

## Tahap 5: Piagam (siap 14 November)

```
Baca CLAUDE.md, docs/PROGRES.md, docs/00-KEPUTUSAN.md, docs/18-PIAGAM.md, dan assets/brand/README.md. Kerjakan Tahap 5: unggah template piagam, atur posisi teks dengan pratinjau, nomor piagam otomatis, piagam peserta untuk semua peran, piagam juara dari tabel hasil form mode 2 (per kegiatan per tingkat, per cabang Wahana, Got Talent, juara umum, Anjangsana), pengecualian peserta yang tidak berhak, unduh per orang/per kontingen/semua. Uji dengan template contoh A4 lanskap. Perbarui docs/PROGRES.md.
```

## Uji coba dan menjelang acara

```
Baca CLAUDE.md, docs/PROGRES.md, dan docs/22-PENGUJIAN.md. Siapkan uji coba bersama panitia 7-8 November: kontingen dan peserta uji yang bisa dihapus bersih, lembar panduan 1 halaman untuk pemindai, juri, dan pengunjung Anjangsana (siap cetak PDF), daftar periksa hari H, dan perintah sigap_hapus_data_uji. Periksa ulang cadangan otomatis dan cara memulihkannya. Laporkan hal yang berisiko gagal di hari H beserta cara mengatasinya.
```

## Setelah acara

```
Baca CLAUDE.md dan docs/19-LOG-KEAMANAN-PDP.md. Buat laporan akhir (rekap kehadiran per tingkat dan kontingen, hasil semua lomba, juara umum, statistik peserta) dalam Excel dan PDF dengan logo PMI dan Jumbara V. Jangan menjalankan sigap_anonimkan sebelum saya mengonfirmasi kesepakatan dengan panitia.
```
