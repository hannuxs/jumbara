# 03. Model Data (rancangan awal)

Ini rancangan, bukan harga mati. Claude Code boleh menyesuaikan nama kolom dan menambah tabel, **asalkan** aturan kunci unik dan pemisahan data pribadi tetap terjaga. Catat setiap perubahan besar di `docs/IMPROVISASI.md`.

Ditulis dalam istilah tabel/kolom; implementasikan sebagai model Django. Semua model domain memakai `id` BigAutoField (`DEFAULT_AUTO_FIELD`), `dibuat_pada`, `diubah_pada`. Model yang bisa dihapus superadmin memakai **soft delete** (field `dihapus_pada` + manager bawaan yang menyaring data terhapus, manager `semua` untuk tempat sampah).

## Akun dan sistem

**users** (model User Django, `AUTH_USER_MODEL` kustom dibuat sejak migrasi pertama): `id`, `username` (superadmin / panitia / juri), `role` (enum SUPERADMIN, PANITIA, JURI), `password`, `password_changed_at`. Hanya tiga baris. Tidak ada pendaftaran akun.

**sessions**: sesi database bawaan Django (`django_session`) + tabel kecil `sesi_akun` (`user_id`, `session_key`, `login_pada`, `perangkat_id`) agar bisa menghapus semua sesi milik satu akun saat kata sandi diganti dan menampilkan perangkat aktif.

**pengaturan**: `kunci` (unik), `nilai` (JSON/teks). Contoh kunci: `biodata.buka_pada`, `biodata.tutup_pada`, `biodata.paksa_status` (otomatis/buka/tutup), `biodata.foto_wajib` (bawaan true), `biodata.terkunci` (untuk cetak kartu), `kontak.superadmin_wa`, `kontak.superadmin_nama`, `anjangsana.paksa_status`, `pengumuman.teks`.

**log_aktivitas**: `id`, `user_id` (nullable untuk publik), `peran`, `nama_pelaku` (nama pemindai/juri/superadmin), `aksi` (contoh: biodata.dibuat, biodata.diubah, biodata.dihapus, kehadiran.dipindai, nilai.dikirim, nilai.dibuka, kartu.dinonaktifkan, sandi.diganti, nik.dilihat, ekspor.lengkap), `subjek_tipe`, `subjek_id`, `data_lama` JSON, `data_baru` JSON, `ip`, `user_agent`, `perangkat_id`, `created_at`. **Jangan menyimpan NIK utuh atau foto di log**; samarkan.

## Kontingen dan peserta

**kontingen**: `id`, `kode` (MU-01, MA-01, WI-01 ...), `nama` (nama resmi untuk dropdown dan kartu), `tingkat` (MULA/MADYA/WIRA), `nama_di_gform`, `pimpinan_gform`, `pendamping_gform` (teks referensi, hanya superadmin), `kuota` (int, dari `kuota_awal`), `qr_token` (acak, unik, untuk QR tenda), `qr_token_dibuat_pada`, `catatan`, soft delete.

**peserta** (biodata, satu baris per orang):
- `id`, `kode_pendaftaran` (unik, mudah dibaca, contoh `SJ-7KQ2M4`), `kontingen_id`, `tingkat`, `peran`
- `nama_lengkap`, `nik` (char 16, **UNIQUE**), `nomor_induk_anggota` (nullable), `jenis_kelamin`, `tempat_lahir`, `tanggal_lahir`, `alamat`, `golongan_darah`, `telepon` (nullable sesuai aturan), `nama_orang_tua`, `telepon_orang_tua`
- `foto_path` (relatif ke disk privat), `foto_asli_hash` (sha256, untuk mendeteksi unggahan sama)
- `persetujuan_data_at` (waktu mencentang persetujuan)
- `qr_token` (acak, UNIQUE, nullable sampai Tahap 2), `kode_kartu` (8 karakter, UNIQUE, dicetak di bawah QR), `versi_kartu` (int), `kartu_aktif` (bool)
- `perlu_cetak_ulang` (bool), `tidak_berhak_piagam` (bool) + `alasan_tidak_berhak_piagam`
- `sumber` (FORM_PUBLIK / SUPERADMIN), `ip_pengirim`, `user_agent_pengirim`
- soft delete

