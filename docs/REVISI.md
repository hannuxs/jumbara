# Revisi Permintaan

Catatan revisi dari Farhan setelah Tahap 1 selesai di laptop. Setiap revisi punya nomor, isi permintaan, dampak, rencana pengerjaan, dan status. Jika revisi mengubah keputusan, `docs/00-KEPUTUSAN.md` ikut diperbarui saat revisi dikerjakan.

## Daftar ringkas

| No | Tanggal | Revisi | Status |
|---|---|---|---|
| R1 | 18 Okt 2026 | Tingkat dipilih paling atas, daftar sekolah hanya menampilkan sekolah tingkat itu | Belum dikerjakan |
| R2 | 18 Okt 2026 | Perubahan manual Farhan: foto dicetak di kartu, bantuan nomor anggota (SIAMO), bantuan nama huruf kapital | Teks sudah diubah Farhan, dampak ke kode/dokumen belum ditindaklanjuti |
| R3 | 18 Okt 2026 | Semua nama disimpan dan ditampilkan dalam HURUF KAPITAL, termasuk gelar | Belum dikerjakan |

---

## R1. Tingkat dipilih dulu, sekolah disaring sesuai tingkat

**Permintaan:** di bagian "1. Kontingen", pilihan **Tingkat (Mula, Madya, Wira)** berada paling atas. Setelah tingkat dipilih, pilihan **Utusan sekolah** hanya menampilkan sekolah dengan tingkat tersebut. Sekolah dari tingkat lain tidak terlihat.

**Kondisi sekarang:** sekolah dipilih dulu (semua 29 sekolah, dikelompokkan per tingkat), tingkat terisi otomatis dari sekolah dan masih bisa diubah. Jika tingkat berbeda, kiriman diterima dengan tanda `TINGKAT_BEDA`.

**Dampak:**
- Urutan bagian 1 menjadi: Tingkat → Utusan sekolah → Peran.
- Dropdown sekolah dan kotak cari sekolah hanya berisi sekolah tingkat terpilih. Sebelum tingkat dipilih, dropdown sekolah nonaktif dengan teks "Pilih tingkat dulu".
- Mengganti tingkat setelah memilih sekolah akan mengosongkan pilihan sekolah bila sekolahnya tidak sesuai.
- Improvisasi lama "tingkat otomatis terisi dari sekolah" dan peringatan kuning "Tingkat ini berbeda dengan tingkat sekolah Anda" tidak dipakai lagi di form publik.
- Lewat form, tingkat dan tingkat sekolah selalu sama, sehingga tanda `TINGKAT_BEDA` praktis tidak muncul dari form publik.
- Tanpa JavaScript (fallback): dropdown tetap berisi semua sekolah per kelompok tingkat; server yang menjaga kecocokan (lihat keputusan di bawah).
- Form tambah/ubah superadmin tetap menampilkan semua sekolah (superadmin perlu memindahkan orang antar kontingen).
- "Isi untuk orang lain" tetap mengisi tingkat lalu sekolah.

**Perlu keputusan Farhan (bertentangan dengan `00-KEPUTUSAN.md` bagian Form biodata: "Tingkat yang dipilih berbeda dengan tingkat kontingen: superadmin melihat tanda"):**
- **Opsi A (saran):** server **menolak** kiriman bila tingkat tidak sama dengan tingkat sekolah, dengan pesan "Sekolah ini bukan tingkat Madya. Pilih lagi tingkat atau sekolah." Konsisten dengan tampilan baru. `00-KEPUTUSAN.md` diperbarui.
- **Opsi B:** server tetap menerima dan memberi tanda `TINGKAT_BEDA` (hanya bisa terjadi bila JavaScript mati atau kiriman dimanipulasi). Keputusan lama tidak berubah.

**Tes yang perlu disesuaikan/ditambah:** `test_tingkat_beda_diterima_dan_ditandai` (diubah sesuai opsi), tes urutan isian dan penyaringan sekolah di browser 360 px.

---

