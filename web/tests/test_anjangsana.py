"""Tes Anjangsana (docs/17-ANJANGSANA.md): sesi, alur dua konfirmasi, review, peringkat."""

from __future__ import annotations

import io
import json
from datetime import date, datetime, time, timedelta

import openpyxl
import pytest
from django.test import Client
from django.utils import timezone

from apps.anjangsana import services as svc
from apps.anjangsana.models import Kunjungan, Review, SesiAnjangsana
from apps.biodata.models import Peserta
from apps.inti import pengaturan
from apps.inti.models import LogAktivitas
from apps.inti.pengaturan import StatusPaksa
from apps.kontingen.models import Kontingen

from .conftest import masuk
from .test_absensi import buat_peserta

WITA = timezone.get_fixed_timezone(8 * 60)


@pytest.fixture
def buka(db):
    pengaturan.simpan("anjangsana.paksa_status", StatusPaksa.BUKA)


@pytest.fixture
def kontingen_mula(db):
    return Kontingen.objects.create(kode="MU-01", nama="SD Negeri Uji", tingkat="MULA", kuota=10)


def api(c: Client, alamat: str, data: dict):
    r = c.post(f"/anjangsana/api/{alamat}", json.dumps(data), content_type="application/json")
    return r.status_code, r.json()


def kunjungi(c: Client, pengunjung, tuan: Kontingen, nilai=(5, 4, 3), komentar="", ganti=False):
    """Alur lengkap: kartu -> tuan rumah -> kunjungan -> review. Mengembalikan jawaban review."""
    _, j = api(c, "kartu", {"teks": "SJP:" + pengunjung.qr_token})
    assert j["ok"], j
    _, j2 = api(c, "tuan-rumah", {"tiket": j["tiket"], "teks": "SJK:" + tuan.qr_token})
    assert j2["ok"], j2
    _, j3 = api(c, "kunjungan", {"tiket_tuan": j2["tiket_tuan"]})
    assert j3["ok"], j3
    n = dict(zip(["pengetahuan", "keterampilan", "sikap"], nilai, strict=True))
    return api(
        c, "review", {"tiket_kunjungan": j3["tiket_kunjungan"], "nilai": n, "komentar": komentar, "ganti": ganti}
    )


def test_status_ikut_sesi(db):
    SesiAnjangsana.objects.create(tanggal=date(2026, 11, 13), mulai=time(8, 0), selesai=time(11, 30))
    SesiAnjangsana.objects.create(tanggal=date(2026, 11, 14), mulai=time(8, 0), selesai=time(11, 30))
    di_sesi = datetime(2026, 11, 13, 9, 0, tzinfo=WITA)
    luar = datetime(2026, 11, 13, 12, 0, tzinfo=WITA)
    assert svc.status(di_sesi).terbuka
    st = svc.status(luar)
    assert not st.terbuka and st.berikutnya.tanggal == date(2026, 11, 14)
    pengaturan.simpan("anjangsana.paksa_status", StatusPaksa.TUTUP)
    assert not svc.status(di_sesi).terbuka
    pengaturan.simpan("anjangsana.paksa_status", StatusPaksa.BUKA)
    assert svc.status(luar).terbuka


def test_halaman_tutup_dan_api_ditolak(db, kontingen_madya):
    SesiAnjangsana.objects.create(
        tanggal=timezone.localdate() + timedelta(days=1), mulai=time(8, 0), selesai=time(11, 30)
    )
    c = Client()
    r = c.get("/anjangsana/")
    isi = r.content.decode()
    assert r.status_code == 200 and "Anjangsana sedang tidak berlangsung." in isi and "Sesi berikutnya:" in isi
    p = buat_peserta(kontingen_madya)
    status, j = api(c, "kartu", {"teks": "SJP:" + p.qr_token})
    assert status == 403 and j["kode"] == "TIDAK_BERLANGSUNG"


