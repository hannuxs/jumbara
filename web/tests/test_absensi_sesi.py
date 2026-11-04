"""Tes R15: pemindai cukup memilih kegiatan (tingkat otomatis dari biodata), buka/tutup per kegiatan, dan
kegiatan satu sesi (Got Talent, Drama) dihitung sekali untuk semua hari dan tingkat."""

from __future__ import annotations

from datetime import time, timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.absensi import rekap
from apps.absensi.models import Kegiatan, Kehadiran, StatusTitik
from apps.inti.models import LogAktivitas
from apps.kontingen.models import Kontingen

from .conftest import masuk
from .test_absensi import buat_peserta, buat_titik, kirim


@pytest.fixture
def traveling(db):
    return Kegiatan.objects.create(
        kode="traveling", nama="Traveling Kepalangmerahan", kelompok="JUMPA", kuota_default=2
    )


@pytest.fixture
def sesi_traveling(traveling):
    """Traveling hari ini: satu titik per tingkat (seperti data jadwal)."""
    return {
        t: buat_titik(kode=f"TR-{t[:2]}", tingkat=t, kegiatan=traveling, nama_tampil=f"Traveling {t.title()}")
        for t in ("MULA", "MADYA", "WIRA")
    }


def test_pindai_lewat_kegiatan_masuk_ke_titik_sesuai_tingkat(panitia, kontingen_madya, kontingen_wira, sesi_traveling):
    ani = buat_peserta(kontingen_madya)
    budi = buat_peserta(kontingen_wira, nama="BUDI SANTOSO")
    wakil = sesi_traveling["MULA"]  # pemindai memilih "Traveling" (titik wakil), bukan tingkat
    assert kirim(panitia, wakil, "SJP:" + ani.qr_token).status == "HIJAU"
    assert kirim(panitia, wakil, "SJP:" + budi.qr_token).status == "HIJAU"
    assert Kehadiran.objects.get(peserta=ani).titik_absen == sesi_traveling["MADYA"]
    assert Kehadiran.objects.get(peserta=budi).titik_absen == sesi_traveling["WIRA"]
    # Pindai ulang lewat titik mana pun: kuning, tidak dobel.
    h = kirim(panitia, sesi_traveling["WIRA"], "SJP:" + ani.qr_token)
    assert h.status == "KUNING" and Kehadiran.objects.filter(peserta=ani).count() == 1


def test_tingkat_tanpa_titik_di_sesi_ditolak(panitia, kontingen_madya, traveling):
    wira_saja = buat_titik(kode="TR-WI", tingkat="WIRA", kegiatan=traveling)
    h = kirim(panitia, wira_saja, "SJP:" + buat_peserta(kontingen_madya).qr_token)
    assert h.kode == "TINGKAT_BEDA" and "hanya Wira" in h.pesan


def test_titik_tingkat_itu_tutup_ditolak(panitia, kontingen_madya, sesi_traveling):
    sesi_traveling["MADYA"].status = StatusTitik.TUTUP
    sesi_traveling["MADYA"].save()
    h = kirim(panitia, sesi_traveling["MULA"], "SJP:" + buat_peserta(kontingen_madya).qr_token)
    assert h.kode == "TITIK_TUTUP" and "Traveling Madya" in h.pesan


def test_kegiatan_lain_hari_lain_tidak_tercampur(panitia, kontingen_madya, traveling):
    kemarin = buat_titik(kode="TR-K", tingkat="MADYA", kegiatan=traveling,
                         tanggal=timezone.localdate() - timedelta(days=1))  # fmt: skip
    hari_ini = buat_titik(kode="TR-H", tingkat="MULA", kegiatan=traveling)
    h = kirim(panitia, hari_ini, "SJP:" + buat_peserta(kontingen_madya).qr_token)
    assert h.kode == "TINGKAT_BEDA" and not Kehadiran.objects.filter(titik_absen=kemarin).exists()


def test_api_daftar_sesi_dan_ringkas_gabungan(panitia, kontingen_madya, kontingen_wira, sesi_traveling):
    klien = Client()
    masuk(klien, "panitia")
    kirim(panitia, sesi_traveling["MULA"], "SJP:" + buat_peserta(kontingen_madya).qr_token)
    kirim(panitia, sesi_traveling["MULA"], "SJP:" + buat_peserta(kontingen_wira, nama="BUDI").qr_token)
    d = klien.get("/api/titik-absen/").json()
    sesi = [s for s in d["sesi"] if s["nama"] == "Traveling Kepalangmerahan"]
    assert len(sesi) == 1 and sesi[0]["hadir"] == 2 and sesi[0]["tingkat"] == "SEMUA"
    assert sorted(sesi[0]["tingkat_list"]) == ["MADYA", "MULA", "WIRA"]
    assert sesi[0]["id"] == min(t.pk for t in sesi_traveling.values())
    r = klien.get(f"/api/titik-absen/{sesi[0]['id']}/ringkas/").json()
    assert r["hadir"] == 2 and r["kontingen_hadir"] == 2 and r["kontingen_total"] == Kontingen.objects.count()
    # Cache nama dan cari manual mencakup semua tingkat sesi itu.
    cache = klien.get(f"/api/titik-absen/{sesi[0]['id']}/peserta/").json()["peserta"]
    assert {p["tingkat"] for p in cache} == {"MADYA", "WIRA"}
    cari = klien.get("/api/cari-peserta/", {"q": "BUDI", "titik": sesi[0]["id"]}).json()["hasil"]
    assert cari and cari[0]["sudah_hadir"]


