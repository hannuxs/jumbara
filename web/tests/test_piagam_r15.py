"""Tes R15 piagam: juara per orang (dapat 2 piagam), PDF kontingen memuat piagam juara anggota, daftar nomor
sertifikat (Excel), tanda tangan Ketua PMI, dan template tegak menjadi bawaan."""

from __future__ import annotations

import io

import openpyxl
import pypdfium2 as pdfium
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory
from PIL import Image

from apps.absensi.models import Kegiatan
from apps.inti import pengaturan
from apps.kontingen.models import Kontingen
from apps.penilaian import services as nilai_svc
from apps.penilaian.hasil import subjek_dari_kunci
from apps.penilaian.models import AksesForm, Formulir, JenisKolom, JenisSubjek, Kolom, ModeForm, StatusForm
from apps.piagam import pdf as pdf_mod
from apps.piagam import services as svc
from apps.piagam.models import JenisPiagam, Orientasi, PiagamTerbit, TemplatePiagam

from .test_absensi import buat_peserta, buat_titik, kirim


def teks_halaman(isi: bytes) -> list[str]:
    doc = pdfium.PdfDocument(isi)
    return [doc[i].get_textpage().get_text_range() for i in range(len(doc))]


def _form_juara(juri, kg, kontingen):
    f = Formulir.objects.create(slug="traveling-wira", judul="Hasil Traveling - Wira", mode=ModeForm.PENILAIAN,
                                status=StatusForm.AKTIF, akses=AksesForm.JURI, jenis_subjek=JenisSubjek.KONTINGEN,
                                tingkat="WIRA", kolom_urut="peringkat", arah_urut="NAIK", kegiatan=kg)  # fmt: skip
    Kolom.objects.create(formulir=f, kode="peringkat", label="Peringkat", jenis=JenisKolom.ANGKA, urutan=1)
    rq = RequestFactory().post("/")
    rq.user = juri
    for k, n in zip(kontingen, (1, 2), strict=True):
        nilai_svc.kirim(rq, f, {"peringkat": n}, {}, "Panitia", subjek_dari_kunci(f, f"K{k.pk}"))
    return f


def test_juara_kontingen_per_orang_dan_pdf_kontingen(klien_superadmin, juri, panitia):
    pengaturan.simpan("piagam.syarat_daftar_ulang", False)
    kg = Kegiatan.objects.create(kode="traveling", nama="Traveling Kepalangmerahan", kelompok="JUMPA")
    k1 = Kontingen.objects.create(kode="WI-01", nama="SMA Uji Satu", tingkat="WIRA", kuota=10)
    k2 = Kontingen.objects.create(kode="WI-02", nama="SMA Uji Dua", tingkat="WIRA", kuota=10)
    pilih = buat_peserta(k1, "ANI PEMILIH")  # memilih Traveling di biodata
    pilih.kegiatan.add(kg)
    hadir = buat_peserta(k1, "BUDI HADIR")  # tidak memilih, tetapi tercatat hadir di titik Traveling
    kirim(panitia, buat_titik(kode="TR-W", tingkat="WIRA", kegiatan=kg), "SJP:" + hadir.qr_token)
    lain = buat_peserta(k1, "CITRA LAIN")  # tidak ikut Traveling: tidak mendapat piagam juara
    f = _form_juara(juri, kg, [k1, k2])
    r = klien_superadmin.post(f"/superadmin/piagam/juara/form/{f.pk}/", {"maks": "1", "kegiatan": "Traveling"})
    assert r["Content-Type"] == "application/pdf"
    juara = PiagamTerbit.objects.filter(jenis=JenisPiagam.JUARA, sumber=f"form:{f.pk}")
    assert {x.peserta for x in juara} == {pilih, hadir}
    teks = teks_halaman(r.content)
    assert len(teks) == 2 and all("JUARA I" in t and "Traveling Tingkat Wira" in t for t in teks)
    assert "ANI PEMILIH" in teks[0] + teks[1] and "CITRA" not in "".join(teks)
    # PDF kontingen: 3 piagam peserta + 2 piagam juara, juara tepat setelah piagam peserta orang itu.
    r = klien_superadmin.get(f"/superadmin/piagam/kontingen/{k1.pk}/unduh.pdf")
    teks = teks_halaman(r.content)
    assert len(teks) == 5
    urutan = [("JUARA" if "JUARA I" in t else "PESERTA", next(n for n in ("ANI", "BUDI", "CITRA") if n in t))
              for t in teks]  # fmt: skip
    for i, (jenis, nama) in enumerate(urutan):
        if jenis == "JUARA":
            assert urutan[i - 1] == ("PESERTA", nama)
    assert lain.piagam.filter(jenis=JenisPiagam.JUARA).count() == 0


