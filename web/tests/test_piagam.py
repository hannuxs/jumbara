"""Tes piagam (docs/18-PIAGAM.md): template, syarat berhak, nomor tetap, unduhan, juara."""

from __future__ import annotations

import io
import json
import zipfile

import pypdfium2 as pdfium
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory
from PIL import Image

from apps.absensi.models import Kegiatan
from apps.anjangsana.models import Kunjungan, Review
from apps.inti import pengaturan
from apps.inti.models import LogAktivitas
from apps.kontingen.models import Kontingen
from apps.penilaian import services as nilai_svc
from apps.penilaian.hasil import subjek_dari_kunci
from apps.penilaian.models import AksesForm, Formulir, JenisKolom, JenisSubjek, Kolom, ModeForm, StatusForm
from apps.piagam import services as svc
from apps.piagam.models import JenisPiagam, PiagamTerbit, TemplatePiagam
from apps.piagam.pdf import isi_teks

from .conftest import masuk
from .test_absensi import buat_peserta, buat_titik, kirim


def halaman(isi: bytes) -> int:
    return len(pdfium.PdfDocument(isi))


def teks_pdf(isi: bytes) -> str:
    doc = pdfium.PdfDocument(isi)
    return "\n".join(doc[i].get_textpage().get_text_range() for i in range(len(doc)))


@pytest.fixture
def template(db):
    svc.pastikan_template_bawaan()
    return TemplatePiagam.objects.get(jenis=JenisPiagam.PESERTA)


@pytest.fixture
def daftar_ulang(db):
    kg = Kegiatan.objects.create(kode="daftar-ulang", nama="Daftar Ulang", kelompok="ADMINISTRASI")
    return buat_titik("TA-001", tingkat="SEMUA", kegiatan=kg, status="BUKA", hitung_poin=False)


def test_placeholder_tanpa_format_atau_eval():
    data = {"nama": "ANI", "kontingen": "SMP 1"}
    assert isi_teks("{nama} dari {kontingen}", data) == "ANI dari SMP 1"
    assert isi_teks("{nama.__class__} {tidak_ada} {0}", data) == "{nama.__class__} {tidak_ada} {0}"


def test_syarat_dan_nomor_tetap(template, kontingen_madya, daftar_ulang, panitia, klien_superadmin):
    a, b, c = (buat_peserta(kontingen_madya, n) for n in ("ANI", "BUDI", "CITRA"))
    kirim(panitia, daftar_ulang, "SJP:" + a.qr_token)
    kirim(panitia, daftar_ulang, "SJP:" + c.qr_token)
    svc.atur_berhak(None, c, False, "Sanksi pedoman BAB VI D")
    hasil, lewat = svc.terbitkan_peserta(None, [a, b, c], template)
    assert [x.peserta for x in hasil] == [a]
    alasan = {p.nama_lengkap: al for p, al in lewat}
    assert alasan["BUDI"] == "Belum daftar ulang" and alasan["CITRA"].startswith("Tidak berhak")
    assert hasil[0].nomor == "001/PST/JUMBARA-V/PMI-BLG/XI/2026"
    # Syarat daftar ulang dimatikan: BUDI ikut, nomor ANI tetap.
    pengaturan.simpan("piagam.syarat_daftar_ulang", False)
    hasil2, _ = svc.terbitkan_peserta(None, [a, b, c], template)
    assert {x.peserta.nama_lengkap: x.nomor for x in hasil2} == {
        "ANI": "001/PST/JUMBARA-V/PMI-BLG/XI/2026", "BUDI": "002/PST/JUMBARA-V/PMI-BLG/XI/2026",
    }  # fmt: skip
    # Nama diperbaiki: data piagam diperbarui, nomor tetap.
    a.nama_lengkap = "ANI LESTARI"
    a.save()
    x = svc.terbitkan_peserta(None, [a], template)[0][0]
    assert x.nomor.startswith("001/") and x.data["nama"] == "ANI LESTARI"
    assert PiagamTerbit.objects.count() == 2
    assert LogAktivitas.objects.filter(aksi="piagam.berhak_diubah").exists()