Pertimbangkan **NIK disimpan terenkripsi** (enkripsi tingkat field, misalnya Fernet dari paket `cryptography` dengan kunci di `.env`) plus kolom `nik_hash` (HMAC-SHA256 dengan kunci aplikasi) yang UNIQUE untuk cek dobel. Jika dipakai, pencarian NIK memakai hash. Putuskan di Tahap 0 dan catat.

**penanda_peserta** (atau kolom JSON `penanda` di `peserta`): `peserta_id`, `jenis` (KUOTA_PENUH, TINGKAT_BEDA, NIK_TGL_LAHIR_BEDA, NIK_JK_BEDA, USIA_TIDAK_WAJAR, FOTO_DUPLIKAT, NAMA_MIRIP), `pesan`, `diabaikan_oleh`, `diabaikan_pada`. Superadmin bisa menandai "sudah dicek" agar tanda hilang dari daftar.

**kartu_riwayat**: `peserta_id`, `versi`, `qr_token_lama`, `alasan` (hilang/rusak/data berubah), `oleh`, `created_at`. Token lama yang dipindai menghasilkan merah "kartu sudah dinonaktifkan".

## Kegiatan dan absensi

**kegiatan**: `id`, `kode` (traveling, jurnalistik, ...), `nama`, `kelompok` (JUMPA/BAKTI/GEMBIRA/ADMINISTRASI), `dipisah_per_tingkat` (bool), `kuota_default` (nullable), `rincian_kuota` (teks), `catatan`, `urutan`.

**kuota_kegiatan**: `kegiatan_id`, `kontingen_id` (nullable = berlaku untuk semua kontingen), `kuota` (int). UNIQUE (`kegiatan_id`, `kontingen_id`). Nilai per kontingen menimpa nilai umum.

**titik_absen** (= satu sesi absensi): `id`, `kode` (TA-001 ...), `kegiatan_id` (nullable untuk titik bebas buatan superadmin), `tingkat` (MULA/MADYA/WIRA/SEMUA), `nama_tampil`, `tanggal`, `mulai`, `selesai` (nullable = "selesai"), `lokasi`, `status` (OTOMATIS/BUKA/TUTUP), `hitung_poin` (bool, bawaan true kecuali daftar ulang), `catatan`.

**kehadiran**: `id`, `titik_absen_id`, `peserta_id`, `dipindai_pada` (waktu di HP), `diterima_pada` (waktu server), `nama_pemindai`, `perangkat_id`, `metode` (SCAN/MANUAL), `client_uuid` (**UNIQUE**), `offline` (bool), soft delete (superadmin bisa membatalkan kehadiran).
- **UNIQUE (`titik_absen_id`, `peserta_id`)** untuk baris yang belum dihapus. Karena MariaDB tidak punya partial index, cara aman: saat soft delete, pindahkan baris ke tabel `kehadiran_dibatalkan` atau isi kolom `aktif` lalu UNIQUE (`titik_absen_id`, `peserta_id`, `aktif_key`) di mana `aktif_key` = 1 untuk aktif dan NULL untuk dibatalkan (NULL boleh dobel di UNIQUE). Pilih satu dan uji.

**pindaian_ditolak** (opsional tapi disarankan): catatan pindaian merah (token tidak dikenal, tingkat salah, kartu nonaktif) untuk audit dan statistik.

## Form builder

