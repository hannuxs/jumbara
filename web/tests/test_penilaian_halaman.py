"""Tes halaman form builder: superadmin, juri, publik, hak akses, template."""

from __future__ import annotations

import io
import json

import openpyxl
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client

from apps.absensi.models import Kegiatan
from apps.inti.models import LogAktivitas
from apps.kontingen.models import Kontingen
from apps.penilaian.hasil import tabel_hasil
from apps.penilaian.models import AksesForm, Formulir, JenisKolom, Kiriman, Kolom, ModeForm, StatusForm

from .conftest import masuk


@pytest.fixture
def kontingen3(db):
    return [
        Kontingen.objects.create(kode=f"WI-0{i}", nama=f"SMA Uji {i}", tingkat="WIRA", kuota=10) for i in range(1, 4)
    ]


@pytest.fixture
def klien_juri(juri):
    c = Client()
    masuk(c, "juri")
    return c


def buat_form_lewat_halaman(c: Client) -> Formulir:
    r = c.post("/superadmin/form/tambah/", {
        "judul": "Penilaian Drama Wira", "mode": "PENILAIAN", "status": "AKTIF", "akses": "JURI",
        "jenis_subjek": "KONTINGEN", "tingkat": "WIRA", "jenis_penilaian": "BIASA", "agregasi": "RATA",
        "jumlah_juri": "2", "arah_urut": "TURUN", "slug": "", "kunci_ref": "penilaian-drama",
    })  # fmt: skip
    assert r.status_code == 302, r.content.decode()[:3000]
    f = Formulir.objects.get(slug="penilaian-drama-wira")
    for kode in ("akting", "tema"):
        r = c.post(f"/superadmin/form/{f.pk}/kolom/tambah/", {"jenis": "ANGKA", "label": kode.title(), "kode": kode,
                                                              "min": "0", "max": "100", "desimal": "0", "wajib": "1"})  # fmt: skip
        assert r.status_code == 302
    r = c.post(f"/superadmin/form/{f.pk}/kolom/tambah/", {"jenis": "RUMUS", "label": "Nilai Akhir", "kode": "nilai_akhir",
                                                          "rumus": "AVG([akting], [tema])", "tampil_desimal": "2"})  # fmt: skip
    assert r.status_code == 302
    f.refresh_from_db()
    r = c.post(f"/superadmin/form/{f.pk}/pengaturan/", {
        "judul": f.judul, "mode": "PENILAIAN", "status": "AKTIF", "akses": "JURI", "jenis_subjek": "KONTINGEN",
        "tingkat": "WIRA", "jenis_penilaian": "BIASA", "agregasi": "RATA", "jumlah_juri": "2", "arah_urut": "TURUN",
        "slug": f.slug, "kunci_ref": "penilaian-drama", "kolom_urut": "nilai_akhir",
    })  # fmt: skip
    assert r.status_code == 302
    f.refresh_from_db()
    return f