def test_superadmin_buka_tutup_per_kegiatan(klien_superadmin, sesi_traveling):
    wakil = sesi_traveling["MULA"]
    halaman = klien_superadmin.get("/superadmin/absensi/titik/")
    assert halaman.status_code == 200 and "Per kegiatan" in halaman.content.decode()
    r = klien_superadmin.post(f"/superadmin/absensi/titik/{wakil.pk}/status-kegiatan/", {"status": "TUTUP"})
    assert r.status_code == 302
    for t in sesi_traveling.values():
        t.refresh_from_db()
        assert t.status == StatusTitik.TUTUP
    assert LogAktivitas.objects.filter(aksi="titik_absen.status").count() == 3
    assert klien_superadmin.get("/superadmin/absensi/titik/", {"tampil": "rinci"}).status_code == 200


# --- Kegiatan satu sesi (Got Talent, Drama) -----------------------------------------------------------


@pytest.fixture
def drama(db):
    return Kegiatan.objects.create(kode="drama", nama="Pentas Seni Drama", kelompok="GEMBIRA", kuota_default=2,
                                   satu_sesi=True)  # fmt: skip


def _malam(drama, hari: int):
    tgl = timezone.localdate() + timedelta(days=hari)
    return {
        t: buat_titik(
            kode=f"DR{hari}{t[:2]}",
            tingkat=t,
            kegiatan=drama,
            tanggal=tgl,
            mulai=time(20),
            selesai=time(23),
            nama_tampil=f"Drama malam {hari + 1} {t.title()}",
        )  # fmt: skip
        for t in ("MULA", "MADYA", "WIRA")
    }


def test_satu_sesi_dihitung_sekali_untuk_semua_hari(panitia, kontingen_madya, drama):
    m1, m2, m3 = _malam(drama, 0), _malam(drama, 1), _malam(drama, 2)
    ani, sri = buat_peserta(kontingen_madya), buat_peserta(kontingen_madya, nama="SRI")
    # Kontingen tampil di malam 2 saja; Ani juga menonton malam 3.
    for t in (m2["MADYA"], m3["MADYA"]):
        t.status = StatusTitik.BUKA
        t.save()
    assert kirim(panitia, m2["MULA"], "SJP:" + ani.qr_token).status == "HIJAU"
    assert kirim(panitia, m2["MULA"], "SJP:" + sri.qr_token).status == "HIJAU"
    h = kirim(panitia, m3["WIRA"], "SJP:" + ani.qr_token)
    assert h.status == "HIJAU" and "dihitung satu kali" in h.info_bentrok
    titik, baris = rekap.tabel_poin_kegiatan(drama, "MADYA")
    assert len(titik) == 1 and titik[0].pk is None  # satu kolom untuk semua malam
    b = next(x for x in baris if x.kontingen == kontingen_madya)
    p = b.sesi[0][1]
    # 2 orang berbeda (Ani tidak dihitung dua kali), kuota 2: tidak ada pengurangan untuk malam lain.
    assert (p.hadir, p.kuota, p.poin) == (2, 2, 2) and b.total == 2
    assert m1  # malam 1 tidak menambah sesi kosong
    # Rekap kontingen: satu baris Drama; halaman rekap kegiatan tampil.
    data = rekap.rekap_kontingen(kontingen_madya)
    drama_baris = [x for x in data["baris"] if x["titik"].kegiatan_id == drama.pk]
    assert len(drama_baris) == 1 and drama_baris[0]["p"].poin == 2


def test_rekap_kegiatan_satu_sesi_tampil(klien_superadmin, kontingen_madya, drama):
    _malam(drama, 0)
    r = klien_superadmin.get(f"/rekap/kegiatan/{drama.pk}/", {"tingkat": "MADYA"})
    assert r.status_code == 200 and "dihitung satu sesi" in r.content.decode()
    assert (
        klien_superadmin.get(f"/rekap/kegiatan/{drama.pk}/", {"tingkat": "MADYA", "unduh": "xlsx"}).status_code == 200
    )
    assert klien_superadmin.get(f"/rekap/kontingen/{kontingen_madya.pk}/").status_code == 200
