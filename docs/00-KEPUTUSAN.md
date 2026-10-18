# 00. Keputusan yang Sudah Final

Dokumen ini adalah daftar keputusan dari klien (panitia Jumbara) dan pengembang (Ahmad Farhan, HANS PROJECT). **Semua yang tertulis di sini mengikat.** Jangan diubah tanpa izin Farhan. Kalau ada konflik antara dokumen lain dan dokumen ini, dokumen ini yang benar.

Sumber: Brief Proyek versi 2.1 (14 Oktober 2026), hasil rapat panitia 12 Oktober 2026, Pedoman Jumbara V 2026, Jadwal Kegiatan (PDF terbaru), dan tanya jawab dengan Farhan sampai 18 Oktober 2026.

## Identitas proyek

| Hal | Nilai |
|---|---|
| Nama aplikasi | **SIGAP JUMBARA** (Sistem Informasi, Absensi, dan Penilaian Jumbara) |
| Acara | Jumbara PMR Tingkat Kabupaten Bulungan V Tahun 2026 |
| Tanggal acara | 12 sampai 15 November 2026 (pendirian tenda 11 November) |
| Lokasi | Kebun Raya Bundayati, Tanjung Selor, Kalimantan Utara |
| Zona waktu | **WITA, Asia/Makassar (UTC+8)**. Semua jam di aplikasi memakai zona ini |
| Jumlah orang | Sekitar 750 sampai 1.000 orang, 29 kontingen (3 Mula, 17 Madya, 9 Wira) |
| Pengembang | Ahmad Farhan, HANS PROJECT |
| Klien | Panitia Pelaksana Jumbara PMR Kab. Bulungan V 2026 (narahubung kontrak: Samir Muslimin) |
| Domain | Belum final. Dasarnya `sigapjumbara` dengan TLD (.com/.id/.org) ditentukan Farhan nanti. Selalu baca dari `web\.env` (`SIGAP_URL`, `DJANGO_ALLOWED_HOSTS`), jangan ditulis mati di kode |
| Server produksi | **Windows + XAMPP** milik Farhan (Apache sebagai reverse proxy, MariaDB 10.5+ sebagai database) |
| Bahasa dan framework | **Python** (keputusan Farhan 18 Okt 2026): Python 3.12 + Django 5.2 LTS, dijalankan Waitress sebagai Windows Service |

## Logo

- **Logo PMI wajib ada** (permintaan panitia, 18 Oktober 2026), berdampingan dengan logo Jumbara V, di header web, form biodata, login, kartu, QR kontingen, dan bukti pendaftaran.
- File dan aturan pemakaian: `assets/brand/README.md`. Logo PMI tidak boleh diubah bentuk/warnanya.
- Logo HANS PROJECT hanya di kaki halaman web.

## Bentuk aplikasi

1. Aplikasi **web biasa** yang dibuka lewat browser HP dan laptop. **Bukan APK dan bukan PWA yang dipasang.** Jangan menambahkan prompt "Install app" atau manifest yang mendorong pemasangan. (Service worker untuk antrean offline pemindai boleh, asalkan tidak ada ajakan memasang.)
2. Tampilan diutamakan untuk layar HP (mobile first). Laptop tetap harus nyaman, terutama halaman superadmin.
3. Bahasa antarmuka: **Bahasa Indonesia** yang sopan, formal ringan, dan mudah dipahami anak SD sampai guru.

## Akun (tiga akun bersama)

| Akun | Dipakai oleh | Bisa | Tidak bisa |
|---|---|---|---|
| Superadmin | Farhan dan ketua panitia | Semua menu | Tidak ada batasan |
| Panitia | Semua panitia pemindai, satu akun dipakai bersama | Memindai kartu, melihat data hasil pindai dan rekap | Mengubah atau menghapus data apa pun |
| Juri | Semua juri, satu akun dipakai bersama | Mengisi form penilaian yang ditugaskan | Mengubah nilai yang sudah dikirim (kecuali dibuka superadmin) |

- Sesi login berakhir **setiap 2 jam** (mutlak sejak login, bukan diperpanjang oleh aktivitas). Setelah itu harus login lagi.
- Web **mengingat menu terakhir dan pilihan terakhir** (misalnya titik absen yang sedang dipindai, filter tabel, form yang sedang diisi) **per perangkat browser**, untuk ketiga akun. Setelah login ulang, pengguna kembali ke posisi itu.
- **Pencatat nama:** di akun panitia, pemindai mengetik namanya sekali per perangkat dan nama itu ikut tercatat pada setiap pindaian. Di akun juri, setiap form penilaian punya isian wajib **Nama Juri**.
- **Ganti kata sandi** oleh superadmin langsung mengeluarkan semua perangkat yang memakai akun itu.