def test_superadmin_bangun_form_dan_juri_mengisi(klien_superadmin, klien_juri, kontingen3):
    c = klien_superadmin
    f = buat_form_lewat_halaman(c)
    assert f.kolom_urut == "nilai_akhir" and list(f.kolom.values_list("kode", flat=True)) == [
        "akting",
        "tema",
        "nilai_akhir",
    ]
    for url in ["/superadmin/form/", f"/superadmin/form/{f.pk}/", f"/superadmin/form/{f.pk}/kolom/tambah/?jenis=RUMUS",
                f"/superadmin/form/{f.pk}/pratinjau/", f"/superadmin/form/{f.pk}/hasil/", f"/superadmin/isi/{f.slug}/"]:  # fmt: skip
        assert c.get(url).status_code == 200, url
    # Cek rumus langsung.
    cek = c.post(
        f"/superadmin/form/{f.pk}/rumus/cek/",
        json.dumps({"kode": "x", "rumus": "[akting] *"}),
        content_type="application/json",
    )
    assert cek.json()["ok"] is False
    cek = c.post(
        f"/superadmin/form/{f.pk}/rumus/cek/",
        json.dumps({"kode": "x", "rumus": "[akting] x 2"}),
        content_type="application/json",
    )
    assert cek.json()["ok"] is True and len(cek.json()["contoh"]) == 3
    # Juri: daftar form, subjek, isi.
    j = klien_juri
    assert f.judul in j.get("/juri/").content.decode()
    k1 = kontingen3[0]
    halaman = j.get(f"/juri/{f.slug}/?nama=Budi").content.decode()
    assert "SMA Uji 1" in halaman and "belum" in halaman
    url_isi = f"/juri/{f.slug}/K{k1.pk}/"
    assert j.get(url_isi).status_code == 200
    r = j.post(url_isi, {"nama_pengisi": "Budi", "k_akting": "101", "k_tema": "80"})
    assert "Paling besar 100" in r.content.decode() and not Kiriman.objects.exists()
    r = j.post(
        url_isi,
        {
            "nama_pengisi": "Budi",
            "k_akting": "90",
            "k_tema": "80",
            "client_uuid": "a1b2c3d4-0000-4000-8000-000000000001",
        },
    )
    assert r.status_code == 302 and "nama=Budi" in r["Location"]
    r = j.post(url_isi, {"nama_pengisi": "Budi", "k_akting": "10", "k_tema": "10"})
    assert "tidak bisa diubah" in r.content.decode()
    j.post(url_isi, {"nama_pengisi": "Sari", "k_akting": "70", "k_tema": "60"})
    b = tabel_hasil(f).baris_subjek(f"K{k1.pk}")
    assert b.nilai["akting"] == 80 and b.nilai["nilai_akhir"] == pytest.approx(75) and b.peringkat == 1
    # Juri tidak bisa melihat hasil (bawaan) dan tidak bisa membuka halaman superadmin.
    assert j.get(f"/juri/{f.slug}/hasil/").status_code == 404
    assert j.get("/superadmin/form/").status_code == 403
    # Superadmin: tabel hasil, Excel, buka kunci kiriman, kunci form.
    isi = c.get(f"/superadmin/form/{f.pk}/hasil/").content.decode()
    assert "SMA Uji 1" in isi and "belum dinilai" in isi
    wb = openpyxl.load_workbook(io.BytesIO(c.get(f"/superadmin/form/{f.pk}/hasil/?unduh=xlsx").content))
    teks = str(list(wb.active.iter_rows(values_only=True)))
    assert "SMA Uji 1" in teks and "Budi" in teks
    x = Kiriman.objects.get(nama_pengisi="Budi")
    c.post(f"/superadmin/form/{f.pk}/kiriman/{x.pk}/", {"aksi": "buka"})
    assert j.post(url_isi, {"nama_pengisi": "Budi", "k_akting": "100", "k_tema": "100"}).status_code == 302
    x.refresh_from_db()
    assert x.data["akting"] == 100 and x.terkunci and len(x.riwayat) == 1
    c.post(f"/superadmin/form/{f.pk}/kunci/", {"kunci": "1"})
    r = j.post(f"/juri/{f.slug}/K{kontingen3[1].pk}/", {"nama_pengisi": "Budi", "k_akting": "1", "k_tema": "1"})
    assert "dikunci" in r.content.decode()
    aksi = set(LogAktivitas.objects.values_list("aksi", flat=True))
    assert {"form.dibuat", "form.kolom_ditambah", "form.kiriman_baru", "form.kiriman_dibuka", "form.dikunci"} <= aksi


def test_ubah_hapus_dan_urutan_kolom(klien_superadmin, kontingen3):
    c = klien_superadmin
    f = buat_form_lewat_halaman(c)
    akting = f.kolom.get(kode="akting")
    r = c.post(f"/superadmin/form/{f.pk}/kolom/{akting.pk}/hapus/", follow=True)
    assert "dipakai" in r.content.decode() and f.kolom.filter(kode="akting").exists()
    ids = list(f.kolom.values_list("pk", flat=True))[::-1]
    r = c.post(f"/superadmin/form/{f.pk}/kolom/urutan/", json.dumps(ids), content_type="application/json")
    assert r.json()["ok"] and list(f.kolom.values_list("pk", flat=True)) == ids
    r = c.post(f"/superadmin/form/{f.pk}/kolom/urutan/", json.dumps(ids[:1]), content_type="application/json")
    assert r.status_code == 400
    c.post(f"/superadmin/form/{f.pk}/salin/", {"tingkat": "MADYA"})
    salinan = Formulir.objects.exclude(pk=f.pk).get()
    assert salinan.tingkat == "MADYA" and salinan.status == StatusForm.DRAF and salinan.kolom.count() == 3
    c.post(f"/superadmin/form/{f.pk}/hapus/")
    assert not Formulir.objects.filter(pk=f.pk).exists() and Formulir.semua.filter(pk=f.pk).exists()


