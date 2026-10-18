# 14. Absensi dengan Kamera HP (Tahap 3)

## Prinsip

- **Panitia memindai kartu peserta.** Peserta tidak memindai apa pun untuk absensi.
- **Catatan panitia (wajib):** "Pemindai harus dapat berjalan secara bersamaan karena ada acara/kegiatan yang berjalan bersama."
  - Banyak titik absen aktif pada saat yang sama (Jumat 13 Nov 08.00: Traveling, Ranking 1, Jurnalistik, Kewirausahaan, Sarasehan, ditambah Anjangsana; per tingkat bisa lebih dari 15 titik).
  - **Banyak HP boleh memindai di satu titik yang sama** secara bersamaan (misalnya daftar ulang dengan 4 meja).
  - Setiap HP memilih titik absennya sendiri, tidak saling mengganggu, dan HP mengingat pilihannya.
  - Satu orang bisa tercatat di dua titik absen yang waktunya bertabrakan (misalnya kolom kegiatan menyebut "Traveling dan Gobak Sodor"). Ini **diizinkan**, tetapi pemindai melihat info kuning kecil "Orang ini juga tercatat di [titik lain] pukul 08.05" agar sadar.
- Lihat bagian "Kebersamaan" di `02-ARSITEKTUR.md` untuk aturan database (kunci unik, idempoten, transaksi pendek).

## Titik absen

- Satu titik absen = satu **kegiatan x tingkat x hari/sesi**. Data awal: `data/titik_absen.csv` (60 titik) dari Jadwal Kegiatan PDF terbaru. Lihat `JADWAL-ACARA.md`.
- Daftar ulang (12 Nov 08.00-12.00) adalah satu titik untuk semua tingkat. Got Talent satu titik gabungan per hari.
- Titik absen dengan tingkat tertentu hanya menerima peserta dari tingkat itu. Kartu tingkat lain -> **merah** "Tingkat tidak sesuai: kartu ini Madya, titik absen ini Wira." (Superadmin bisa mengizinkan pengecualian manual.)
- Status titik: **Otomatis** (aktif sejak 60 menit sebelum mulai sampai 60 menit setelah selesai; jika selesai kosong, sampai 23.59 hari itu), **Buka paksa**, **Tutup paksa**. Titik yang tertutup tidak bisa dipindai (pesan jelas), kecuali superadmin.
- Superadmin bisa menambah titik bebas (misalnya Parade Budaya naik bus, Senam Pagi) dengan kegiatan kosong dan opsi "tidak dihitung poin".
- Jadwal **tidak ditulis mati di kode**. Semua dari database.

## Halaman pemindai (akun panitia dan superadmin)

Alur:
1. Buka "Pindai". Jika belum ada nama pemindai di perangkat ini, minta nama dulu.
2. **Pilih titik absen.** Daftar dikelompokkan: "Sedang berlangsung" (paling atas, tombol besar), "Nanti hari ini", "Sudah lewat". Bisa dicari. Setiap kartu titik menunjukkan nama, tingkat (warna), jam, lokasi, jumlah sudah hadir / kuota total.
3. Titik terpilih diingat per perangkat. Setelah login ulang, langsung kembali ke titik ini.
4. **Mode pindai layar penuh:** kamera belakang menyala terus, kotak bidik di tengah, nama titik absen dan nama pemindai di atas, penghitung "Hadir 23 / 29 kontingen" di bawah.
5. Setiap QR terbaca:
   - **Hijau** (getar pendek + bunyi "bip" tinggi): "Berhasil" + NAMA BESAR, kontingen, tingkat, peran. Tampil 1,5 detik lalu siap pindai berikutnya.
   - **Kuning** (getar dua kali + bunyi sedang): "Sudah tercatat pukul 08.12 oleh Rina" + nama. Bukan galat.
   - **Merah** (getar panjang + bunyi rendah): alasan jelas: kartu tidak dikenal, kartu nonaktif, tingkat tidak sesuai, titik absen tertutup, QR kontingen, QR asing.
   - Kunci QR yang sama selama 3 detik agar satu kartu tidak terbaca berkali-kali saat kamera masih mengarah.
6. **Daftar pindaian terakhir** (10 terakhir) di bawah layar, dengan status masing-masing (hijau/kuning/merah/menunggu terkirim).
7. **Cari manual:** tombol "Cari nama" untuk kartu rusak/tertinggal: ketik nama atau `kode_kartu`, pilih orang (hanya peserta tingkat yang sesuai), konfirmasi. Tercatat dengan metode MANUAL.
8. Tombol ganti kamera, senter (jika didukung), suara on/off, dan "Selesai".

