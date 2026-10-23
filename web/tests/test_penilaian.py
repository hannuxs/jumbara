"""Tes form penilaian (docs/16-FORM-BUILDER.md): agregasi juri, kolom otomatis, rumus, REF, peringkat, kunci."""

from __future__ import annotations

import pytest
from django.test import RequestFactory

from apps.absensi.models import Kegiatan
from apps.akun.models import Pengguna
from apps.inti.models import LogAktivitas
from apps.kontingen.models import Kontingen
from apps.penilaian import services as svc
from apps.penilaian.hasil import Penghitung, hitung_peringkat, subjek_dari_kunci, tabel_hasil
from apps.penilaian.models import (
    AksesForm,
    ArahUrut,
    Formulir,
    JenisKolom,
    JenisPenilaian,
    JenisSubjek,
    Kiriman,
    Kolom,
    ModeForm,
    PemecahSeri,
    StatusForm,
)

from .test_absensi import buat_peserta, buat_titik
from .test_absensi import kirim as pindai


def req(user=None):
    r = RequestFactory().post("/")
    r.user = user or Pengguna.objects.get(username="superadmin")
    r.nama_pelaku = "Uji"
    r.perangkat_id = ""
    return r


@pytest.fixture
def madya(db, superadmin):
    return [
        Kontingen.objects.create(kode=f"MA-0{i}", nama=f"SMP Uji {i}", tingkat="MADYA", kuota=10) for i in range(1, 5)
    ]


@pytest.fixture
def traveling(db):
    return Kegiatan.objects.create(kode="traveling", nama="Traveling", kelompok="JUMPA", kuota_default=2)


def form_nilai(slug="penilaian-traveling-madya", kegiatan=None, tingkat="MADYA", kunci_ref="penilaian-traveling", **kw):
    data = {
        "slug": slug, "kunci_ref": kunci_ref, "judul": slug, "mode": ModeForm.PENILAIAN, "status": StatusForm.AKTIF,
        "akses": AksesForm.JURI, "jenis_subjek": JenisSubjek.KONTINGEN, "kegiatan": kegiatan, "tingkat": tingkat,
        "kolom_urut": "nilai_akhir", "jumlah_juri": 2,
    }  # fmt: skip
    data.update(kw)
    return Formulir.objects.create(**data)


def kolom(f, kode, jenis=JenisKolom.ANGKA, **p):
    return Kolom.objects.create(formulir=f, kode=kode, label=kode.title(), jenis=jenis, wajib=True,
                                urutan=Kolom.objects.filter(formulir=f).count() * 10, pengaturan=p)  # fmt: skip


def nilai(f, k, juri, **data):
    s = subjek_dari_kunci(f, f"K{k.pk}")
    return svc.kirim(req(Pengguna.objects.get(username="juri")), f, data, {}, juri, s)


@pytest.fixture
def juri_akun(juri):
    return juri


