# 16. Form Builder Mode 1 dan Mode 2 (Tahap 4)

Hasil rapat: "Penilaian dibuat fleksibel seperti Google Form untuk sementara." Form builder dikelola **hanya oleh superadmin**. Juri hanya mengisi.

## Mode 1: Input biasa

Untuk form umum (misalnya data tambahan, pendaftaran parade budaya, catatan pelanggaran, kebersihan kaveling).

- Buat form: judul, deskripsi, akses (superadmin saja / juri / publik dengan link), jadwal buka/tutup, satu kiriman per subjek atau bebas.
- Subjek (opsional): kontingen (pilih dari daftar), peserta (cari nama), atau bebas.
- Jenis isian: teks pendek, paragraf, angka (min, max, desimal), pilihan tunggal (radio/dropdown), pilihan ganda (checkbox), tanggal, jam, ya/tidak, unggah file (tipe dan ukuran dibatasi, disimpan privat), skala 1-5, judul bagian/teks keterangan.
- Setiap isian: label, teks bantuan, wajib/tidak, urutan (seret untuk mengurutkan).
- Salin form, arsipkan form, pratinjau sebagai pengisi.
- Hasil: tabel semua kiriman (cari, saring, urut), detail kiriman, ubah/hapus kiriman (superadmin), **rekap** (jumlah, rata-rata untuk angka, hitungan pilihan dengan grafik batang sederhana), **unduh Excel**.

## Mode 2: Penilaian

Semua kemampuan mode 1, ditambah:

### Pengaturan form penilaian
- Terhubung ke **kegiatan** (opsional) dan **tingkat** (Mula/Madya/Wira/Semua) dan **cabang** (opsional, contoh Bakiak).
- **Subjek penilaian: per kontingen (bawaan) atau per orang.** Untuk per kontingen, daftar subjek otomatis = kontingen tingkat itu (atau semua untuk Got Talent). Superadmin bisa memilih subjek tertentu saja (misalnya hanya 8 finalis Got Talent).
- **Jenis: biasa atau gugur.** Jenis gugur (Ranking 1, cabang Wahana) cukup satu kolom **peringkat akhir** yang diisi juri; peringkat diurutkan naik.
- **Banyak juri:** satu subjek boleh dinilai lebih dari satu juri (misalnya 3 juri Got Talent). Setiap kiriman menyimpan Nama Juri. Nilai kolom input untuk subjek = **agregasi antarjuri** sesuai pengaturan form: rata-rata (bawaan), jumlah, atau ambil kiriman terakhir. Tampilkan juga rincian per juri.
- Ditugaskan ke akun juri (form muncul di daftar juri) atau hanya diisi superadmin.

### Kolom
- **Kolom input**: angka (min/max), pilihan, teks catatan juri.
- **Kolom otomatis** (dihitung sistem, tidak diisi juri): `poin_kehadiran`, `jumlah_hadir`, `kuota` untuk kegiatan form itu (lihat `15-REKAP-POIN.md`), `jumlah_juri`.
- **Kolom rumus**: ekspresi yang bebas disusun superadmin. Contoh:
  - `[nilai_c] = [nilai_a] + [nilai_b]`
  - `[nilai_akhir] = 0.25*[pengetahuan] + 0.25*[sikap] + 0.5*[keterampilan] + [poin_kehadiran]`
- **Kolom peringkat** otomatis berdasarkan kolom yang dipilih (naik/turun).

### Bahasa rumus (wajib aman, tanpa `eval`)

- Angka: `12`, `0.25`, `0,25` (koma desimal juga diterima).
- Referensi kolom di form yang sama: `[kode_kolom]`.
- Operator: `+ - * /`, kurung `( )`, juga `x` atau `×` sebagai kali (karena pengguna awam). Perbandingan `= <> < <= > >=` untuk `IF`.
- Fungsi:
  - `SUM(a, b, ...)`, `AVG(a, b, ...)`, `MIN(...)`, `MAX(...)`, `ROUND(x, desimal)`, `ABS(x)`, `IF(kondisi, jika_ya, jika_tidak)`, `COALESCE(x, cadangan)` / nilai kosong dianggap 0 kecuali pakai `ISBLANK(x)`.
  - `REF("slug-form", "kode_kolom")`: **menarik nilai dari form penilaian lain** untuk subjek yang sama (kontingen yang sama). Jika form sumber per tingkat, cari form yang `kegiatan`-nya sama dengan tingkat subjek.
  - `REF("slug-form", "kode_kolom", "TINGKAT_INI")` atau varian eksplisit `REF("penilaian-traveling-wira", "peringkat")`. Tentukan sintaks final dan dokumentasikan di halaman bantuan form builder.
  - `PERINGKAT([kolom])`: peringkat subjek pada kolom itu dalam form ini.
  - `POIN_PERINGKAT(peringkat, p1, p2, p3, ...)`: mengubah peringkat menjadi poin, contoh `POIN_PERINGKAT(REF("ranking-1-madya","peringkat"), 10, 8, 6, 4, 2)` -> juara 1 dapat 10, juara 2 dapat 8, dan seterusnya; di luar daftar = 0.