def test_alur_lengkap_dan_konfirmasi(buka, kontingen_madya, kontingen_wira):
    p = buat_peserta(kontingen_madya, "BUDI SANTOSO")
    c = Client()
    assert c.get("/anjangsana/").status_code == 200
    _, j = api(c, "kartu", {"teks": "SJP:" + p.qr_token})
    assert j["nama"] == "BUDI SANTOSO" and j["kontingen"] == "SMP Negeri Uji"
    assert "nik" not in json.dumps(j).lower()
    # Kartu sendiri dipindai di langkah tuan rumah -> ditolak.
    _, salah = api(c, "tuan-rumah", {"tiket": j["tiket"], "teks": "SJP:" + p.qr_token})
    assert salah["kode"] == "BUKAN_QR_KONTINGEN"
    # QR kontingen sendiri -> ditolak.
    _, sendiri = api(c, "tuan-rumah", {"tiket": j["tiket"], "teks": "SJK:" + kontingen_madya.qr_token})
    assert sendiri["pesan"] == "Anda tidak bisa mengunjungi kontingen sendiri."
    # Antartingkat boleh (Madya mengunjungi Wira).
    status, j3 = kunjungi(c, p, kontingen_wira, (5, 4, 3), "Tendanya rapi  sekali")
    assert status == 200 and j3["ok"] and not j3["diganti"]
    r = Review.objects.get()
    assert (r.nilai_pengetahuan, r.nilai_keterampilan, r.nilai_sikap, r.komentar) == (5, 4, 3, "Tendanya rapi sekali")
    assert Kunjungan.objects.count() == 1
    assert LogAktivitas.objects.filter(aksi="anjangsana.review").exists()


def test_pindai_kartu_galat(buka, kontingen_madya):
    c = Client()
    _, j = api(c, "kartu", {"teks": "SJK:" + kontingen_madya.qr_token})
    assert j["pesan"] == "Ini QR kontingen. Pindai kartu peserta Anda dulu."
    _, j = api(c, "kartu", {"teks": "SJP:" + "A" * 26})
    assert j["kode"] == "KARTU_TIDAK_DIKENAL"
    p = buat_peserta(kontingen_madya)
    Peserta.objects.filter(pk=p.pk).update(kartu_aktif=False)
    _, j = api(c, "kartu", {"teks": "SJP:" + p.qr_token})
    assert j["kode"] == "KARTU_NONAKTIF"
    q = buat_peserta(kontingen_madya, "CITRA")
    _, j = api(c, "kartu", {"teks": q.kode_kartu.lower()})  # kode manual, huruf kecil
    assert j["ok"] and j["nama"] == "CITRA"


def test_tiket_dipalsukan_ditolak(buka, kontingen_madya, kontingen_wira):
    c = Client()
    status, j = api(c, "tuan-rumah", {"tiket": "palsu", "teks": "SJK:" + kontingen_wira.qr_token})
    assert status == 400 and j["kode"] == "TIKET_SALAH"
    status, j = api(c, "kunjungan", {"tiket_tuan": "x"})
    assert j["kode"] == "TIKET_SALAH"
    status, j = api(c, "review", {"tiket_kunjungan": "x", "nilai": {}})
    assert j["kode"] == "TIKET_SALAH"


def test_satu_review_per_kontingen_tamu_diganti(buka, kontingen_madya, kontingen_wira):
    a, b = buat_peserta(kontingen_madya, "A"), buat_peserta(kontingen_madya, "B")
    c = Client()
    kunjungi(c, a, kontingen_wira, (2, 2, 2))
    # Anggota lain dari kontingen yang sama: peringatan muncul sebelum form review.
    _, j = api(c, "kartu", {"teks": "SJP:" + b.qr_token})
    _, j2 = api(c, "tuan-rumah", {"tiket": j["tiket"], "teks": "SJK:" + kontingen_wira.qr_token})
    assert j2["peringatan"].startswith("Kontingen Anda sudah memberi review ke Kontingen SMA Negeri Uji pada ")
    assert j2["peringatan"].endswith("Jika Anda lanjut, review sebelumnya akan diganti.")
    _, j3 = api(c, "kunjungan", {"tiket_tuan": j2["tiket_tuan"]})
    n = {"pengetahuan": 5, "keterampilan": 5, "sikap": 5}
    status, tanpa_ganti = api(c, "review", {"tiket_kunjungan": j3["tiket_kunjungan"], "nilai": n, "ganti": False})
    assert status == 409 and tanpa_ganti["kode"] == "SUDAH_ADA"
    status, hasil = api(c, "review", {"tiket_kunjungan": j3["tiket_kunjungan"], "nilai": n, "ganti": True})
    assert hasil["diganti"]
    r = Review.objects.get()
    assert r.nilai_sikap == 5 and r.pengunjung == b and len(r.riwayat) == 1 and r.riwayat[0]["sikap"] == 2
    assert Kunjungan.objects.count() == 2  # kunjungan tetap tercatat sebagai kunjungan baru


