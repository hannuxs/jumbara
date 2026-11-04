"""Tes R15: poin daftar ulang (tepat waktu 1, telat 0,5) dengan waktu tiba kontingen agar antrean tidak merugikan."""

from __future__ import annotations

import uuid
from datetime import datetime, time, timedelta

import pytest
from django.utils import timezone

from apps.absensi import daftar_ulang as du
from apps.absensi import rekap, services
from apps.absensi.models import KedatanganKontingen, Kegiatan, Kehadiran, StatusTitik, SumberKedatangan
from apps.inti import pengaturan
from apps.inti.models import LogAktivitas
from apps.kontingen.models import Kontingen

from .test_absensi import buat_peserta, buat_titik

# Titik kemarin, agar jam pindaian (yang tidak boleh di masa depan) bisa diatur bebas.
KEMARIN = timezone.localdate() - timedelta(days=1)


def jam(j: int, m: int = 0) -> str:
    return timezone.make_aware(datetime.combine(KEMARIN, time(j, m))).isoformat()


@pytest.fixture
def titik_du(db):
    kg = Kegiatan.objects.create(kode="daftar-ulang", nama="Daftar Ulang", kelompok="ADMINISTRASI")
    return buat_titik(kode="TA-001", tingkat="SEMUA", kegiatan=kg, tanggal=KEMARIN, mulai=time(8), selesai=time(12),
                      status=StatusTitik.BUKA, nama_tampil="Daftar Ulang")  # fmt: skip


def pindai(user, titik, qr, pada, **ubah):
    data = {"client_uuid": str(ubah.pop("cu", uuid.uuid4())), "titik_absen_id": titik.pk, "qr": qr,
            "nama_pemindai": "Rina", "perangkat_id": "hp-1", "dipindai_pada": pada, **ubah}  # fmt: skip
    return services.pindai(user, data)


def test_antrean_tidak_merugikan_kontingen_yang_tiba_tepat_waktu(panitia, kontingen_madya, kontingen_wira, titik_du):
    a = [buat_peserta(kontingen_madya, nama=f"ANGGOTA A{i}") for i in range(3)]
    b = buat_peserta(kontingen_wira, nama="ANGGOTA B")
    # Kontingen A tiba 11.50 (QR kontingen dipindai di ujung antrean).
    h = pindai(panitia, titik_du, "SJK:" + kontingen_madya.qr_token, jam(11, 50))
    assert h.status == "HIJAU" and h.kode == "KONTINGEN_TIBA" and h.extra["kontingen_tiba"]["kode"] == "MA-01"
    assert pindai(panitia, titik_du, "SJK:" + kontingen_madya.qr_token, jam(11, 55)).kode == "KONTINGEN_SUDAH_TIBA"
    pindai(panitia, titik_du, "SJP:" + a[0].qr_token, jam(11, 55))  # sebelum batas
    h = pindai(panitia, titik_du, "SJP:" + a[1].qr_token, jam(12, 40))  # tertahan antrean: tetap tepat
    assert "tepat waktu" in h.info_bentrok
    h = pindai(panitia, titik_du, "SJP:" + a[2].qr_token, jam(14, 30))  # datang sendiri jauh setelah rombongan
    assert "telat" in h.info_bentrok
    # Kontingen B tanpa QR kontingen: kartu pertama 12.10 menjadi waktu tibanya -> telat.
    pindai(panitia, titik_du, "SJP:" + b.qr_token, jam(12, 10))
    tiba_b = KedatanganKontingen.objects.get(kontingen=kontingen_wira)
    assert tiba_b.sumber == SumberKedatangan.KARTU_PERTAMA
    r = du.ringkas_per_kontingen([titik_du])
    assert (r[kontingen_madya.pk].tepat, r[kontingen_madya.pk].telat, r[kontingen_madya.pk].poin) == (2, 1, 2.5)
    assert (r[kontingen_wira.pk].tepat, r[kontingen_wira.pk].telat, r[kontingen_wira.pk].poin) == (0, 1, 0.5)
    # Tabel poin kegiatan dan rekap kontingen memakai aturan yang sama.
    _, baris = rekap.tabel_poin_kegiatan(titik_du.kegiatan, "MADYA")
    assert next(x for x in baris if x.kontingen == kontingen_madya).total == 2.5


def test_antrean_offline_dengan_jam_lebih_awal_memperbarui_waktu_tiba(panitia, kontingen_madya, titik_du):
    p1, p2 = buat_peserta(kontingen_madya), buat_peserta(kontingen_madya, nama="SRI")
    pindai(panitia, titik_du, "SJP:" + p1.qr_token, jam(12, 20))
    pindai(panitia, titik_du, "SJP:" + p2.qr_token, jam(11, 40), offline=True)  # terkirim belakangan
    tiba = KedatanganKontingen.objects.get(kontingen=kontingen_madya)
    assert timezone.localtime(tiba.tiba_pada).time() == time(11, 40)
    r = du.ringkas_per_kontingen([titik_du])[kontingen_madya.pk]
    assert (r.tepat, r.telat) == (2, 0)  # yang 12.20 kini tepat karena kontingennya tiba 11.40


