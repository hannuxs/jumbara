# 20. Tampilan dan Gaya

## Kesan

Hangat, modern, rapi, dan ramah anak. Tema **oranye-kuning** seperti brief HANS PROJECT. Mudah dibaca di bawah sinar matahari (perkemahan) dan di HP murah.

## Warna (Tailwind theme)

| Token | Hex | Pemakaian |
|---|---|---|
| `oranye` (primer) | `#F26B1D` | Tombol utama, header, aksen |
| `oranye-tua` | `#E2451F` | Hover, judul penting |
| `oranye-judul` | `#E8590C` | Judul bagian |
| `amber` | `#FFB21A` | Sorotan, badge |
| `navy` | `#1F2937` | Teks utama |
| `teks` | `#374151` | Teks isi |
| `abu` | `#6B7280` | Teks bantuan |
| `krem` | `#FFF3E4` | Latar kartu/kotak info |
| `zebra` | `#FFF9F2` | Baris tabel selang-seling |
| `garis` | `#F5D2B3` | Garis tepi |

Warna tingkat (dari makna logo Jumbara V): **Mula hijau** (`#16A34A`), **Madya biru** (`#2563EB`), **Wira kuning** (`#EAB308`, teks gelap di atasnya). Dipakai konsisten untuk badge tingkat, kartu, dan titik absen.

Warna status pemindai: hijau `#16A34A`, kuning `#F59E0B`, merah `#DC2626`, abu `#9CA3AF` (menunggu terkirim). Layar status pemindai memenuhi layar dengan warna ini agar terlihat dari jauh.

Kontras teks minimal WCAG AA. Jangan menaruh teks putih di atas amber.

## Huruf

- **Poppins** untuk judul dan angka besar, **Inter** untuk isi. Di-host lokal (file WOFF2 di `web/static/fonts/`, unduh sekali dari Google Fonts/Fontsource lalu commit), hanya bobot yang dipakai (400, 500, 600, 700) dan subset latin.
- Ukuran dasar 16 px di HP (agar input tidak memicu zoom di iPhone).

## Tata letak

- Mobile first. Lebar konten maksimal sekitar 640 px untuk halaman publik dan pemindai; halaman superadmin boleh lebar penuh dengan sidebar di laptop dan menu bawah/hamburger di HP.
- Tombol besar (tinggi minimal 44 px), jarak antar elemen lega.
- Tabel lebar di HP: gulir horizontal di dalam kartu, atau ubah menjadi daftar kartu.
- Status kosong, status memuat, dan pesan galat yang jelas di setiap halaman.

## Identitas

- Nama aplikasi **SIGAP JUMBARA** di header, dengan subjudul "Jumbara PMR Tingkat Kabupaten Bulungan V 2026".
- **Logo PMI wajib ada** (permintaan panitia 18 Oktober 2026): `assets/brand/pmi-logo.svg` / `.png`. Tampil berdampingan dengan logo Jumbara V (PMI di kiri) di header semua halaman, beranda, form biodata, login, kartu, QR kontingen, dan bukti pendaftaran. Aturan pemakaian (tidak boleh diubah, latar terang, ruang kosong) ada di `assets/brand/README.md`. Karena header bertema oranye, letakkan kedua logo di dalam wadah/pita putih.
- **Logo Jumbara V sudah ada:** `assets/brand/jumbara-v-logo.jpg` (sudah dipangkas, 1205 x 1512 px) dan `assets/brand/jumbara-v-logo-asli.jpg` (file asli dari panitia, 1408 x 1600 px). Latarnya putih (JPG, bukan transparan), jadi tampilkan di atas latar putih atau di dalam lingkaran/kotak putih. Jangan menghapus latarnya secara otomatis karena logo punya banyak unsur putih (bulu, ukiran). Buat versi web yang lebih kecil (misalnya lebar 400 px dan 160 px, WebP + JPG) dan favicon dari kepala enggang. Superadmin tetap bisa mengganti logo dari menu pengaturan jika panitia mengirim versi PNG transparan.
- Warna di logo cocok dengan tema: kuning (Jumbara, paruh enggang), merah (PMR, syal), hijau-biru-kuning (bulu tingkat Mula, Madya, Wira). Ambil aksen merah `#D7262E` dari syal untuk elemen PMI/PMR bila perlu, tetapi warna utama aplikasi tetap oranye.
- Kaki halaman: "Dikembangkan oleh HANS PROJECT" dengan logo kecil dari `assets/brand/hans-project-logo.png` (salin ke `web/public/images/`, buat versi kecil 64 px dan favicon).
- Tema Jumbara V: "Unggul - Responsif - Berkarakter".

## Teks

- Bahasa Indonesia yang sopan dan pendek. Contoh: "Isi Biodata", "Kirim", "Perbaiki", "Pindai", "Cari nama", "Sudah tercatat", "Kartu tidak dikenal".
- Hindari istilah teknis (token, server, sinkronisasi). Gunakan "kode", "terkirim", "tersimpan di HP".
- Format tanggal: "Senin, 26 Oktober 2026", jam "08.00 WITA".
- Angka ribuan dengan titik: 1.000.

## Gaya visual

Gunakan skill `frontend-design` jika tersedia untuk arah visual. Hindari tampilan generik bawaan; buat header dengan gradasi oranye ke amber yang lembut, kartu putih dengan sudut membulat dan bayangan halus, ikon sederhana (misalnya Heroicons/Lucide yang dibundel lokal).