def test_unduh_kontingen_peserta_semua(template, kontingen_madya, kontingen_wira, klien_superadmin):
    pengaturan.simpan("piagam.syarat_daftar_ulang", False)
    for n in ("ANI", "BUDI"):
        buat_peserta(kontingen_madya, n)
    w = buat_peserta(kontingen_wira, "WAWAN", peran="PEMBINA_PENDAMPING")
    c = klien_superadmin
    assert c.get("/superadmin/piagam/").status_code == 200
    r = c.get(f"/superadmin/piagam/kontingen/{kontingen_madya.pk}/unduh.pdf")
    assert r["Content-Type"] == "application/pdf" and halaman(r.content) == 2
    isi = teks_pdf(r.content)
    assert "ANI" in isi and "Peserta" in isi and "SMP Negeri Uji" in isi and "PIAGAM PENGHARGAAN" in isi
    r = c.get(f"/superadmin/piagam/peserta/{w.pk}/unduh.pdf")
    assert "Pembina Pendamping" in teks_pdf(r.content)
    r = c.get("/superadmin/piagam/semua.zip")
    z = zipfile.ZipFile(io.BytesIO(r.content))
    assert sorted(n.split("_")[1] for n in z.namelist()) == ["MA-01", "WI-01"]
    assert c.get(f"/superadmin/piagam/kontingen/{kontingen_madya.pk}/").status_code == 200
    assert c.get("/superadmin/piagam/pengecualian/").status_code == 200
    # Tandai tidak berhak lewat halaman: wajib alasan.
    p = kontingen_madya.peserta.first()
    c.post(f"/superadmin/piagam/kontingen/{kontingen_madya.pk}/", {"peserta": p.pk, "berhak": "0", "alasan": ""})
    p.refresh_from_db()
    assert not p.tidak_berhak_piagam
    c.post(f"/superadmin/piagam/kontingen/{kontingen_madya.pk}/", {"peserta": p.pk, "berhak": "0", "alasan": "Sanksi"})
    p.refresh_from_db()
    assert p.tidak_berhak_piagam
    assert p.nama_lengkap in c.get("/superadmin/piagam/pengecualian/").content.decode()


def test_piagam_juara_dari_tabel_hasil(klien_superadmin, juri):
    svc.pastikan_template_bawaan()
    ks = [Kontingen.objects.create(kode=f"WI-0{i}", nama=f"SMA Uji {i}", tingkat="WIRA", kuota=10) for i in range(1, 5)]
    f = Formulir.objects.create(slug="ranking-1-wira", judul="Hasil Ranking 1 - Wira", mode=ModeForm.PENILAIAN,
                                status=StatusForm.AKTIF, akses=AksesForm.JURI, jenis_subjek=JenisSubjek.KONTINGEN,
                                tingkat="WIRA", kolom_urut="peringkat", arah_urut="NAIK")  # fmt: skip
    Kolom.objects.create(formulir=f, kode="peringkat", label="Peringkat", jenis=JenisKolom.ANGKA, urutan=1)
    rq = RequestFactory().post("/")
    rq.user = juri
    for k, p in zip(ks, (2, 1, 3, 4), strict=True):
        nilai_svc.kirim(rq, f, {"peringkat": p}, {}, "Panitia", subjek_dari_kunci(f, f"K{k.pk}"))
    r = klien_superadmin.post(f"/superadmin/piagam/juara/form/{f.pk}/", {"maks": "3", "kegiatan": "Ranking 1"})
    assert r["Content-Type"] == "application/pdf" and halaman(r.content) == 3
    isi = teks_pdf(r.content)
    assert "Kontingen SMA Uji 2" in isi and "Juara 1" in isi and "Ranking 1 Tingkat Wira" in isi
    x = PiagamTerbit.objects.get(sumber=f"form:{f.pk}", peringkat=1)
    assert x.kontingen == ks[1] and x.nomor == "001/JR/JUMBARA-V/PMI-BLG/XI/2026"
    # Unduh ulang: nomor sama, tidak ada piagam baru.
    klien_superadmin.post(f"/superadmin/piagam/juara/form/{f.pk}/", {"maks": "3", "kegiatan": "Ranking 1"})
    assert PiagamTerbit.objects.filter(jenis=JenisPiagam.JUARA).count() == 3
    assert klien_superadmin.get(f"/superadmin/piagam/juara/form:{f.pk}/unduh.pdf").status_code == 200
    # Seri di 3 besar ditolak tanpa centang.
    nilai_svc.kirim(rq, f, {"peringkat": 1}, {}, "Panitia 2", subjek_dari_kunci(f, f"K{ks[0].pk}"))
    f.agregasi = "TERAKHIR"
    f.save()
    r = klien_superadmin.post(f"/superadmin/piagam/juara/form/{f.pk}/", {"maks": "3"}, follow=True)
    assert "seri" in r.content.decode()


def test_piagam_juara_anjangsana(klien_superadmin, kontingen_madya, kontingen_wira):
    svc.pastikan_template_bawaan()
    p = buat_peserta(kontingen_wira, "TAMU")
    Kunjungan.objects.create(pengunjung=p, kontingen_tamu=kontingen_wira, kontingen_tuan_rumah=kontingen_madya)
    Review.objects.create(kontingen_tamu=kontingen_wira, kontingen_tuan_rumah=kontingen_madya, pengunjung=p,
                          nilai_pengetahuan=5, nilai_keterampilan=5, nilai_sikap=5)  # fmt: skip
    r = klien_superadmin.post("/superadmin/piagam/juara/anjangsana/", {"tingkat": "MADYA", "maks": "3"})
    assert halaman(r.content) == 1 and "Anjangsana Tingkat Madya" in teks_pdf(r.content)