def test_tabel_traveling_agregasi_poin_peringkat(madya, traveling, panitia, juri_akun):
    f = form_nilai(kegiatan=traveling)
    for kode in ("pengetahuan", "sikap", "keterampilan"):
        kolom(f, kode, min=0, max=100)
    kolom(f, "nilai_akhir", JenisKolom.RUMUS,
          rumus="0.25*[pengetahuan] + 0.25*[sikap] + 0.5*[keterampilan] + [poin_kehadiran]")  # fmt: skip
    a, b, c, d = madya
    # Kehadiran: A hadir 2 (kuota 2 -> poin 2), B hadir 1 (poin 0), C dan D tidak hadir (poin -2).
    t = buat_titik("TA-TR", tingkat="MADYA", kegiatan=traveling, status="BUKA")
    for p in [buat_peserta(a, "A1"), buat_peserta(a, "A2"), buat_peserta(b, "B1")]:
        assert pindai(panitia, t, "SJP:" + p.qr_token).status == "HIJAU"
    nilai(f, a, "Juri Satu", pengetahuan=80, sikap=80, keterampilan=80)
    nilai(f, a, "Juri Dua", pengetahuan=90, sikap=90, keterampilan=90)  # rata-rata 85
    nilai(f, b, "Juri Satu", pengetahuan=86, sikap=86, keterampilan=86)
    nilai(f, c, "Juri Satu", pengetahuan=89, sikap=89, keterampilan=89)
    tab = tabel_hasil(f)
    per = {x.subjek.kontingen.kode: x for x in tab.baris}
    assert per["MA-01"].nilai["pengetahuan"] == 85 and per["MA-01"].jumlah_juri == 2
    assert per["MA-01"].nilai["poin_kehadiran"] == 2 and per["MA-02"].nilai["poin_kehadiran"] == 0
    assert per["MA-01"].nilai["nilai_akhir"] == pytest.approx(87)
    assert per["MA-02"].nilai["nilai_akhir"] == pytest.approx(86)
    assert per["MA-03"].nilai["nilai_akhir"] == pytest.approx(87)  # 89 - 2
    assert (per["MA-01"].peringkat, per["MA-03"].peringkat, per["MA-02"].peringkat) == (1, 1, 3)
    assert per["MA-01"].seri and per["MA-03"].seri and not per["MA-02"].seri
    assert per["MA-04"].belum_dinilai and per["MA-04"].nilai["pengetahuan"] is None
    assert per["MA-04"].nilai["nilai_akhir"] == pytest.approx(-2)
    assert per["MA-04"].peringkat is None  # belum dinilai juri: tanpa peringkat
    assert "poin_kehadiran" in tab.bawaan_tampil and "jumlah_juri" in tab.bawaan_tampil
    # Pemecah seri manual: MA-03 di atas MA-01.
    PemecahSeri.objects.create(formulir=f, kunci_subjek=f"K{c.pk}", nilai=1)
    PemecahSeri.objects.create(formulir=f, kunci_subjek=f"K{a.pk}", nilai=2)
    per = {x.subjek.kontingen.kode: x for x in tabel_hasil(f).baris}
    assert (per["MA-03"].peringkat, per["MA-01"].peringkat) == (1, 2) and not per["MA-01"].seri


def test_agregasi_jumlah_dan_terakhir(madya, juri_akun):
    a = madya[0]
    f = form_nilai(agregasi="JUMLAH")
    kolom(f, "skor", max=10)
    nilai(f, a, "J1", skor=4)
    nilai(f, a, "J2", skor=5)
    assert tabel_hasil(f).baris_subjek(f"K{a.pk}").nilai["skor"] == 9
    f.agregasi = "TERAKHIR"
    f.save()
    assert tabel_hasil(f).baris_subjek(f"K{a.pk}").nilai["skor"] == 5


def test_form_gugur_dan_ref_juara_umum(madya, juri_akun):
    a, b, c, _ = madya
    gugur = form_nilai("ranking-1-madya", kunci_ref="ranking-1", kolom_urut="peringkat", arah_urut=ArahUrut.NAIK,
                       jenis_penilaian=JenisPenilaian.GUGUR)  # fmt: skip
    kolom(gugur, "peringkat", min=1, max=99)
    for k, p in [(a, 2), (b, 1), (c, 3)]:
        svc.kirim(req(), gugur, {"peringkat": p}, {}, "Panitia Lomba", subjek_dari_kunci(gugur, f"K{k.pk}"))
    # Form Wira dengan kunci yang sama tidak boleh tertukar.
    form_nilai("ranking-1-wira", kunci_ref="ranking-1", tingkat="WIRA", kolom_urut="peringkat")
    ju = form_nilai("juara-umum-madya", kunci_ref="juara-umum", kolom_urut="total", akses=AksesForm.SUPERADMIN)
    kolom(ju, "poin_r1", JenisKolom.RUMUS, rumus='POIN_PERINGKAT(REF("ranking-1", "peringkat"), 10, 8, 6)')
    kolom(ju, "total", JenisKolom.RUMUS, rumus="SUM([poin_r1])")
    per = {x.subjek.kontingen.kode: x for x in tabel_hasil(ju).baris}
    assert per["MA-02"].nilai["poin_r1"] == 10 and per["MA-01"].nilai["poin_r1"] == 8
    assert per["MA-03"].nilai["poin_r1"] == 6 and per["MA-04"].nilai["poin_r1"] == 0
    assert per["MA-02"].peringkat == 1


