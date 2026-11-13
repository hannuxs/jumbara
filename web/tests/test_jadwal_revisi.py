"""Tes R16: migrasi jadwal revisi panitia aman untuk database produksi (tidak menghapus, kehadiran ikut, aman diulang)."""

from __future__ import annotations

import importlib
from datetime import date, time

from django.apps import apps as django_apps

from apps.absensi import jadwal
from apps.absensi.models import Kegiatan, Kehadiran, TitikAbsen

from .test_absensi import buat_peserta, buat_titik, kirim

mig = importlib.import_module("apps.absensi.migrations.0006_jadwal_revisi_panitia")
JUMAT, SABTU = date(2026, 11, 13), date(2026, 11, 14)


def _kg(kode, nama):
    return Kegiatan.objects.create(kode=kode, nama=nama, kelompok="JUMPA", kuota_default=3)


def test_jadwal_revisi_digeser_kehadiran_tetap_dan_aman_diulang(panitia, kontingen_madya):
    traveling, ranking, ngobrol = (_kg("traveling", "Traveling"), _kg("ranking-1", "Ranking 1"),
                                   _kg("ngobrol-bareng", "Ngobrol Bareng PMR"))  # fmt: skip
    _kg("sarasehan-pergaulan", "Sarasehan Menjaga Diri")
    tr = buat_titik(kode="TA-024", tingkat="MADYA", kegiatan=traveling, tanggal=JUMAT, selesai=None, status="BUKA",
                    nama_tampil="Traveling Kepalangmerahan Jumat Madya")  # fmt: skip
    rk = buat_titik(kode="TA-018", tingkat="MADYA", kegiatan=ranking, tanggal=JUMAT, selesai=None, status="BUKA",
                    nama_tampil="Ranking 1 Madya")  # fmt: skip
    ng = buat_titik(kode="TA-027", tingkat="MADYA", kegiatan=ngobrol, tanggal=JUMAT, mulai=time(14), selesai=time(17),
                    nama_tampil="Ngobrol Bareng PMR Madya")  # fmt: skip
    buat_titik(kode="TA-061", tingkat="SEMUA", nama_tampil="Titik lain yang sudah memakai kode TA-061")
    ani = buat_peserta(kontingen_madya)
    assert kirim(panitia, rk, "SJP:" + ani.qr_token).status == "HIJAU"  # kehadiran asli sebelum revisi
    jumlah = Kehadiran.objects.count()

    mig.terapkan(django_apps, None)
    mig.terapkan(django_apps, None)  # aman diulang (misalnya migrate dijalankan lagi)

    for t in (tr, rk, ng):
        t.refresh_from_db()
    assert (tr.tanggal, tr.mulai, tr.selesai) == (JUMAT, time(7, 30), time(18))
    assert (rk.tanggal, rk.mulai, rk.selesai) == (SABTU, time(8), None)
    assert (ng.tanggal, ng.mulai, ng.selesai) == (SABTU, time(8), time(12))
    assert Kehadiran.objects.count() == jumlah and Kehadiran.objects.get(peserta=ani).titik_absen == rk
    sampah = Kegiatan.objects.get(kode="sarasehan-sampah")
    titik = TitikAbsen.objects.filter(kegiatan=sampah).order_by("kode")
    assert sorted(t.tingkat for t in titik) == ["MADYA", "MULA", "WIRA"]
    assert "TA-061" not in {t.kode for t in titik}  # kode yang sudah dipakai dilewati
    assert all((t.tanggal, t.mulai, t.selesai) == (SABTU, time(8), time(12)) for t in titik)
    # Kegiatan baru bisa dipilih di biodata dan bentrok dengan Ngobrol Bareng (sama-sama Sabtu 08.00-12.00).
    pilihan = {p.kegiatan.kode: p for p in jadwal.pilihan("MADYA")}
    assert ngobrol.pk in pilihan["sarasehan-sampah"].bentrok


def test_titik_buatan_superadmin_di_hari_baru_tidak_ditimpa(db):
    _kg("traveling", "Traveling")
    ranking = _kg("ranking-1", "Ranking 1")
    lama = buat_titik(kode="TA-017", tingkat="MULA", kegiatan=ranking, tanggal=JUMAT, selesai=None)
    buat_titik(kode="TA-900", tingkat="MULA", kegiatan=ranking, tanggal=SABTU, selesai=None)  # dibuat superadmin
    mig.terapkan(django_apps, None)
    lama.refresh_from_db()
    assert lama.tanggal == JUMAT  # tidak digeser agar tidak ada dua titik Ranking 1 Mula di hari Sabtu


def test_database_kosong_dilewati(db):
    mig.terapkan(django_apps, None)
    assert not Kegiatan.objects.exists() and not TitikAbsen.objects.exists()