def test_kiriman_ulang_qr_kontingen_idempoten(panitia, kontingen_madya, titik_du):
    cu = uuid.uuid4()
    h1 = pindai(panitia, titik_du, "SJK:" + kontingen_madya.qr_token, jam(9), cu=cu)
    h2 = pindai(panitia, titik_du, "SJK:" + kontingen_madya.qr_token, jam(9), cu=cu)
    assert h1.kode == h2.kode == "KONTINGEN_TIBA" and KedatanganKontingen.objects.count() == 1


def test_qr_kontingen_di_titik_lain_tetap_ditolak(panitia, kontingen_madya):
    t = buat_titik(kode="TA-950", tingkat="SEMUA")
    assert pindai(panitia, t, "SJK:" + kontingen_madya.qr_token, jam(9)).kode == "BUKAN_KARTU_PESERTA"


def test_daftar_ulang_terbuka_sampai_malam_untuk_yang_telat(titik_du):
    titik_du.status = StatusTitik.OTOMATIS
    malam = timezone.make_aware(datetime.combine(KEMARIN, time(21)))
    assert services.titik_terbuka(titik_du, malam)
    pengaturan.simpan("daftar_ulang.terbuka_sampai_malam", False)
    assert not services.titik_terbuka(titik_du, malam)


def test_batas_poin_dan_toleransi_bisa_diatur(panitia, kontingen_madya, titik_du):
    p = buat_peserta(kontingen_madya)
    pindai(panitia, titik_du, "SJP:" + p.qr_token, jam(10, 30))
    pengaturan.simpan("daftar_ulang.batas_tepat", "10:00")
    pengaturan.simpan("daftar_ulang.poin_telat", 0.25)
    r = du.ringkas_per_kontingen([titik_du])[kontingen_madya.pk]
    assert (r.tepat, r.telat, r.poin) == (0, 1, 0.25)


def test_superadmin_koreksi_per_orang_dan_waktu_tiba(klien_superadmin, panitia, kontingen_madya, kontingen_wira,
                                                     titik_du):  # fmt: skip
    p = buat_peserta(kontingen_wira, nama="BUDI")
    pindai(panitia, titik_du, "SJP:" + p.qr_token, jam(12, 30))  # telat
    k = Kehadiran.objects.get(peserta=p)
    url = f"/superadmin/absensi/kehadiran/{k.pk}/waktu/"
    klien_superadmin.post(url, {"status": "TEPAT"})  # tanpa alasan: ditolak
    k.refresh_from_db()
    assert k.tepat_waktu_manual is None
    klien_superadmin.post(url, {"status": "TEPAT", "alasan": "Bus mogok, lapor ke sekretariat 11.30"})
    k.refresh_from_db()
    assert k.tepat_waktu_manual is True and du.ringkas_per_kontingen([titik_du])[kontingen_wira.pk].poin == 1
    assert LogAktivitas.objects.filter(aksi="kehadiran.waktu_dikoreksi").exists()
    klien_superadmin.post(url, {"status": "OTOMATIS"})
    # Waktu tiba diisi manual 11.45: kini tepat karena masih dalam toleransi antrean.
    r = klien_superadmin.post(f"/superadmin/absensi/titik/{titik_du.pk}/kedatangan/",
                              {"kontingen": kontingen_wira.pk, "jam": "11.45"})  # fmt: skip
    assert r.status_code == 302
    tiba = KedatanganKontingen.objects.get(kontingen=kontingen_wira)
    assert tiba.sumber == SumberKedatangan.MANUAL and timezone.localtime(tiba.tiba_pada).time() == time(11, 45)
    assert du.ringkas_per_kontingen([titik_du])[kontingen_wira.pk].tepat == 1
    halaman = klien_superadmin.get(f"/superadmin/absensi/titik/{titik_du.pk}/").content.decode()
    assert "Kedatangan kontingen" in halaman and "tepat waktu" in halaman
    klien_superadmin.post(f"/superadmin/absensi/titik/{titik_du.pk}/kedatangan/", {"kontingen": kontingen_wira.pk,
                                                                                  "hapus": "1"})  # fmt: skip
    assert not KedatanganKontingen.objects.filter(kontingen=kontingen_wira).exists()


def test_halaman_rekap_daftar_ulang_menampilkan_poin(klien_superadmin, panitia, kontingen_madya, titik_du):
    pindai(panitia, titik_du, "SJP:" + buat_peserta(kontingen_madya).qr_token, jam(9))
    isi = klien_superadmin.get("/rekap/daftar-ulang/").content.decode()
    assert "Kontingen tiba" in isi and "Batas tepat waktu 12.00" in isi
    assert klien_superadmin.get("/rekap/daftar-ulang/", {"unduh": "xlsx"}).status_code == 200
    assert klien_superadmin.get(f"/rekap/kegiatan/{titik_du.kegiatan_id}/", {"tingkat": "MADYA"}).status_code == 200
    assert klien_superadmin.get(f"/rekap/kontingen/{kontingen_madya.pk}/").status_code == 200
    assert Kontingen.objects.count() >= 1