def test_nilai_di_luar_rentang_ditolak(buka, kontingen_madya, kontingen_wira):
    p = buat_peserta(kontingen_madya)
    c = Client()
    for nilai in [(0, 3, 3), (6, 3, 3)]:
        status, j = kunjungi(c, p, kontingen_wira, nilai)
        assert status == 400 and j["kode"] == "NILAI_SALAH"
    _, j = api(c, "kartu", {"teks": "SJP:" + p.qr_token})
    _, j2 = api(c, "tuan-rumah", {"tiket": j["tiket"], "teks": "SJK:" + kontingen_wira.qr_token})
    _, j3 = api(c, "kunjungan", {"tiket_tuan": j2["tiket_tuan"]})
    status, j4 = api(c, "review", {"tiket_kunjungan": j3["tiket_kunjungan"], "nilai": {"pengetahuan": "x"}})
    assert j4["kode"] == "NILAI_SALAH"
    assert not Review.objects.exists()


def test_batas_kunjungan_per_kartu(buka, kontingen_madya, kontingen_wira, monkeypatch):
    monkeypatch.setattr(svc, "BATAS_KUNJUNGAN_PER_JAM", 2)
    p = buat_peserta(kontingen_madya)
    c = Client()
    _, j = api(c, "kartu", {"teks": "SJP:" + p.qr_token})
    _, j2 = api(c, "tuan-rumah", {"tiket": j["tiket"], "teks": "SJK:" + kontingen_wira.qr_token})
    assert api(c, "kunjungan", {"tiket_tuan": j2["tiket_tuan"]})[1]["ok"]
    assert api(c, "kunjungan", {"tiket_tuan": j2["tiket_tuan"]})[1]["ok"]
    status, j3 = api(c, "kunjungan", {"tiket_tuan": j2["tiket_tuan"]})
    assert status == 429 and j3["kode"] == "TERLALU_SERING"


def test_peringkat_dan_seri(buka, kontingen_madya, kontingen_wira, kontingen_mula):
    wira2 = Kontingen.objects.create(kode="WI-02", nama="SMA Dua", tingkat="WIRA", kuota=30)
    c = Client()
    m1, m2 = buat_peserta(kontingen_madya, "M"), buat_peserta(kontingen_mula, "U")
    kunjungi(c, m1, kontingen_wira, (4, 4, 4))
    kunjungi(c, m1, wira2, (4, 4, 4))
    kunjungi(c, m2, wira2, (4, 4, 4))  # sama rata-rata, tetapi WI-02 dikunjungi 2 kontingen berbeda
    hasil = svc.peringkat("WIRA")
    assert [h["k"].kode for h in hasil] == ["WI-02", "WI-01"]
    assert [h["peringkat"] for h in hasil] == [1, 2]
    assert hasil[0]["rata_rata"] == 4.0 and hasil[0]["tamu_berbeda"] == 2
    gabungan = svc.peringkat()
    assert len(gabungan) == 4 and gabungan[-1]["rata_rata"] == 0.0