## Prioritas dan tenggat

| Tahap | Isi | Siap paling lambat |
|---|---|---|
| 1 | Form biodata publik, data kontingen, tiga akun, halaman superadmin untuk melihat, mencari, memperbaiki, dan mengunduh biodata | **25 Oktober 2026** (form dibuka **26 Oktober 2026**) |
| 2 | Kartu peserta B-2 dan QR kontingen siap cetak | 3 November 2026 |
| 3 | Absensi QR (banyak pemindai bersamaan), rekap per tingkat, poin kehadiran, Anjangsana | 7 November 2026 |
| 4 | Form builder mode 1 dan mode 2 (rumus, tarik data antarform, akun juri) | 7 November 2026 |
| 5 | Piagam juara dan piagam peserta | 14 November 2026 |

Uji coba bersama panitia 7 sampai 8 November. Pelatihan panitia dan juri 10 November.

## Form biodata

- Form tetap (bukan hasil form builder). Link publik, tanpa login. Setiap orang mengisi sendiri.
- Dibuka **26 Oktober 2026** dan ditutup **2 November 2026** (jam persisnya diatur superadmin; bawaan 26 Okt 00.00 WITA sampai 2 Nov 23.59 WITA).
- Isian: nama lengkap, NIK, nomor induk anggota, jenis kelamin, tempat lahir, tanggal lahir, alamat rumah, golongan darah, telepon, utusan sekolah, tingkat, peran, nama ayah atau ibu, telepon ayah atau ibu, upload foto. Rincian di `11-FORM-BIODATA.md`.
- **Utusan sekolah** dipilih dari dropdown daftar kontingen (`data/kontingen.csv`), bukan diketik bebas.
- **Nama peserta tetap diketik manual** oleh peserta. Data lain yang belum lengkap juga diisi di form.
- **JANGAN memakai daftar nama peserta dari spreadsheet panitia.** Satu-satunya data awal yang dipakai adalah daftar kontingen hasil Google Form pendaftaran (nama sekolah, tingkat, jumlah orang).
- Kuota kontingen penuh: **form tetap menerima**, superadmin melihat tanda.
- Tingkat yang dipilih berbeda dengan tingkat kontingen: superadmin melihat tanda.
- NIK yang sama tidak bisa dikirim dua kali. Kalau seseorang salah isi atau mengisi dua kali, ia menghubungi superadmin.
- Foto JPG atau PNG, maksimal 5 MB, otomatis dikecilkan dan dipotong rasio 3x4. **Foto hanya arsip, dicetak di kartu.**
- Superadmin bisa melihat, mencari, memperbaiki, dan mengunduh seluruh biodata dalam Excel.

## Kartu dan QR

- Kartu ukuran **B-2** (sekitar 8,8 x 12,5 cm, potret), **4 kartu per lembar F4** (215 x 330 mm) dengan garis potong.
- Isi kartu: nama, kontingen, tingkat, peran, QR. **Tanpa foto.**
- QR berisi **kode acak**, bukan NIK atau nama. Kartu hilang bisa dinonaktifkan dan dicetak ulang dengan kode baru.
- Kartu dicetak per kontingen dalam satu PDF.
- Setiap kontingen mendapat **satu lembar QR kontingen ukuran F4** untuk ditempel di tenda (dipakai Anjangsana).

## Absensi

- **Panitia yang memindai kartu peserta** dengan kamera HP. Peserta tidak memindai apa pun untuk absensi.
- Titik absen: daftar ulang (12 Nov), setiap kegiatan **per tingkat** (Mula, Madya, Wira) **per hari/sesi**, dan Jumbara Got Talent sebagai satu titik gabungan per hari.
- **Catatan panitia: "pemindai harus dapat berjalan secara bersamaan karena ada acara/kegiatan yang berjalan bersama."** Banyak titik absen aktif pada saat yang sama, dan banyak HP boleh memindai di titik yang sama. Rincian di `14-ABSENSI.md`.
- Kegiatan yang berlangsung lebih dari satu hari dibuat **satu titik absen per kegiatan x tingkat x hari/sesi** (keputusan Farhan, opsi 4a). Poin kehadiran dijumlah dari semua sesinya.
- Kamera tetap menyala untuk pindai berturut-turut. Hijau = berhasil, kuning = sudah tercatat, merah = kartu tidak dikenal/nonaktif atau tingkat tidak sesuai. Nama, kontingen, tingkat tampil di layar.
- Cari nama manual jika kartu rusak/tertinggal. Pindaian disimpan di HP saat koneksi putus dan dikirim otomatis saat kembali.