def test_template_editor_latar_dan_validasi(klien_superadmin, template):
    c = klien_superadmin
    url = f"/superadmin/piagam/template/{template.pk}/"
    assert c.get(url).status_code == 200
    r = c.get(url + "pratinjau.png")
    assert r["Content-Type"] == "image/png" and Image.open(io.BytesIO(r.content)).width == 1100
    elemen = [{"teks": "{nama}", "x": "30", "y": 90, "lebar": 237, "font": "jahat", "ukuran": 500, "rata": "ATAS",
               "warna": "red; x", "baris_maks": 99}]  # fmt: skip
    r = c.post(url + "elemen/", json.dumps(elemen), content_type="application/json")
    assert r.json()["ok"]
    template.refresh_from_db()
    e = template.elemen[0]
    assert (e["font"], e["ukuran"], e["rata"], e["warna"], e["baris_maks"], e["x"]) == (
        "INTER",
        96,
        "TENGAH",
        "#1F2937",
        6,
        30.0,
    )
    r = c.post(url + "elemen/", json.dumps({"bukan": "daftar"}), content_type="application/json")
    assert r.status_code == 400
    # Latar gambar.
    buf = io.BytesIO()
    Image.new("RGB", (1754, 1240), (250, 240, 220)).save(buf, format="PNG")
    c.post(url, {"aksi": "latar", "latar": SimpleUploadedFile("desain.png", buf.getvalue(), content_type="image/png")})
    template.refresh_from_db()
    assert template.latar.endswith(".png") and template.latar_asli == "desain.png" and template.orientasi == "MENDATAR"
    assert not template.desain_bawaan
    # Latar PDF dari panitia diubah menjadi gambar.
    from reportlab.pdfgen import canvas as rl

    pdf = io.BytesIO()
    k = rl.Canvas(pdf, pagesize=(595, 842))
    k.drawString(100, 700, "Desain panitia")
    k.showPage()
    k.save()
    c.post(
        url,
        {"aksi": "latar", "latar": SimpleUploadedFile("desain.pdf", pdf.getvalue(), content_type="application/pdf")},
    )
    template.refresh_from_db()
    assert template.latar_asli == "desain.pdf" and template.orientasi == "TEGAK"
    # File bukan gambar ditolak; latar lama tetap.
    r = c.post(url, {"aksi": "latar", "latar": SimpleUploadedFile("x.png", b"bukan gambar")}, follow=True)
    assert "PNG/JPG atau PDF" in r.content.decode()
    template.refresh_from_db()
    assert template.latar_asli == "desain.pdf"
    assert c.get(url + "pratinjau.pdf")["Content-Type"] == "application/pdf"


def test_pengaturan_nomor_dan_hak_akses(klien_superadmin, panitia):
    r = klien_superadmin.post("/superadmin/piagam/", {
        "format_nomor_peserta": "PST-2026", "format_nomor_juara": "{urut}/JR", "digit_urut": "4",
        "tempat": "Tanjung Selor", "tanggal": "2026-11-15",
    })  # fmt: skip
    assert "Harus memuat {urut}" in r.content.decode()
    klien_superadmin.post("/superadmin/piagam/", {
        "format_nomor_peserta": "{urut}/PST", "format_nomor_juara": "{urut}/JR", "digit_urut": "4",
        "tempat": "Tanjung Selor", "tanggal": "2026-11-14",
    })  # fmt: skip
    assert svc.nomor_dari_format(JenisPiagam.PESERTA, 7) == "0007/PST"
    assert pengaturan.ambil("piagam.syarat_daftar_ulang") is False
    assert svc.data_umum()["tanggal"] == "14 November 2026"
    p = Client()
    masuk(p, "panitia")
    assert p.get("/superadmin/piagam/").status_code == 403


def test_simpan_pengaturan_template_angka_koma(klien_superadmin, template):
    r = klien_superadmin.post(f"/superadmin/piagam/template/{template.pk}/", {
        "aksi": "pengaturan", "t-nama": "Piagam peserta", "t-jenis": "PESERTA", "t-ukuran_kertas": "F4",
        "t-orientasi": "MENDATAR", "t-tempel_logo": "on", "t-logo_x": "0", "t-logo_y": "17,5", "t-logo_tinggi": "20",
        "t-aktif": "on",
    })  # fmt: skip
    assert r.status_code == 302
    template.refresh_from_db()
    assert (template.logo_y, template.ukuran_kertas, template.desain_bawaan) == (17.5, "F4", False)
    r = klien_superadmin.post("/superadmin/piagam/template/tambah/", {
        "aksi": "pengaturan", "t-nama": "Juara panitia", "t-jenis": "JUARA", "t-ukuran_kertas": "A4",
        "t-orientasi": "TEGAK", "t-logo_x": "0", "t-logo_y": "10", "t-logo_tinggi": "20", "t-aktif": "on",
    })  # fmt: skip
    baru = TemplatePiagam.objects.get(nama="Juara panitia")
    assert r.status_code == 302 and any(e["kode"] == "juara" for e in baru.elemen)
