"""Tempat sampah umum: form, kiriman form, kehadiran, review Anjangsana."""

from __future__ import annotations

from apps.absensi.models import Kehadiran
from apps.anjangsana.models import Review
from apps.inti.models import LogAktivitas
from apps.penilaian.models import Formulir, Kiriman, ModeForm, StatusForm

from .test_absensi import buat_peserta, buat_titik, kirim


def url(jenis, pk, aksi):
    return f"/superadmin/sampah/{jenis}/{pk}/{aksi}/"


def test_halaman_sampah_menampilkan_semua_jenis(klien_superadmin, kontingen_madya, panitia):
    f = Formulir.objects.create(slug="form-a", judul="Form A", mode=ModeForm.INPUT, status=StatusForm.AKTIF)
    f.hapus_lunak(oleh="Uji")
    t = buat_titik("TA-S1", status="BUKA")
    p = buat_peserta(kontingen_madya)
    kirim(panitia, t, "SJP:" + p.qr_token)
    Kehadiran.objects.get().hapus_lunak(oleh="Uji")
    isi = klien_superadmin.get("/superadmin/sampah/").content.decode()
    assert (
        "Form A" in isi and "Kehadiran yang dibatalkan" in isi and p.nama_lengkap in isi and "Review Anjangsana" in isi
    )


def test_pulihkan_dan_bentrok_form(klien_superadmin):
    lama = Formulir.objects.create(slug="sama", judul="Lama")
    lama.hapus_lunak()
    Formulir.objects.create(slug="sama", judul="Baru")
    r = klien_superadmin.post(url("form", lama.pk, "pulihkan"), follow=True)
    assert "Slug form sudah dipakai" in r.content.decode() and Formulir.semua.get(pk=lama.pk).terhapus
    Formulir.objects.get(judul="Baru").hapus_lunak()
    klien_superadmin.post(url("form", lama.pk, "pulihkan"))
    assert not Formulir.semua.get(pk=lama.pk).terhapus
    assert LogAktivitas.objects.filter(aksi="sampah.form_dipulihkan").exists()


def test_kiriman_dan_hapus_permanen(klien_superadmin, kontingen_madya):
    f = Formulir.objects.create(slug="nilai", judul="Nilai", mode=ModeForm.PENILAIAN, jenis_subjek="KONTINGEN")
    x = Kiriman.objects.create(formulir=f, kontingen=kontingen_madya, nama_pengisi="Budi", data={"a": 1})
    x.hapus_lunak()
    f.hapus_lunak()
    r = klien_superadmin.post(url("kiriman", x.pk, "pulihkan"), follow=True)
    assert "Pulihkan form-nya dulu" in r.content.decode()
    r = klien_superadmin.post(url("form", f.pk, "hapus-permanen"), follow=True)
    assert "masih punya kiriman" in r.content.decode() and Formulir.semua.filter(pk=f.pk).exists()
    f.pulihkan()
    Kiriman.objects.create(formulir=f, kontingen=kontingen_madya, nama_pengisi="budi", data={"a": 2})
    r = klien_superadmin.post(url("kiriman", x.pk, "pulihkan"), follow=True)
    assert "sudah punya kiriman aktif" in r.content.decode()
    klien_superadmin.post(url("kiriman", x.pk, "hapus-permanen"))
    assert not Kiriman.semua.filter(pk=x.pk).exists()
    assert LogAktivitas.objects.filter(aksi="sampah.kiriman_dihapus_permanen").exists()


def test_kehadiran_dan_review_bentrok(klien_superadmin, kontingen_madya, kontingen_wira, panitia):
    t = buat_titik("TA-S2", status="BUKA")
    p = buat_peserta(kontingen_madya)
    kirim(panitia, t, "SJP:" + p.qr_token)
    k1 = Kehadiran.objects.get()
    k1.hapus_lunak()
    kirim(panitia, t, "SJP:" + p.qr_token)  # dipindai lagi setelah dibatalkan
    r = klien_superadmin.post(url("kehadiran", k1.pk, "pulihkan"), follow=True)
    assert "sudah tercatat hadir lagi" in r.content.decode()
    rv = Review.objects.create(kontingen_tamu=kontingen_madya, kontingen_tuan_rumah=kontingen_wira, pengunjung=p,
                               nilai_pengetahuan=1, nilai_keterampilan=1, nilai_sikap=1)  # fmt: skip
    rv.hapus_lunak()
    klien_superadmin.post(url("review", rv.pk, "pulihkan"))
    assert not Review.semua.get(pk=rv.pk).terhapus
    assert klien_superadmin.post(url("hantu", 1, "pulihkan"), follow=True).status_code == 200


def test_sampah_hanya_superadmin(panitia):
    from django.test import Client

    from .conftest import masuk

    c = Client()
    masuk(c, "panitia")
    assert c.post(url("form", 1, "pulihkan")).status_code == 403