## Kegiatan yang diabsen dan dinilai

Jumpa: Traveling Kepalangmerahan, Jurnalistik Remaja, Ranking 1, Sarasehan Sehat Bermedia Sosial, Sarasehan Menjaga Diri dari Pergaulan Bebas, Ngobrol Bareng PMR.
Bakti: Bakti Masyarakat, Kewirausahaan dan Pameran.
Gembira: Pentas Seni Drama Kepalangmerahan, Jumbara Got Talent, Anjangsana, Wahana Kepalangmerahan (Olahraga Persahabatan).

- Setiap kegiatan punya absen, rekap, dan juara terpisah per tingkat.
- **Pengecualian:** Got Talent satu juara umum tanpa tingkat. Wahana Kepalangmerahan satu absen per tingkat, juara per cabang (Bakiak, Voli Tutup Terpal, Gobak Sodor) dan per tingkat.
- Tidak diabsen secara bawaan: senam pagi, bakti lingkungan, parade budaya, upacara. Superadmin tetap bisa menambah titik absen baru kapan saja.

## Poin kehadiran

- Setiap kegiatan punya kuota orang per kontingen (diatur superadmin; bawaan dari pedoman, lihat `data/kegiatan.csv`).
- Per sesi: setiap orang hadir **+1**, setiap kekurangan dari kuota **-1**. Contoh: kuota 8, hadir 7 -> 7 - 1 = 6.
- Poin ini menjadi kolom otomatis `[poin_kehadiran]` di form penilaian kegiatan tersebut.

## Form builder

- **Mode 1 (input biasa):** membuat form umum, melihat hasil, rekap, unduh. Jenis isian: teks, angka, pilihan, tanggal, unggah file, dan lain-lain.
- **Mode 2 (penilaian):** semua kemampuan mode 1 ditambah: subjek per kontingen (bawaan) atau per orang; kolom rumus bebas (+ - x / kurung, SUM, AVG, MIN, MAX, dll.); rumus bisa menarik data dari form penilaian lain; lomba gugur cukup isi peringkat akhir; tabel bisa diurutkan dan peringkat otomatis; superadmin bisa mengunci nilai; juri tidak bisa mengubah nilai terkirim kecuali dibuka superadmin; piagam juara langsung dari tabel hasil.
- **Juara umum per tingkat** dihitung lewat satu form mode 2 khusus yang menarik data dari form lain.

## Anjangsana

- 13 dan 14 November. Satu **link publik** untuk semua peserta. Link **hanya aktif selama sesi**: 08.00-11.30, 13.30-17.30, 20.00-22.00 WITA.
- Alur: pengunjung buka link -> pindai kartunya sendiri -> konfirmasi 1 -> pindai QR kontingen tuan rumah -> konfirmasi 2 -> kunjungan tercatat -> form review (nilai 1-5 untuk pengetahuan, keterampilan, sikap + komentar).
- Teks konfirmasi persis seperti di `17-ANJANGSANA.md`.
- Satu review per kontingen tamu per tuan rumah (review baru mengganti yang lama setelah peringatan). Antartingkat boleh. Tidak bisa memindai QR kontingen sendiri.
- Peringkat: rata-rata nilai review, lalu jumlah kunjungan sebagai pemecah seri.

## Piagam

- Semua orang mendapat piagam PDF (peserta, pimpinan kontingen, pembina pendamping, peninjau).
- Piagam juara dari form mode 2: juara setiap kegiatan per tingkat, juara per cabang Wahana, juara Got Talent, juara umum per tingkat.
- Template dari panitia. Nama, kontingen, kegiatan, peringkat diisi otomatis. Unduh per orang atau per kontingen.

## Keamanan dan data pribadi

- Semua pindaian, nilai, perubahan, dan penghapusan tercatat dengan nama dan waktu.
- Data yang dihapus masuk tempat sampah dan bisa dikembalikan superadmin.
- Cadangan data otomatis setiap hari.
- Mengikuti prinsip UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi: NIK disamarkan, biodata lengkap dan foto hanya untuk superadmin, halaman publik tidak pernah menampilkan data pribadi orang lain.
