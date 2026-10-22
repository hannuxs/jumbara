"""Tes Tahap 2: token QR, kartu PDF (QR benar-benar terbaca), terbitkan ulang, kunci data, QR kontingen."""

from __future__ import annotations

import io
import re
import zipfile

import pytest
from django.test import Client

from apps.biodata.models import Peserta
from apps.inti import pengaturan
from apps.inti.models import LogAktivitas
from apps.kartu import services, token
from apps.kartu.models import KartuRiwayat
from apps.kartu.pdf import kartu_pdf, qr_kontingen_pdf
from apps.kontingen.models import Kontingen

from .conftest import data_valid, masuk, token_lama


def isi_biodata(client, k, n: int = 1, **ubah) -> list[Peserta]:
    """Kirim n biodata lewat form publik (NIK dan nama berbeda)."""
    for i in range(n):
        nik = f"65010141011{20 + i:02d}{i:03d}"[:16].ljust(16, "7")
        nama = ["Ani Lestari", "Budi Santoso", "Citra Dewi", "Dodi Pratama", "Eka Putri", "Fajar Nugraha"][i % 6]
        r = client.post(
            "/daftar/", data_valid(k, nik=nik, nama_lengkap=f"{nama} {'ABCDEFGH'[i]}", token=token_lama(), **ubah)
        )
        assert r.status_code == 302, r.context["form"].errors if r.context else r
    return list(Peserta.objects.order_by("id"))


def jumlah_halaman(isi: bytes) -> int:
    return len(re.findall(rb"/Type /Page\b(?!s)", isi))