def test_halaman_kelola_dan_hapus_review(buka, klien_superadmin, panitia, juri, kontingen_madya, kontingen_wira):
    p = buat_peserta(kontingen_madya)
    kunjungi(Client(), p, kontingen_wira, (3, 3, 3), "iseng")
    c = Client()
    masuk(c, "panitia")
    for url in ["/rekap/anjangsana/", "/rekap/anjangsana/?tingkat=WIRA", "/rekap/anjangsana/kunjungan/",
                f"/rekap/anjangsana/review/?k={kontingen_wira.pk}&arah=tuan"]:  # fmt: skip
        r = c.get(url)
        assert r.status_code == 200, url
        assert p.nik_samar not in r.content.decode()
    assert "iseng" in c.get("/rekap/anjangsana/review/").content.decode()
    r = c.get("/rekap/anjangsana/?unduh=xlsx")
    wb = openpyxl.load_workbook(io.BytesIO(r.content))
    assert "SMA Negeri Uji" in str(list(wb.active.iter_rows(values_only=True)))
    for url in ["/rekap/anjangsana/kunjungan/?unduh=xlsx", "/rekap/anjangsana/review/?unduh=xlsx"]:
        assert c.get(url)["Content-Type"].startswith("application/vnd.openxmlformats")
    # Panitia tidak boleh menghapus review, juri tidak boleh melihat.
    review = Review.objects.get()
    assert c.post(f"/rekap/anjangsana/review/{review.pk}/hapus/").status_code == 403
    j = Client()
    masuk(j, "juri")
    assert j.get("/rekap/anjangsana/").status_code == 403
    assert klien_superadmin.post(f"/rekap/anjangsana/review/{review.pk}/hapus/").status_code == 302
    assert not Review.objects.exists() and Review.semua.count() == 1
    assert LogAktivitas.objects.filter(aksi="anjangsana.review_dihapus").exists()
    assert svc.peringkat("WIRA")[0]["jumlah_review"] == 0
    # Setelah review iseng dihapus, kontingen tamu bisa memberi review baru.
    status, j2 = kunjungi(Client(), p, kontingen_wira, (5, 5, 5))
    assert j2["ok"] and not j2["diganti"]


def test_superadmin_sesi_status_poster(klien_superadmin):
    c = klien_superadmin
    assert c.get("/superadmin/anjangsana/").status_code == 200
    c.post("/superadmin/anjangsana/", {"aksi": "tambah", "tanggal": "2026-11-13", "mulai": "08:00", "selesai": "11:30"})
    s = SesiAnjangsana.objects.get()
    # Bertumpuk dan jam terbalik ditolak.
    c.post("/superadmin/anjangsana/", {"aksi": "tambah", "tanggal": "2026-11-13", "mulai": "11:00", "selesai": "12:00"})
    c.post("/superadmin/anjangsana/", {"aksi": "tambah", "tanggal": "2026-11-14", "mulai": "12:00", "selesai": "11:00"})
    assert SesiAnjangsana.objects.count() == 1
    c.post(
        "/superadmin/anjangsana/",
        {"aksi": "ubah", "pk": s.pk, "tanggal": "2026-11-13", "mulai": "08:30", "selesai": "11:30"},
    )
    s.refresh_from_db()
    assert s.mulai == time(8, 30)
    c.post("/superadmin/anjangsana/", {"aksi": "status", "paksa": "BUKA"})
    assert pengaturan.ambil("anjangsana.paksa_status") == "BUKA"
    c.post("/superadmin/anjangsana/", {"aksi": "status", "paksa": "NGAWUR"})
    assert pengaturan.ambil("anjangsana.paksa_status") == "BUKA"
    r = c.get("/superadmin/anjangsana/poster.pdf")
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    c.post("/superadmin/anjangsana/", {"aksi": "hapus", "pk": s.pk})
    assert not SesiAnjangsana.objects.exists()
    aksi = set(LogAktivitas.objects.values_list("aksi", flat=True))
    assert {
        "anjangsana.sesi_ditambah",
        "anjangsana.sesi_diubah",
        "anjangsana.status_diubah",
        "anjangsana.sesi_dihapus",
    } <= aksi


def test_panitia_tidak_bisa_kelola_sesi(panitia):
    c = Client()
    masuk(c, "panitia")
    assert c.get("/superadmin/anjangsana/").status_code == 403