**form**: `id`, `slug` (unik, dipakai di rumus `REF`), `judul`, `mode` (INPUT/PENILAIAN), `kegiatan_id` (nullable), `tingkat` (nullable/SEMUA), `cabang` (nullable, contoh Bakiak), `subjek` (KONTINGEN/PESERTA/BEBAS), `jenis` (BIASA/GUGUR), `status` (DRAFT/AKTIF/TERKUNCI/ARSIP), `akses` (SUPERADMIN/JURI/PUBLIK), `agregasi_juri` (RATA_RATA/JUMLAH/TERAKHIR), `urut_kolom`, `urut_arah`, `pengaturan` JSON.

**form_kolom**: `form_id`, `kode` (unik dalam form, huruf kecil/angka/garis bawah), `label`, `tipe` (TEKS, PARAGRAF, ANGKA, PILIHAN, PILIHAN_GANDA, TANGGAL, JAM, FILE, YA_TIDAK, RUMUS, OTOMATIS), `wajib`, `min`, `max`, `desimal`, `opsi` JSON, `rumus` (teks, untuk RUMUS), `sumber_otomatis` (contoh `poin_kehadiran`, `jumlah_hadir`), `tampil_ke_juri` (bool), `urutan`.

**form_isian** (satu kiriman): `form_id`, `subjek_kontingen_id` / `subjek_peserta_id` (nullable), `nama_pengisi` (Nama Juri), `user_id`, `dikirim_pada`, `terkunci` (bool), `dibuka_oleh`, `dibuka_pada`, soft delete.

**form_nilai**: `form_isian_id`, `form_kolom_id`, `nilai_teks`, `nilai_angka` (DECIMAL 12,4), `nilai_file`. UNIQUE (`form_isian_id`, `form_kolom_id`).

Nilai kolom RUMUS **tidak disimpan permanen sebagai sumber kebenaran**; dihitung ulang dari data (boleh di-cache dengan invalidasi saat data sumber berubah).

## Anjangsana

**anjangsana_kunjungan**: `id`, `pengunjung_peserta_id`, `kontingen_tamu_id`, `kontingen_tuan_rumah_id`, `sesi` (tanggal + jam mulai), `dipindai_pada`, `ip`, `user_agent`. Setiap kunjungan yang terkonfirmasi tercatat (boleh banyak).

**anjangsana_review**: `kontingen_tamu_id`, `kontingen_tuan_rumah_id`, `pengunjung_peserta_id` (pengirim terakhir), `nilai_pengetahuan`, `nilai_keterampilan`, `nilai_sikap` (1-5), `komentar`, `dikirim_pada`, `riwayat` JSON (review lama yang diganti). **UNIQUE (`kontingen_tamu_id`, `kontingen_tuan_rumah_id`)**.

**anjangsana_sesi**: `tanggal`, `mulai`, `selesai`.

## Piagam

**piagam_template**: `id`, `nama`, `jenis` (PESERTA/JUARA), `file_latar` (gambar/PDF dari panitia), `ukuran_kertas` (A4/F4), `orientasi`, `tata_letak` JSON (posisi x, y, lebar, font, ukuran, warna, perataan untuk setiap isian: nama, kontingen, peran, tingkat, kegiatan, peringkat, nomor piagam, tanggal), `aktif`.

**piagam_terbit**: `id`, `nomor` (unik, format diatur superadmin), `peserta_id` / `kontingen_id`, `template_id`, `form_id` (untuk juara), `peringkat`, `data` JSON (teks yang tercetak), `file_path`, `diterbitkan_pada`.

## Indeks penting

- `peserta(kontingen_id, tingkat, peran)`, `peserta(nama_lengkap)` untuk pencarian, `peserta(qr_token)`, `peserta(kode_kartu)`.
- `kehadiran(titik_absen_id, peserta_id)` UNIQUE, `kehadiran(peserta_id)`, `kehadiran(client_uuid)` UNIQUE.
- `titik_absen(tanggal, status)`.
- `form_isian(form_id, subjek_kontingen_id)`, `form_isian(form_id, subjek_peserta_id)`.
