# 10. Akun, Login, Sesi, dan Ingatan Perangkat

## Tiga akun bersama

| Username | Peran | Halaman awal setelah login |
|---|---|---|
| `superadmin` | SUPERADMIN | Dasbor superadmin (atau menu terakhir) |
| `panitia` | PANITIA | Halaman pemindai (atau menu terakhir) |
| `juri` | JURI | Daftar form penilaian (atau menu terakhir) |

- Tidak ada pendaftaran akun dan tidak ada akun tambahan. Username boleh diubah superadmin, tapi jumlahnya tetap tiga.
- Kata sandi awal dibaca dari `web\.env` (`SIGAP_SANDI_AWAL_SUPERADMIN`, `..._PANITIA`, `..._JURI`) saat seeding. Jika kosong, seeder membuat sandi acak dan menampilkannya sekali di konsol.
- Superadmin bisa mengganti kata sandi ketiga akun dari menu **Akun**. Saat diganti:
  - semua baris `sessions` milik akun itu dihapus, sehingga semua perangkat langsung keluar;
  - dicatat di log.
- Halaman login: satu form username + kata sandi, tombol tampilkan sandi, batas percobaan (5 kali per menit per IP + username, misalnya dengan `django-ratelimit` atau `django-axes`), pesan galat yang tidak membocorkan apakah username ada.
- **Tidak ada fitur "ingat saya" yang memperpanjang sesi.**

## Sesi 2 jam mutlak

- Saat login berhasil, simpan `login_at` di sesi.
- Middleware `SesiMutlak` di semua rute yang butuh login: jika `now() - login_at >= 120 menit`, logout, hapus sesi, arahkan ke login dengan pesan "Sesi Anda sudah 2 jam. Silakan masuk lagi."
- `SESSION_COOKIE_AGE = 7200` dan `SESSION_SAVE_EVERY_REQUEST = False` di settings Django, tapi tetap pakai middleware `SesiMutlak` karena yang dihitung adalah waktu sejak login.
- Django otomatis membatalkan sesi lain saat kata sandi diganti (hash autentikasi sesi berubah). Tetap hapus juga baris sesi milik akun itu dari tabel `django_session` (simpan pemetaan `user_id` -> `session_key` saat login) agar bersih dan bisa diuji.
- Tampilkan **sisa waktu sesi** kecil di header (misalnya "Sesi berakhir 14.32"). 5 menit sebelum habis, munculkan peringatan agar pemindai/juri bersiap.
- **Penting untuk pemindai:** jika sesi habis saat memindai, pindaian yang belum terkirim **tidak boleh hilang**. Simpan di antrean IndexedDB (lihat `14-ABSENSI.md`) dan kirim otomatis setelah login lagi. Jangan menampilkan pindaian sebagai berhasil (hijau) kalau server belum menerima; tampilkan status "tersimpan di HP, menunggu terkirim".
- **Penting untuk juri:** isian form yang sedang diketik disimpan sebagai draf di `localStorage` agar tidak hilang saat sesi habis.

## Ingatan menu dan pilihan terakhir per perangkat

Keputusan: web mengingat menu terakhir dan pilihan terakhir **per perangkat browser** untuk ketiga akun.

Implementasi yang disarankan:
- Setiap perangkat punya `perangkat_id` (UUID acak di `localStorage`, dibuat sekali).
- Simpan di `localStorage` dengan kunci per akun, misalnya `sigap:{username}:ingatan` berisi:
  - `rute_terakhir` (path + query),
  - `titik_absen_terakhir` (pemindai),
  - `filter` per halaman tabel (kontingen, tingkat, peran, kata kunci, urutan, halaman),
  - `form_terakhir` dan `subjek_terakhir` (juri),
  - pilihan kamera depan/belakang dan suara on/off.
- Setelah login, halaman perantara kecil membaca `rute_terakhir` dari `localStorage` lalu mengarahkan ke sana jika rute itu boleh diakses peran tersebut. Jika tidak, ke halaman awal peran.
- Filter tabel dibaca saat halaman dimuat dan ditulis setiap kali berubah (Alpine `$persist` atau kode sederhana).
- Bungkus akses `localStorage` dengan `try/catch` (mode privat browser bisa melempar galat).
- Tombol **"Lupakan perangkat ini"** di menu profil untuk menghapus semua ingatan dan nama pemindai.

## Pencatat nama pada akun bersama

- **Akun panitia:** saat pertama kali membuka pemindai di suatu perangkat, muncul dialog "Nama Anda (pemindai)" yang wajib diisi. Disimpan di `localStorage` (`sigap:panitia:nama_pemindai`). Selalu tampil di header pemindai ("Pemindai: Rina") dengan tombol ganti. Setiap pindaian mengirim `nama_pemindai` dan `perangkat_id`.
- **Akun juri:** setiap form penilaian punya isian wajib **Nama Juri**. Bawaannya terisi dari isian terakhir di perangkat itu (boleh diubah). Nama ini tersimpan di setiap kiriman nilai.
- **Akun superadmin:** juga diminta nama sekali per perangkat (misalnya "Farhan" atau "Ketua Panitia") agar log jelas siapa yang mengubah data.
- Nama ini tidak menggantikan login; hanya label untuk log.

## Hak akses (ringkas)

| Fitur | Superadmin | Panitia | Juri | Publik |
|---|---|---|---|---|
| Form biodata publik | lihat | - | - | isi (saat dibuka) |
| Daftar dan detail biodata | penuh | - | - | - |
| NIK utuh, alamat, kontak ortu, foto | ya (tercatat di log saat dibuka) | tidak | tidak | tidak |
| Kelola kontingen, kuota, kegiatan, titik absen | ya | - | - | - |
| Cetak kartu dan QR kontingen | ya | - | - | - |
| Memindai | ya | ya | - | - |
| Melihat hasil pindai dan rekap kehadiran | ya | ya (tanpa data pribadi) | - | - |
| Membatalkan kehadiran | ya | - | - | - |
| Form builder | ya | - | - | - |
| Mengisi form penilaian | ya | - | ya (form yang ditugaskan) | - |
| Membuka kunci nilai | ya | - | - | - |
| Anjangsana (pindai dan review) | lihat hasil | lihat hasil | - | ya (saat sesi) |
| Piagam | ya | - | - | - |
| Log aktivitas, tempat sampah, cadangan | ya | - | - | - |

Data yang ditampilkan ke akun panitia hanya: nama, kontingen, tingkat, peran, status hadir, jam, nama pemindai.