def test_form_publik_mode_1_dengan_berkas(kontingen3, klien_superadmin, settings):
    f = Formulir.objects.create(slug="parade-budaya", judul="Pendaftaran Parade Budaya", mode=ModeForm.INPUT,
                                status=StatusForm.AKTIF, akses=AksesForm.PUBLIK, jenis_subjek="KONTINGEN",
                                tingkat="SEMUA", satu_per_subjek=True)  # fmt: skip
    Kolom.objects.create(formulir=f, kode="tema", label="Tema", jenis=JenisKolom.TEKS, wajib=True, urutan=1)
    Kolom.objects.create(formulir=f, kode="jumlah", label="Jumlah penampil", jenis=JenisKolom.ANGKA, urutan=2,
                         pengaturan={"min": 1, "max": 30, "desimal": 0})  # fmt: skip
    Kolom.objects.create(formulir=f, kode="kostum", label="Kostum", jenis=JenisKolom.CENTANG, urutan=3,
                         pengaturan={"pilihan": ["Adat", "Modern"]})  # fmt: skip
    Kolom.objects.create(formulir=f, kode="surat", label="Surat", jenis=JenisKolom.BERKAS, urutan=4,
                         pengaturan={"tipe_berkas": ["pdf"], "ukuran_mb": 1})  # fmt: skip
    p = Client()
    halaman = p.get("/f/parade-budaya/").content.decode()
    assert "SMA Uji 1" in halaman and "Nama pengisi" in halaman
    k = kontingen3[0]
    palsu = SimpleUploadedFile("surat.pdf", b"MZ bukan pdf", content_type="application/pdf")
    r = p.post("/f/parade-budaya/", {"subjek_kunci": f"K{k.pk}", "nama_pengisi": "Bu Ani", "k_tema": "Dayak",
                                      "k_jumlah": "12", "k_kostum": ["Adat"], "k_surat": palsu})  # fmt: skip
    assert "tidak sesuai" in r.content.decode()
    asli = SimpleUploadedFile("surat.pdf", b"%PDF-1.4 isi", content_type="application/pdf")
    r = p.post("/f/parade-budaya/", {"subjek_kunci": f"K{k.pk}", "nama_pengisi": "Bu Ani", "k_tema": "Dayak",
                                      "k_jumlah": "12", "k_kostum": ["Adat"], "k_surat": asli})  # fmt: skip
    assert r.status_code == 302 and r["Location"] == "/f/parade-budaya/terkirim/"
    x = Kiriman.objects.get()
    assert x.data["kostum"] == ["Adat"] and x.data["jumlah"] == 12 and x.data["surat"]["nama"] == "surat.pdf"
    r = p.post(
        "/f/parade-budaya/", {"subjek_kunci": f"K{k.pk}", "nama_pengisi": "Pak Budi", "k_tema": "Lain", "k_jumlah": "3"}
    )
    assert "sudah punya kiriman" in r.content.decode()
    # Berkas hanya untuk superadmin.
    url_berkas = f"/superadmin/form/{f.pk}/kiriman/{x.pk}/berkas/surat/"
    assert p.get(url_berkas).status_code == 302
    unduh = klien_superadmin.get(url_berkas)
    assert unduh.status_code == 200 and b"".join(unduh.streaming_content).startswith(b"%PDF")
    rekap = klien_superadmin.get(f"/superadmin/form/{f.pk}/hasil/").content.decode()
    assert "Dayak" in rekap and "Adat" in rekap
    # Form draf / juri tidak bisa dibuka publik.
    f.status = StatusForm.DRAF
    f.save()
    assert p.get("/f/parade-budaya/").status_code == 404


def test_validasi_pengaturan_form(klien_superadmin):
    r = klien_superadmin.post("/superadmin/form/tambah/", {
        "judul": "Data peserta", "mode": "INPUT", "status": "DRAF", "akses": "PUBLIK", "jenis_subjek": "PESERTA",
        "tingkat": "SEMUA", "jenis_penilaian": "BIASA", "agregasi": "RATA", "jumlah_juri": "1", "arah_urut": "TURUN",
    })  # fmt: skip
    assert r.status_code == 200 and "daftar nama tidak boleh publik" in r.content.decode()
    r = klien_superadmin.post("/superadmin/form/tambah/", {
        "judul": "Nilai", "mode": "PENILAIAN", "status": "DRAF", "akses": "JURI", "jenis_subjek": "BEBAS",
        "tingkat": "SEMUA", "jenis_penilaian": "BIASA", "agregasi": "RATA", "jumlah_juri": "1", "arah_urut": "TURUN",
    })  # fmt: skip
    assert "harus per kontingen" in r.content.decode()
    assert not Formulir.objects.exists()


def test_hak_akses(panitia, juri):
    p = Client()
    masuk(p, "panitia")
    assert p.get("/superadmin/form/").status_code == 403
    assert p.get("/juri/").status_code == 403
    publik = Client()
    assert publik.get("/juri/").status_code == 302
    assert publik.get("/superadmin/form/").status_code == 302


def test_perintah_template_penilaian(db):
    for kode in ("traveling", "jurnalistik", "kewirausahaan", "drama", "got-talent", "ranking-1", "wahana",
                 "bakti-masyarakat", "ngobrol-bareng", "sarasehan-medsos", "sarasehan-pergaulan"):  # fmt: skip
        Kegiatan.objects.create(kode=kode, nama=kode.title(), kelompok="JUMPA")
    call_command("sigap_buat_template_penilaian")
    assert Formulir.objects.filter(status=StatusForm.DRAF, perlu_konfirmasi=True).count() == Formulir.objects.count()
    assert Formulir.objects.filter(slug="penilaian-traveling-madya", kunci_ref="penilaian-traveling").exists()
    gt = Formulir.objects.get(slug="penilaian-got-talent")
    assert gt.tingkat == "SEMUA" and gt.jumlah_juri == 3
    assert Formulir.objects.get(slug="wahana-bakiak-wira").arah_urut == "NAIK"
    ju = Formulir.objects.get(slug="juara-umum-madya")
    assert ju.akses == AksesForm.SUPERADMIN and ju.kolom.filter(kode="poin_traveling").exists()
    n = Formulir.objects.count()
    call_command("sigap_buat_template_penilaian")  # aman diulang
    assert Formulir.objects.count() == n