def baca_semua_qr(isi_pdf: bytes) -> list[str]:
    """Render PDF lalu pindai QR per seperempat halaman (seperti HP membaca satu kartu)."""
    pdfium = pytest.importorskip("pypdfium2")
    cv2 = pytest.importorskip("cv2")
    import numpy as np

    hasil = []
    det = cv2.QRCodeDetector()
    dok = pdfium.PdfDocument(io.BytesIO(isi_pdf))
    for i in range(len(dok)):
        img = cv2.cvtColor(np.array(dok[i].render(scale=2).to_pil()), cv2.COLOR_RGB2BGR)
        h, w = img.shape[:2]
        halaman = []
        for y0, x0 in ((0, 0), (0, w // 2), (h // 2, 0), (h // 2, w // 2)):
            teks, _, _ = det.detectAndDecode(img[y0 : y0 + h // 2, x0 : x0 + w // 2])
            if teks:
                halaman.append(teks)
        if not halaman:  # QR kontingen memenuhi halaman: pindai utuh
            teks, _, _ = det.detectAndDecode(img)
            if teks:
                halaman.append(teks)
        hasil.extend(halaman)
    dok.close()
    return hasil


# --- Token ---------------------------------------------------------------------


def test_format_token():
    t = token.token_acak()
    assert len(t) == 26 and re.fullmatch(r"[23456789ABCDEFGHJKMNPQRSTUVWXYZ]{26}", t)
    assert token.kode_dari_token(t) == f"{t[:4]}-{t[4:8]}"
    assert token.isi_qr_peserta(t) == "SJP:" + t
    assert len({token.token_acak() for _ in range(2000)}) == 2000


@pytest.mark.parametrize(
    "teks,jenis",
    [
        ("SJP:" + "A" * 26, "PESERTA"),
        ("sjp:" + "a" * 26, "PESERTA"),
        ("SJK:" + "B" * 26, "KONTINGEN"),
        ("k7q2-m4xa", "KODE"),
        ("K7Q2 M4XA", "KODE"),
        ("https://contoh.com", "ASING"),
        ("SJP:12345", "ASING"),
        ("K0Q2-M4XA", "ASING"),  # 0 tidak pernah dipakai di kode
    ],
)
def test_baca_qr(teks, jenis):
    assert token.baca_qr(teks)[0] == jenis


def test_biodata_baru_langsung_punya_token(client, kontingen_madya):
    p = isi_biodata(client, kontingen_madya)[0]
    assert len(p.qr_token) == 26
    assert p.kode_kartu == token.kode_dari_token(p.qr_token)
    assert p.versi_kartu == 1 and p.kartu_aktif and not p.perlu_cetak_ulang
    assert p.qr_token not in str(p.kode_pendaftaran)


def test_kontingen_baru_punya_qr_token(db):
    k = Kontingen.objects.create(kode="MA-99", nama="SMP Uji Token", tingkat="MADYA", kuota=5)
    assert len(k.qr_token) == 26 and k.qr_token_dibuat_pada


# --- Mengenali kartu (dipakai pemindai Tahap 3) ----------------------------------------


def test_kenali_kartu(client, kontingen_madya, superadmin):
    p = isi_biodata(client, kontingen_madya)[0]
    assert services.kenali("SJP:" + p.qr_token).kode == "BERHASIL"
    assert services.kenali(p.kode_kartu.lower().replace("-", " ")).peserta == p
    assert services.kenali("SJK:" + kontingen_madya.qr_token).kode == "BUKAN_KARTU_PESERTA"
    assert services.kenali("halo").kode == "QR_ASING"
    assert services.kenali("SJP:" + "Z" * 26).kode == "KARTU_TIDAK_DIKENAL"


# --- Terbitkan ulang, nonaktif ---------------------------------------------------------


def test_terbitkan_ulang_kartu(client, kontingen_madya, klien_superadmin):
    p = isi_biodata(client, kontingen_madya)[0]
    lama_token, lama_kode = p.qr_token, p.kode_kartu
    r = klien_superadmin.post(f"/superadmin/kartu/peserta/{p.pk}/terbitkan-ulang/", {"alasan": "HILANG"})
    assert r.status_code == 302
    p.refresh_from_db()
    assert p.qr_token != lama_token and p.versi_kartu == 2 and p.perlu_cetak_ulang and p.kartu_aktif
    rw = KartuRiwayat.objects.get(peserta=p)
    assert rw.qr_token_lama == lama_token and rw.kode_kartu_lama == lama_kode and rw.oleh == "Penguji"
    hasil = services.kenali("SJP:" + lama_token)
    assert hasil.kode == "KARTU_NONAKTIF" and "terbaru" in hasil.pesan
    assert services.kenali(lama_kode).kode == "KARTU_NONAKTIF"
    assert services.kenali("SJP:" + p.qr_token).kode == "BERHASIL"
    assert LogAktivitas.objects.filter(aksi="kartu.diterbitkan_ulang").exists()


def test_terbitkan_ulang_wajib_alasan(client, kontingen_madya, klien_superadmin):
    p = isi_biodata(client, kontingen_madya)[0]
    klien_superadmin.post(f"/superadmin/kartu/peserta/{p.pk}/terbitkan-ulang/", {"alasan": ""})
    p.refresh_from_db()
    assert p.versi_kartu == 1


def test_nonaktifkan_dan_aktifkan(client, kontingen_madya, klien_superadmin):
    p = isi_biodata(client, kontingen_madya)[0]
    klien_superadmin.post(f"/superadmin/kartu/peserta/{p.pk}/aktif/", {"aktif": "0"})
    assert services.kenali("SJP:" + p.qr_token).kode == "KARTU_NONAKTIF"
    klien_superadmin.post(f"/superadmin/kartu/peserta/{p.pk}/aktif/", {"aktif": "1"})
    assert services.kenali("SJP:" + p.qr_token).kode == "BERHASIL"


# --- Kunci data biodata --------------------------------------------------------------


def data_ubah(p: Peserta, **ubah) -> dict:
    from apps.biodata import nik as nik_mod

    data = {
        "kontingen": str(p.kontingen_id), "tingkat": p.tingkat, "peran": p.peran, "nama_lengkap": p.nama_lengkap,
        "nik": nik_mod.dekripsi(p.nik_terenkripsi), "nomor_induk_anggota": "", "jenis_kelamin": p.jenis_kelamin,
        "tempat_lahir": p.tempat_lahir, "tanggal_lahir_0": str(p.tanggal_lahir.day),
        "tanggal_lahir_1": str(p.tanggal_lahir.month), "tanggal_lahir_2": str(p.tanggal_lahir.year),
        "alamat": p.alamat, "golongan_darah": p.golongan_darah, "telepon": "", "nama_orang_tua": p.nama_orang_tua,
        "telepon_orang_tua": p.telepon_orang_tua,
    }  # fmt: skip
    data.update(ubah)
    return data


def test_kunci_data_menutup_form_dan_menandai_cetak_ulang(client, kontingen_madya, klien_superadmin):
    p = isi_biodata(client, kontingen_madya)[0]
    # Sebelum dikunci: ubah nama tidak menandai cetak ulang.
    klien_superadmin.post(f"/superadmin/biodata/{p.pk}/ubah/", data_ubah(p, nama_lengkap="Ani Lestari Baru"))
    p.refresh_from_db()
    assert not p.perlu_cetak_ulang
    klien_superadmin.post("/superadmin/kartu/kunci/", {"kunci": "1"})
    assert pengaturan.ambil("biodata.terkunci") is True
    assert LogAktivitas.objects.filter(aksi="biodata.dikunci").exists()
    # Form publik tertutup (server menolak).
    r = Client().post("/daftar/", data_valid(kontingen_madya, nik="6501019999990004", token=token_lama()))
    assert r.status_code == 403
    # Ubah alamat (tidak tercetak di kartu) -> tidak perlu cetak ulang.
    klien_superadmin.post(f"/superadmin/biodata/{p.pk}/ubah/", data_ubah(p, alamat="Jl. Baru RT 01, Tanjung Selor"))
    p.refresh_from_db()
    assert not p.perlu_cetak_ulang
    # Ubah nama -> perlu cetak ulang.
    klien_superadmin.post(f"/superadmin/biodata/{p.pk}/ubah/", data_ubah(p, nama_lengkap="Ani Lestari Sekali"))
    p.refresh_from_db()
    assert p.perlu_cetak_ulang
    log = LogAktivitas.objects.filter(aksi="biodata.diubah").first()
    assert "perlu dicetak ulang" in str(log.data_baru)
    # Tandai sudah dicetak.
    klien_superadmin.post("/superadmin/kartu/tercetak/", {"peserta": p.pk})
    p.refresh_from_db()
    assert not p.perlu_cetak_ulang
    # Buka kunci -> form publik kembali mengikuti jadwal (di tes: paksa buka).
    klien_superadmin.post("/superadmin/kartu/kunci/", {"kunci": "0"})
    r = Client().post("/daftar/", data_valid(kontingen_madya, nik="6501019999990004", token=token_lama()))
    assert r.status_code == 302


def test_tambah_manual_saat_terkunci_perlu_dicetak(klien_superadmin, kontingen_madya):
    pengaturan.simpan("biodata.terkunci", True)
    data = data_valid(kontingen_madya)
    for kunci in ("token", "persetujuan", "situs_web"):
        data.pop(kunci)
    klien_superadmin.post("/superadmin/biodata/tambah/", data)
    assert Peserta.objects.get().perlu_cetak_ulang


# --- PDF kartu ----------------------------------------------------------------------


def test_urutan_cetak(db):
    k = Kontingen(kode="X", nama="X", tingkat="MADYA")
    orang = [
        Peserta(nama_lengkap="ZAKI", peran="PESERTA", kontingen=k, pk=1),
        Peserta(nama_lengkap="BUDI", peran="PENINJAU", kontingen=k, pk=2),
        Peserta(nama_lengkap="ANI", peran="PESERTA", kontingen=k, pk=3),
        Peserta(nama_lengkap="SRI", peran="PEMBINA_PENDAMPING", kontingen=k, pk=4),
        Peserta(nama_lengkap="YANI", peran="PIMPINAN_KONTINGEN", kontingen=k, pk=5),
    ]
    assert [p.nama_lengkap for p in services.urutkan_untuk_cetak(orang)] == ["YANI", "SRI", "ANI", "ZAKI", "BUDI"]


def test_pdf_kartu_kontingen_qr_terbaca(client, kontingen_madya, klien_superadmin):
    daftar = isi_biodata(client, kontingen_madya, n=5)
    r = klien_superadmin.get(f"/superadmin/kartu/unduh/kontingen/{kontingen_madya.pk}/")
    assert r["Content-Type"] == "application/pdf"
    assert 'filename="Kartu_MA-01_SMP_Negeri_Uji.pdf"' in r["Content-Disposition"]
    isi = r.content
    assert jumlah_halaman(isi) == 1 + 2  # sampul + 2 lembar (4 + 1 kartu)
    terbaca = baca_semua_qr(isi)
    assert sorted(terbaca) == sorted("SJP:" + p.qr_token for p in daftar)
    assert LogAktivitas.objects.filter(aksi="kartu.diunduh").exists()


def test_pdf_hanya_cetak_ulang(client, kontingen_madya, klien_superadmin):
    daftar = isi_biodata(client, kontingen_madya, n=3)
    Peserta.objects.filter(pk=daftar[1].pk).update(perlu_cetak_ulang=True)
    r = klien_superadmin.get(f"/superadmin/kartu/unduh/kontingen/{kontingen_madya.pk}/?ulang=1")
    assert jumlah_halaman(r.content) == 2
    assert baca_semua_qr(r.content) == ["SJP:" + Peserta.objects.get(pk=daftar[1].pk).qr_token]


def test_pdf_satu_orang(client, kontingen_madya, klien_superadmin):
    p = isi_biodata(client, kontingen_madya)[0]
    r = klien_superadmin.get(f"/superadmin/kartu/unduh/peserta/{p.pk}/")
    assert jumlah_halaman(r.content) == 1
    assert baca_semua_qr(r.content) == ["SJP:" + p.qr_token]


def test_nama_terpanjang_tetap_dibuat(db, kontingen_madya):
    t = token.token_acak()
    p = Peserta(nama_lengkap="MUHAMMAD RIZKY ALFAREZA PRATAMA SAPUTRA WIJAYAKUSUMA, S.PD., M.PD.", peran="PIMPINAN_KONTINGEN",
                tingkat="MADYA", kontingen=kontingen_madya, qr_token=t, kode_kartu=token.kode_dari_token(t), pk=999)  # fmt: skip
    isi = kartu_pdf([p], "Uji nama panjang")
    assert baca_semua_qr(isi) == ["SJP:" + t]


def test_zip_semua_kontingen(client, kontingen_madya, kontingen_wira, klien_superadmin):
    isi_biodata(client, kontingen_madya, n=2)
    r = klien_superadmin.get("/superadmin/kartu/unduh/semua/")
    z = zipfile.ZipFile(io.BytesIO(r.content))
    assert z.namelist() == ["Kartu_MA-01_SMP_Negeri_Uji.pdf"]  # kontingen tanpa biodata dilewati


# --- QR kontingen ---------------------------------------------------------------------


def test_pdf_qr_kontingen(kontingen_madya, kontingen_wira, klien_superadmin):
    r = klien_superadmin.get(f"/superadmin/kartu/qr/{kontingen_madya.pk}/")
    assert jumlah_halaman(r.content) == 1
    assert baca_semua_qr(r.content) == ["SJK:" + kontingen_madya.qr_token]
    semua = klien_superadmin.get("/superadmin/kartu/qr/").content
    assert jumlah_halaman(semua) == Kontingen.objects.count()
    assert jumlah_halaman(qr_kontingen_pdf([])) == 1


def test_ganti_qr_kontingen(kontingen_madya, klien_superadmin):
    lama = kontingen_madya.qr_token
    klien_superadmin.post(f"/superadmin/kartu/qr/{kontingen_madya.pk}/ganti/")
    kontingen_madya.refresh_from_db()
    assert kontingen_madya.qr_token != lama
    assert services.kenali("SJK:" + lama).kontingen is None
    assert LogAktivitas.objects.filter(aksi="kontingen.qr_diganti").exists()


# --- Halaman dan hak akses -------------------------------------------------------------


RUTE = ["/superadmin/kartu/", "/superadmin/kartu/qr/", "/superadmin/kartu/unduh/semua/"]


@pytest.mark.parametrize("url", RUTE)
def test_halaman_kartu_hanya_superadmin(client, panitia, juri, superadmin, url):
    assert client.get(url).status_code == 302
    masuk(client, "panitia")
    assert client.get(url).status_code == 403
    c = Client()
    masuk(c, "juri")
    assert c.get(url).status_code == 403


def test_halaman_kartu_dan_detail_tampil(client, kontingen_madya, klien_superadmin):
    p = isi_biodata(client, kontingen_madya)[0]
    assert klien_superadmin.get("/superadmin/kartu/").status_code == 200
    isi = klien_superadmin.get(f"/superadmin/biodata/{p.pk}/").content.decode()
    assert p.kode_kartu in isi and "Nonaktifkan &amp; terbitkan baru" in isi
    assert "Ganti QR tenda" in klien_superadmin.get(f"/superadmin/kontingen/{kontingen_madya.pk}/").content.decode()


def test_publik_tidak_bisa_unduh_kartu(client, kontingen_madya):
    p = isi_biodata(client, kontingen_madya)[0]
    r = Client().get(f"/superadmin/kartu/unduh/peserta/{p.pk}/")
    assert r.status_code == 302 and r["Location"].startswith("/masuk/")