def test_kolom_peringkat_dan_fungsi_peringkat(madya, juri_akun):
    f = form_nilai(kolom_urut="")
    kolom(f, "skor", max=100)
    Kolom.objects.create(formulir=f, kode="rank_skor", label="Rank", jenis=JenisKolom.PERINGKAT, urutan=90,
                         pengaturan={"dasar": "skor", "arah": "TURUN"})  # fmt: skip
    kolom(f, "bonus", JenisKolom.RUMUS, rumus='IF(PERINGKAT([skor]) = 1, 5, 0) + PERINGKAT([skor], "NAIK")')
    for k, s in zip(madya[:3], (70, 90, 80), strict=True):
        nilai(f, k, "J", skor=s)
    per = {x.subjek.kontingen.kode: x for x in tabel_hasil(f).baris}
    assert [per[k].nilai["rank_skor"] for k in ("MA-01", "MA-02", "MA-03")] == [3, 1, 2]
    assert per["MA-02"].nilai["bonus"] == 5 + 3 and per["MA-01"].nilai["bonus"] == 1
    assert per["MA-04"].nilai["rank_skor"] is None


def test_bagi_nol_jadi_kosong_dengan_peringatan(madya, juri_akun):
    f = form_nilai(kolom_urut="hasil")
    kolom(f, "a")
    kolom(f, "b")
    kolom(f, "hasil", JenisKolom.RUMUS, rumus="[a] / [b]")
    nilai(f, madya[0], "J", a=5, b=0)
    b = tabel_hasil(f).baris_subjek(f"K{madya[0].pk}")
    assert b.nilai["hasil"] is None and b.peringkat is None and "Pembagian dengan nol" in b.peringatan[0]


def test_validasi_rumus_saat_simpan(madya):
    f = form_nilai()
    kolom(f, "a")
    kolom(f, "catatan", JenisKolom.TEKS)
    data = {"jenis": JenisKolom.RUMUS, "label": "B"}
    for rumus, pesan in [
        ("[tidak_ada] + 1", "tidak ada di form ini"),
        ("[catatan] + 1", "berisi teks"),
        ("[b] + 1", "dirinya sendiri"),
        ('REF("form-hantu", "x")', "tidak ditemukan"),
        ("1 +", "berakhir terlalu cepat"),
    ]:
        with pytest.raises(svc.GagalForm) as e:
            svc.simpan_kolom(req(), f, {**data, "kode": "b", "rumus": rumus})
        assert pesan in e.value.pesan, rumus
    svc.simpan_kolom(req(), f, {**data, "kode": "b", "rumus": "[a] * 2"})
    c = svc.simpan_kolom(req(), f, {**data, "kode": "c", "label": "C", "rumus": "[b] + 1"})
    # Mengubah b agar memakai c -> melingkar.
    with pytest.raises(svc.GagalForm) as e:
        svc.simpan_kolom(req(), f, {**data, "kode": "b", "rumus": "[c] + 1"}, kolom=f.kolom.get(kode="b"))
    assert "melingkar" in e.value.pesan
    # Kolom yang dipakai rumus tidak bisa dihapus atau diganti kodenya.
    with pytest.raises(svc.GagalForm):
        svc.hapus_kolom(req(), f.kolom.get(kode="a"))
    with pytest.raises(svc.GagalForm):
        svc.simpan_kolom(req(), f, {"jenis": "ANGKA", "label": "A", "kode": "a2"}, kolom=f.kolom.get(kode="a"))
    assert c.atur("rumus") == "[b] + 1"
    assert LogAktivitas.objects.filter(aksi="form.kolom_ditambah").count() == 2


def test_ref_melingkar_antar_form_ditolak(madya):
    a = form_nilai("form-a", kunci_ref="", kolom_urut="")
    b = form_nilai("form-b", kunci_ref="", kolom_urut="")
    kolom(a, "x")
    kolom(b, "y")
    svc.simpan_kolom(req(), b, {"jenis": "RUMUS", "label": "Dari A", "kode": "dari_a", "rumus": 'REF("form-a", "x")'})
    with pytest.raises(svc.GagalForm) as e:
        svc.simpan_kolom(
            req(), a, {"jenis": "RUMUS", "label": "Dari B", "kode": "dari_b", "rumus": 'REF("form-b", "dari_a")'}
        )
    assert "melingkar" in e.value.pesan
    with pytest.raises(svc.GagalForm) as e:
        svc.simpan_kolom(req(), a, {"jenis": "RUMUS", "label": "Z", "kode": "z", "rumus": 'REF("form-b", "hantu")'})
    assert "tidak ada" in e.value.pesan