Teknis pemindai:
- Pakai `qr-scanner` (nimiq) dengan worker, resolusi sedang agar HP murah tetap lancar. Minta izin kamera dengan penjelasan ramah. Tangani galat izin ditolak dengan panduan membuka izin kamera di Chrome dan Safari.
- Wajib HTTPS (lihat `02-ARSITEKTUR.md`).
- Layar jangan mati saat mode pindai: pakai Screen Wake Lock API jika tersedia.

## Antrean offline (wajib)

- Setiap pindaian dibuat dulu di **IndexedDB** dengan `client_uuid`, `qr_token`, `titik_absen_id`, `dipindai_pada` (jam HP), `nama_pemindai`, `perangkat_id`, status `menunggu`.
- Lalu dikirim ke server. Jika berhasil, status berubah sesuai jawaban server (hijau/kuning/merah).
- Jika gagal karena koneksi, status tetap `menunggu`, tampil abu-abu "Tersimpan di HP, akan dikirim otomatis". Penghitung "3 pindaian menunggu terkirim" di header.
- Pengiriman ulang otomatis: setiap 10 detik, saat event `online`, saat halaman dibuka, dan setelah login ulang. Server idempoten berdasarkan `client_uuid`.
- Karena hasil validasi hanya pasti dari server, saat offline tampilkan nama dari **cache daftar peserta lokal** (diunduh saat memilih titik absen: id, token hash, nama, kontingen, tingkat; tanpa data pribadi lain) supaya pemindai tetap bisa memastikan kartu dipakai pemiliknya.
- Jangan pernah menghapus antrean yang belum terkirim tanpa konfirmasi. Peringatkan jika pengguna mencoba logout sementara antrean belum kosong.

## API pindai

`POST /api/pindai` (login panitia/superadmin, JSON, dengan token CSRF Django dikirim di header `X-CSRFToken`):

```json
{ "client_uuid": "...", "titik_absen_id": 12, "qr": "SJP:...", "dipindai_pada": "2026-11-13T08:05:12+08:00",
  "nama_pemindai": "Rina", "perangkat_id": "...", "metode": "SCAN", "offline": false }
```

Jawaban:

```json
{ "status": "HIJAU|KUNING|MERAH", "kode": "BERHASIL|SUDAH_TERCATAT|KARTU_TIDAK_DIKENAL|KARTU_NONAKTIF|TINGKAT_BEDA|TITIK_TUTUP|BUKAN_KARTU_PESERTA",
  "pesan": "...", "peserta": { "nama": "...", "kontingen": "...", "tingkat": "MADYA", "peran": "PESERTA" },
  "tercatat_pada": "08:05", "oleh": "Rina", "info_bentrok": "Juga tercatat di Ranking 1 Madya pukul 08.01" }
```

- Kiriman dengan `client_uuid` yang sama mengembalikan jawaban yang sama (idempoten).
- Batch: `POST /api/pindai/batch` untuk antrean offline (maksimal 50 per kiriman).
- Pindaian MERAH dicatat di `pindaian_ditolak` untuk audit.

## Pengelolaan oleh superadmin

- Kelola titik absen (tambah, ubah, buka/tutup paksa, salin titik untuk hari lain).
- Batalkan satu kehadiran (soft delete, tercatat di log) jika salah pindai.
- Tambah kehadiran manual dengan alasan.
- Layar **pantauan langsung**: semua titik yang sedang berlangsung, jumlah hadir, jumlah HP aktif (berdasarkan pindaian 5 menit terakhir), antrean dan pindaian merah terbaru. Diperbarui dengan polling.

## Uji yang wajib

- Dua HP memindai kartu yang sama di titik yang sama dalam waktu hampir bersamaan -> satu hijau, satu kuning, satu baris di database.
- Kiriman ulang `client_uuid` yang sama -> tidak dobel.
- Antrean offline: matikan jaringan, pindai 10 kartu, nyalakan -> semua terkirim, tidak dobel.
- Uji beban 30 perangkat x 15 titik (lihat `22-PENGUJIAN.md`).
- Kartu tingkat salah, kartu nonaktif, QR kontingen, QR acak -> merah dengan pesan benar.