- Tangani: pembagian dengan nol (hasil kosong + peringatan), referensi melingkar (tolak saat menyimpan dengan pesan jelas), kolom/form tidak ada (galat saat menyimpan), nilai kosong.
- Editor rumus: kotak teks dengan daftar kolom yang bisa diklik untuk menyisipkan, daftar fungsi, validasi langsung, dan pratinjau hasil untuk satu subjek contoh.
- Hasil rumus ditampilkan dengan pembulatan sesuai pengaturan kolom (bawaan 2 desimal), tapi dihitung dengan presisi penuh.
- **Tes unit lengkap** untuk tokenizer, prioritas operator, fungsi, REF, rekursi, galat.

### Tabel hasil
- Satu baris per subjek: kontingen, kolom input (agregat), kolom otomatis, kolom rumus, peringkat.
- **Bisa diurutkan** pada kolom mana pun. Peringkat otomatis mengikuti kolom urut yang ditetapkan form.
- **Nilai seri:** peringkat sama (1, 2, 2, 4) dan beri tanda seri; superadmin bisa memasukkan pemecah seri manual (kolom `pemecah_seri`).
- Penanda subjek yang belum dinilai / jumlah juri belum lengkap.
- Unduh Excel (dengan rumus sebagai nilai).
- **Kunci form**: setelah dikunci, juri tidak bisa mengirim/mengubah. Superadmin bisa membuka kunci seluruh form atau satu kiriman.
- **Buat piagam juara** langsung dari tabel: pilih peringkat 1-3 (atau sesuai pengaturan), pilih template piagam, terbitkan (lihat `18-PIAGAM.md`).

### Juara umum per tingkat
- Dibuat sebagai form mode 2 khusus per tingkat dengan subjek semua kontingen tingkat itu, tanpa kolom input juri, berisi kolom rumus `REF` + `POIN_PERINGKAT` ke form-form kegiatan. Rumusnya disusun panitia bersama superadmin.
- Poin tambahan non-lomba (kontingen favorit dari sarasehan, kebersihan kaveling dari pedoman) bisa dibuat sebagai form mode 2 biasa lalu ditarik dengan `REF`.

## Halaman juri

- Login akun `juri` -> daftar form yang ditugaskan dan sedang aktif, dikelompokkan per kegiatan dan tingkat.
- Pilih form -> **isi Nama Juri (wajib)** -> pilih subjek (kontingen) dari daftar dengan status sudah/belum dinilai oleh juri ini -> isi nilai -> **Kirim**.
- Sebelum kirim: ringkasan dan peringatan "Nilai yang sudah dikirim tidak bisa diubah."
- Setelah kirim: terkunci untuk juri. Jika salah, juri menghubungi superadmin yang bisa membuka kunci kiriman itu (tercatat di log).
- Draf isian disimpan di `localStorage` selama mengetik.
- Juri tidak melihat nilai juri lain dan tidak melihat tabel peringkat (kecuali superadmin mengizinkan per form).
- Tampilan besar dan sederhana untuk HP; tombol angka mudah ditekan; validasi min/max.

## Keputusan sintaks (dibuat 23 Okt 2026, juga tampil di "Bantuan rumus" editor)

- `REF("kunci", "kode")`: `kunci` boleh **slug** form (misal `penilaian-traveling-wira`, selalu form itu) atau **kunci REF bersama** (misal `penilaian-traveling`), lalu dipilih form dengan tingkat yang sama dengan subjek; bila tidak ada, form tingkat Semua. `REF("kunci", "kode", "TINGKAT_INI")` memaksa tingkat sama (kosong bila tidak ada).
- `kode` = kode kolom form sumber, kolom otomatis, atau `"peringkat"` (peringkat akhir form sumber, kecuali form itu punya kolom bernama `peringkat`).
- `REF("anjangsana", ...)`: `rata_rata`, `jumlah_review`, `tamu_berbeda`, `jumlah_kunjungan`, `peringkat` (per tingkat subjek), `peringkat_gabungan`.
- `PERINGKAT([kolom])` terbesar = 1; `PERINGKAT([kolom], "NAIK")` terkecil = 1.
- Koma desimal `0,25` hanya di luar fungsi. Di dalam fungsi `1,2` ditolak (membingungkan); tulis `1.2` atau `1, 2`. Titik koma juga pemisah argumen.
- Kosong: dihitung 0 pada + - * / dan SUM; diabaikan AVG/MIN/MAX. Subjek yang belum dinilai juri tidak diberi peringkat akhir (kecuali form tanpa isian, misal juara umum).
- Template: kunci REF = `penilaian-<kegiatan>`, `<kegiatan>` untuk form gugur, `<kegiatan>-<cabang>` per cabang, `juara-umum`; slug = kunci + `-mula`/`-madya`/`-wira`.

## Template awal

`data/template_penilaian.json` berisi contoh form dari pedoman (Traveling, Jurnalistik, Kewirausahaan, Drama, Got Talent, Ranking 1, Wahana per cabang, Bakti Masyarakat, Ngobrol Bareng, Sarasehan, Juara Umum). Buat seeder/perintah `python manage.py sigap_buat_template_penilaian` yang membuatnya sebagai **DRAF** per tingkat. Aspek dan bobot final dari panitia menyusul (paling lambat 5 November); superadmin akan menyesuaikan di form builder. Bobot Got Talent di pedoman tidak lengkap, jadi template menandainya "perlu konfirmasi".

Rencana lanjutan (setelah acara, bukan sekarang): aspek penilaian dibuat statis/tetap oleh pengembang. Jadi rancang form builder agar data penilaian tetap bisa diekspor rapi.