def test_kiriman_juri_terkunci_dan_dibuka_superadmin(madya, juri_akun):
    f = form_nilai(kolom_urut="")
    kolom(f, "skor", min=0, max=100)
    a = madya[0]
    x, diganti = nilai(f, a, "Budi", skor=70)
    assert not diganti and x.terkunci
    with pytest.raises(svc.GagalForm) as e:
        nilai(f, a, "budi", skor=99)  # nama sama (beda huruf besar) -> ditolak
    assert "tidak bisa diubah" in e.value.pesan
    nilai(f, a, "Sari", skor=80)  # juri lain boleh
    svc.atur_kunci_kiriman(req(), x, False)
    y, diganti = nilai(f, a, "Budi", skor=75)
    assert diganti and y.pk == x.pk and y.data["skor"] == 75 and y.riwayat[0]["data"]["skor"] == 70 and y.terkunci
    assert Kiriman.objects.filter(formulir=f).count() == 2
    svc.atur_kunci_form(req(), f, True)
    with pytest.raises(svc.GagalForm) as e:
        nilai(f, madya[1], "Budi", skor=60)
    assert "dikunci" in e.value.pesan
    assert LogAktivitas.objects.filter(aksi__in=["form.kiriman_dibuka", "form.dikunci"]).count() == 2


def test_form_tutup_dan_client_uuid_idempoten(madya, juri_akun):
    f = form_nilai(kolom_urut="", status=StatusForm.DRAF)
    kolom(f, "skor")
    with pytest.raises(svc.GagalForm) as e:
        nilai(f, madya[0], "Budi", skor=1)
    assert "tidak dibuka" in e.value.pesan
    f.status = StatusForm.AKTIF
    f.save()
    s = subjek_dari_kunci(f, f"K{madya[0].pk}")
    cu = "8b2d3f4e-1111-4222-8333-944455556666"
    x1, _ = svc.kirim(req(Pengguna.objects.get(username="juri")), f, {"skor": 1}, {}, "Budi", s, client_uuid=cu)
    x2, _ = svc.kirim(req(Pengguna.objects.get(username="juri")), f, {"skor": 1}, {}, "Budi", s, client_uuid=cu)
    assert x1.pk == x2.pk and Kiriman.objects.count() == 1


def test_salin_form_dan_peringkat_umum(madya):
    f = form_nilai()
    kolom(f, "a")
    kolom(f, "nilai_akhir", JenisKolom.RUMUS, rumus="[a] * 2")
    baru = svc.salin_form(req(), f, tingkat="WIRA")
    assert baru.slug != f.slug and baru.status == StatusForm.DRAF and baru.tingkat == "WIRA"
    assert list(baru.kolom.values_list("kode", flat=True)) == ["a", "nilai_akhir"]
    p, seri = hitung_peringkat({"x": 5, "y": 7, "z": 7, "w": None}, naik=False)
    assert p == {"y": 1, "z": 1, "x": 3} and seri == {"y", "z"}


def test_ref_anjangsana(madya):
    from apps.anjangsana.models import Kunjungan, Review

    a, b, *_ = madya
    p = buat_peserta(b, "TAMU")
    Kunjungan.objects.create(pengunjung=p, kontingen_tamu=b, kontingen_tuan_rumah=a)
    Review.objects.create(kontingen_tamu=b, kontingen_tuan_rumah=a, pengunjung=p, nilai_pengetahuan=5,
                          nilai_keterampilan=4, nilai_sikap=3)  # fmt: skip
    f = form_nilai("ju", kunci_ref="", kolom_urut="")
    kolom(f, "anj", JenisKolom.RUMUS, rumus='REF("anjangsana", "rata_rata") * 10')
    kolom(f, "anj_p", JenisKolom.RUMUS, rumus='REF("anjangsana", "peringkat")')
    per = {x.subjek.kontingen.kode: x for x in Penghitung().tabel(f).baris}
    assert per["MA-01"].nilai["anj"] == pytest.approx(40) and per["MA-01"].nilai["anj_p"] == 1
    with pytest.raises(svc.GagalForm):
        svc.simpan_kolom(req(), f, {"jenis": "RUMUS", "label": "X", "kode": "x", "rumus": 'REF("anjangsana", "hantu")'})
