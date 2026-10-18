# 22. Rencana Pengujian

## Tes otomatis (wajib, dijalankan sebelum setiap commit besar)

- **Biodata:** semua aturan di `11-FORM-BIODATA.md` bagian "Tes yang wajib ada".
- **Akun dan sesi:** sesi habis tepat 2 jam meski aktif; ganti sandi mengeluarkan sesi lain; hak akses setiap rute per peran (tabel di `10-AKUN-SESI.md`).
- **Absensi:** kunci unik, idempoten `client_uuid`, tingkat salah, kartu nonaktif, titik tertutup, QR kontingen di pemindai.
- **Poin kehadiran:** contoh brief (kuota 8, hadir 7 -> 6), multi-sesi dijumlah, batas ke kuota, kuota kosong.
- **Rumus:** tokenizer, prioritas operator, koma desimal, fungsi, `REF`, `POIN_PERINGKAT`, referensi melingkar, bagi nol, nilai kosong.
- **Penilaian:** agregasi antarjuri, peringkat seri, kunci dan buka kunci.
- **Anjangsana:** sesi aktif/tidak, kunjungan kontingen sendiri ditolak, satu review per pasangan dengan penggantian dan riwayat, urutan peringkat.

## Uji beban pemindai bersamaan

Buat perintah `python manage.py sigap_uji_beban` (memakai `httpx` + `asyncio` atau thread pool, skrip di `web/scripts/`) yang:
1. Menyiapkan data uji di database terpisah (`sigap_jumbara_uji`): 29 kontingen, sekitar 750 peserta palsu, 15 titik absen aktif.
2. Menyimulasikan 30 "perangkat" mengirim pindaian bersamaan ke `/api/pindai` selama 3 menit, termasuk 10% pindaian dobel dan 5% kiriman ulang `client_uuid` yang sama.
3. Melaporkan: jumlah permintaan, rata-rata dan p95 waktu respons, jumlah galat, dan memeriksa bahwa tidak ada baris kehadiran ganda.

Jalankan di PC server Windows sungguhan (bukan hanya laptop), karena Apache + Waitress di Windows berperilaku berbeda.

## Uji manual di HP

- Android murah (RAM 2-3 GB) dengan Chrome, Android baru, iPhone dengan Safari.
- Form biodata lengkap termasuk foto dari kamera dan dari galeri, foto potret/lanskap, foto besar 5 MB.
- Pemindai: cahaya terang/redup, kartu tercetak, kartu di layar, pindai beruntun cepat, mode pesawat lalu online lagi, sesi habis di tengah memindai.
- Anjangsana dari HP peserta.

## Uji coba bersama panitia (7-8 November)

Siapkan skenario dan data uji (kontingen uji "SEKOLAH UJI COBA" yang bisa dihapus bersih), lembar panduan singkat untuk pemindai dan juri (1 halaman, bisa dicetak), dan daftar periksa. Setelah uji coba, hapus semua data uji dengan satu perintah (`python manage.py sigap_hapus_data_uji`).