def test_juara_atas_nama_kontingen_bila_dipilih(klien_superadmin, juri):
    kg = Kegiatan.objects.create(kode="traveling", nama="Traveling Kepalangmerahan", kelompok="JUMPA")
    k1 = Kontingen.objects.create(kode="WI-01", nama="SMA Uji Satu", tingkat="WIRA", kuota=10)
    k2 = Kontingen.objects.create(kode="WI-02", nama="SMA Uji Dua", tingkat="WIRA", kuota=10)
    buat_peserta(k1, "ANI").kegiatan.add(kg)
    f = _form_juara(juri, kg, [k1, k2])
    klien_superadmin.post(f"/superadmin/piagam/juara/form/{f.pk}/", {"maks": "1", "penerima": "KONTINGEN"})
    x = PiagamTerbit.objects.get(jenis=JenisPiagam.JUARA)
    assert x.peserta is None and x.kontingen == k1 and x.data["nama"] == "Kontingen SMA Uji Satu"


def test_daftar_nomor_sertifikat_excel(klien_superadmin, kontingen_madya):
    pengaturan.simpan("piagam.syarat_daftar_ulang", False)
    ani = buat_peserta(kontingen_madya, "AIRLANGGA PRADIPA HUSONO")
    svc.terbitkan_peserta(None, [ani], svc.template_aktif(JenisPiagam.PESERTA))
    r = klien_superadmin.get("/superadmin/piagam/unduh/nomor/")
    wb = openpyxl.load_workbook(io.BytesIO(r.content))
    ws = wb["Peserta"]
    assert [c.value for c in ws[3]] == ["NO.", "NAMA PESERTA", "UNIT PMR", "SEBAGAI", "NOMOR SERTIFIKAT"]
    assert [c.value for c in ws[4]] == [1, "AIRLANGGA PRADIPA HUSONO", "PMR MADYA UNIT SMP NEGERI UJI", "PESERTA",
                                        "001 / JMB-V / PMR / PMI.BULUNGAN / PST / XI / 2026"]  # fmt: skip
    assert "Juara" in wb.sheetnames


def _png(warna_latar=(255, 255, 255)) -> bytes:
    img = Image.new("RGB", (400, 150), warna_latar)
    for x in range(40, 360):
        img.putpixel((x, 75), (10, 10, 60))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_gambar_tanda_tangan_diunggah_transparan_dan_dicetak(klien_superadmin):
    r = klien_superadmin.post("/superadmin/piagam/ttd/", {"ttd": SimpleUploadedFile("ttd.png", _png())})
    assert r.status_code == 302
    path = pdf_mod.path_ttd()
    assert path is not None
    with Image.open(path) as img:
        assert img.mode == "RGBA" and img.getpixel((0, 0))[3] == 255  # dipangkas ke goresan (bukan latar putih)
    t = svc.template_aktif(JenisPiagam.PESERTA)
    assert pdf_mod.pratinjau_png(t, svc.data_contoh(t.jenis), 400)[:4] == b"\x89PNG"
    klien_superadmin.post("/superadmin/piagam/ttd/", {"hapus": "1"})
    assert pdf_mod.path_ttd() is None and not path.exists()
    r = klien_superadmin.post("/superadmin/piagam/ttd/", {"ttd": SimpleUploadedFile("x.png", b"bukan")}, follow=True)
    assert "PNG atau JPG" in r.content.decode()


def test_template_tegak_menjadi_bawaan_tanpa_menghapus_yang_lama(db):
    lama = TemplatePiagam.objects.create(nama="Piagam peserta (desain bawaan)", jenis=JenisPiagam.PESERTA,
                                         orientasi=Orientasi.MENDATAR, elemen=[])  # fmt: skip
    panitia = TemplatePiagam.objects.create(nama="Desain panitia", jenis=JenisPiagam.PESERTA, latar="a" * 32 + ".png",
                                            orientasi=Orientasi.MENDATAR, desain_bawaan=False, elemen=[])  # fmt: skip
    svc.pastikan_template_bawaan()
    svc.pastikan_template_bawaan()  # aman diulang
    lama.refresh_from_db()
    panitia.refresh_from_db()
    tegak = TemplatePiagam.objects.filter(orientasi=Orientasi.TEGAK)
    assert tegak.count() == 2 and not lama.aktif and panitia.aktif
    assert svc.template_aktif(JenisPiagam.PESERTA).orientasi == Orientasi.TEGAK