## R2. Perubahan manual oleh Farhan (diperiksa Claude, 18 Okt 2026)

Ditemukan lewat `git diff` (belum di-commit) di 4 file:

| No | File | Sebelum | Sesudah |
|---|---|---|---|
| R2.1 | `docs/00-KEPUTUSAN.md` (Form biodata) | "**Foto hanya arsip, tidak dicetak di kartu.**" | "**Foto hanya arsip, dicetak di kartu.**" |
| R2.2 | `docs/11-FORM-BIODATA.md` (Perilaku foto) | teks bantuan "...arsip panitia dan **tidak dicetak di kartu**." | "...arsip panitia dan **dicetak di kartu**." |
| R2.3 | `web/templates/biodata/form.html` (bagian Foto) | "...arsip panitia dan **tidak dicetak di kartu**." | "...arsip panitia dan **dicetak di kartu**." |
| R2.4 | `web/apps/biodata/forms.py` dan `form.html` (Nomor Induk Anggota) | "Ada di KTA PMR. Kosongkan jika belum punya." | "Terdapat pada aplikasi SIAMO" |
| R2.5 | `web/templates/biodata/form.html` (Nama lengkap) | "Tulis nama lengkap sesuai Kartu Keluarga, beserta gelar jika ada." | "Tulis nama lengkap dengan **huruf KAPITAL/Huruf Besar,** beserta gelar jika ada." |

### R2.1-R2.3 Foto dicetak di kartu

Keputusan baru: **foto peserta dicetak di kartu B-2.**

Hal yang masih bertentangan dan perlu dirapikan saat revisi ini dikerjakan:
- `docs/00-KEPUTUSAN.md` bagian **Kartu dan QR** masih menulis "Isi kartu: nama, kontingen, tingkat, peran, QR. **Tanpa foto.**" (baris 77).
- `docs/13-KARTU-QR.md` masih menulis "**Tanpa foto.**" (baris 29) dan belum mengatur letak foto di desain kartu.
- Kalimat "Foto hanya arsip, dicetak di kartu" saling bertentangan ("hanya arsip" vs dicetak). Usulan teks: "Foto dipakai di kartu peserta dan disimpan sebagai arsip panitia."
- Teks bantuan di form: usulan "Foto wajah terbaru, tampak depan, latar polos jika ada. Foto akan **dicetak di kartu peserta** dan disimpan sebagai arsip panitia."

Dampak teknis:
- **Tahap 2 (kartu):** desain B-2 perlu ruang foto 3x4 (usulan sekitar 24 x 32 mm di samping/atas nama), QR tetap minimal 45 x 45 mm. Foto 600x800 yang sudah disimpan cukup tajam untuk cetak ukuran itu (sekitar 635 dpi).
- **Foto wajib:** jika foto dicetak di kartu, sakelar `biodata.foto_wajib` sebaiknya tetap aktif. Untuk biodata tanpa foto (ditambah superadmin), kartu menampilkan kotak "FOTO" kosong untuk ditempel manual. Perlu konfirmasi.
- **Kualitas foto:** superadmin perlu daftar "tanpa foto" dan bisa mengganti foto (sudah ada di menu ubah). Usulan tambahan: tanda "foto perlu diganti" sebelum cetak kartu.
- **Perlindungan data:** foto anak akan terlihat di kartu yang dipakai di area kegiatan. Ini keputusan panitia; halaman web publik tetap tidak menampilkan foto. Tidak ada perubahan pada penyimpanan foto (tetap folder privat).
- **Perubahan foto setelah kartu dicetak** harus ikut menandai `perlu_cetak_ulang` (Tahap 2).
- `docs/IMPROVISASI.md` baris "Foto wajib, bisa dimatikan" dan alasan pemotong 3:4 tetap berlaku.

### R2.4 Nomor Induk Anggota dari aplikasi SIAMO

- Teks bantuan sudah diubah di `forms.py` dan `form.html`. Isian tetap **tidak wajib** dan label masih "Nomor Induk Anggota PMR (jika ada)".
- Kalimat "Kosongkan jika belum punya" ikut terhapus. Usulan: "Terdapat pada aplikasi SIAMO. Kosongkan jika belum punya." agar anak yang belum terdaftar tidak bingung.
- Perlu diperbarui juga: `docs/11-FORM-BIODATA.md` tabel Bagian 2 (masih "Ada di KTA PMR").
- Pertanyaan: apakah format nomor SIAMO tertentu (misalnya hanya angka, panjang tetap)? Jika ya, bisa ditambahkan validasi.

### R2.5 Nama ditulis huruf kapital

- Teks bantuan sudah diubah. Frasa "sesuai Kartu Keluarga" terhapus; usulan dikembalikan: "Tulis nama lengkap sesuai Kartu Keluarga, beserta gelar jika ada. Huruf besar/kecil tidak masalah, sistem otomatis menyimpannya dalam HURUF KAPITAL." (lihat R3, karena sistem yang mengubah ke kapital, pengisi tidak wajib mengetik kapital).

### Catatan

- Keempat file tersebut belum di-commit. Saat R2 dikerjakan, perubahan Farhan di-commit terpisah dengan pesan yang jelas.
- Tidak ada perubahan manual lain yang ditemukan (di luar 4 file di atas, folder kerja sama dengan commit terakhir `88f5c79`).

---

## R3. Semua nama dalam HURUF KAPITAL

**Permintaan:** nama tercatat sebagai HURUF KAPITAL di seluruh sistem (database, tampilan, Excel, PDF, kartu, piagam) walaupun pengisi menulis huruf kecil. Berlaku juga untuk gelar (contoh `Sri Handayani, S.Pd` → `SRI HANDAYANI, S.PD`).

**Kondisi sekarang:** nama disimpan sesuai ketikan (spasi dirapikan). Hanya bukti PDF yang menampilkan nama dalam huruf besar.

**Rencana:**
- Form (publik dan superadmin): `clean_nama_lengkap` mengubah ke kapital sebelum disimpan. Validasi huruf/titik/koma/apostrof/tanda hubung tetap.
- Isian nama di form diberi gaya huruf kapital saat diketik (`text-transform: uppercase`, `autocapitalize="characters"`) agar pengisi melihat hasilnya; ringkasan sebelum kirim dan bukti menampilkan kapital.
- Data yang sudah ada: migrasi data aman (`UPPER(nama_lengkap)`), dicatat di log. Sebelum 26 Oktober hanya ada data uji, jadi tidak ada risiko ke data asli.
- Excel, PDF bukti, halaman superadmin otomatis ikut karena membaca dari database. Tahap 2 (kartu) dan Tahap 5 (piagam) memakai nilai yang sama.
- Pencarian nama di superadmin tetap tidak membedakan huruf besar/kecil.
- Cek "nama mirip" tidak terpengaruh (sudah membandingkan tanpa huruf besar/kecil).
- Tes: nama huruf kecil tersimpan kapital; gelar ikut kapital; apostrof tetap (`AS'AD`).

**Perlu konfirmasi Farhan:**
- Apakah **nama ayah/ibu/wali** juga dibuat kapital? (Saran: **ya**, agar seragam.)
- **Tempat lahir** dan **alamat**: saran tetap sesuai ketikan (bukan nama orang). Atau ikut kapital?
- **Nama kontingen/sekolah** sudah dikelola superadmin; saran tidak diubah otomatis (kartu sudah menampilkan huruf besar sesuai desain).

---

## Urutan pengerjaan yang disarankan

1. Commit perubahan manual Farhan (R2) apa adanya.
2. R3 (nama kapital) dan R1 (tingkat dulu): kecil, menyentuh form publik, harus selesai dan diuji di HP sebelum 25 Oktober.
3. Rapikan dokumen yang bertentangan (R2.1-R2.5) dan perbarui `00-KEPUTUSAN.md`.
4. Desain kartu dengan foto (R2.1) dikerjakan di Tahap 2.
