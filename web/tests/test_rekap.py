"""Tes poin kehadiran dan rekap (docs/15-REKAP-POIN.md)."""

from __future__ import annotations

from datetime import date, time

import openpyxl
import pytest
from django.test import Client

from apps.absensi import rekap
from apps.absensi.models import Kegiatan, KuotaKegiatan
from apps.inti import pengaturan
from apps.inti.models import LogAktivitas

from .conftest import masuk
from .test_absensi import buat_peserta, buat_titik, kirim


@pytest.mark.parametrize(
    "hadir,kuota,batasi,poin",
    [(7, 8, True, 6), (8, 8, True, 8), (9, 8, True, 8), (9, 8, False, 9), (0, 3, True, -3), (4, None, True, 4)],
)
def test_rumus_poin_sesi(hadir, kuota, batasi, poin):
    p = rekap.hitung_poin_sesi(hadir, kuota, batasi)
    assert p.poin == poin
    assert p.lebih == (kuota is not None and hadir > kuota)
    assert p.kuota_kosong == (kuota is None)


@pytest.fixture
def traveling(db):
    return Kegiatan.objects.create(
        kode="traveling", nama="Traveling Kepalangmerahan", kelompok="JUMPA", kuota_default=8
    )


def isi_hadir(panitia, titik, orang):
    for p in orang:
        assert kirim(panitia, titik, "SJP:" + p.qr_token).status == "HIJAU"


def test_poin_multi_sesi_dijumlah(panitia, kontingen_madya, traveling):
    orang = [buat_peserta(kontingen_madya, f"ORANG {i}") for i in range(9)]
    jumat = buat_titik("TA-J", tingkat="MADYA", kegiatan=traveling, tanggal=date(2026, 11, 13), status="BUKA")
    sabtu = buat_titik("TA-S", tingkat="MADYA", kegiatan=traveling, tanggal=date(2026, 11, 14), status="BUKA")
    isi_hadir(panitia, jumat, orang[:7])
    isi_hadir(panitia, sabtu, orang[:9])  # 9 hadir, kuota 8: tetap 8
    titik, baris = rekap.tabel_poin_kegiatan(traveling, "MADYA")
    assert [t.kode for t in titik] == ["TA-J", "TA-S"]
    b = baris[0]
    assert [p.poin for _, p in b.sesi] == [6, 8] and b.total == 14 and b.total_hadir == 16
    assert rekap.poin_kehadiran("traveling", kontingen_madya) == {"poin_kehadiran": 14, "jumlah_hadir": 16, "kuota": 8}
    pengaturan.simpan("poin.batasi_ke_kuota", False)
    assert rekap.poin_kehadiran("traveling", kontingen_madya)["poin_kehadiran"] == 15


def test_kuota_khusus_kontingen_dan_tingkat_lain(panitia, kontingen_madya, kontingen_wira, traveling):
    KuotaKegiatan.objects.create(kegiatan=traveling, kontingen=kontingen_madya, kuota=5)
    t_madya = buat_titik("TA-1", tingkat="MADYA", kegiatan=traveling, status="BUKA")
    buat_titik("TA-2", tingkat="WIRA", kegiatan=traveling, status="BUKA")
    buat_titik("TA-3", tingkat="MADYA", kegiatan=traveling, status="BUKA", hitung_poin=False)
    isi_hadir(panitia, t_madya, [buat_peserta(kontingen_madya, f"O {i}") for i in range(4)])
    hasil = rekap.poin_kehadiran("traveling", kontingen_madya)
    assert hasil == {
        "poin_kehadiran": 3,
        "jumlah_hadir": 4,
        "kuota": 5,
    }  # 4 - 1; titik Wira dan tanpa-poin tidak dihitung
    assert rekap.poin_kehadiran("traveling", kontingen_wira)["poin_kehadiran"] == -8  # titik Wira, tidak ada yang hadir


def test_kegiatan_tanpa_kuota_dan_tidak_ada(panitia, kontingen_madya):
    drama = Kegiatan.objects.create(kode="drama", nama="Drama", kelompok="GEMBIRA", kuota_default=None)
    t = buat_titik("TA-D", kegiatan=drama, status="BUKA")
    isi_hadir(panitia, t, [buat_peserta(kontingen_madya, "A"), buat_peserta(kontingen_madya, "B")])
    _, baris = rekap.tabel_poin_kegiatan(drama, "MADYA")
    assert baris[0].total == 2 and baris[0].ada_kuota_kosong
    assert rekap.poin_kehadiran("tidak-ada", kontingen_madya)["poin_kehadiran"] == 0


def test_daftar_ulang(panitia, kontingen_madya, kontingen_wira):
    du = Kegiatan.objects.create(kode="daftar-ulang", nama="Daftar Ulang", kelompok="ADMINISTRASI")
    t = buat_titik("TA-001", tingkat="SEMUA", kegiatan=du, status="BUKA", hitung_poin=False)
    a, _b = buat_peserta(kontingen_madya, "A"), buat_peserta(kontingen_madya, "B")
    buat_peserta(kontingen_wira, "W")
    isi_hadir(panitia, t, [a])
    data = {d["k"].kode: d for d in rekap.rekap_daftar_ulang()}
    assert (data["MA-01"]["sudah"], data["MA-01"]["belum"]) == (1, 1)
    assert (data["WI-01"]["sudah"], data["WI-01"]["belum"]) == (0, 1)
    du_k = rekap.daftar_ulang_kontingen(kontingen_madya)
    assert [p.nama_lengkap for p in du_k["belum"]] == ["B"]


def test_halaman_rekap_dan_excel(panitia, juri, kontingen_madya, traveling):
    t = buat_titik(
        "TA-J", tingkat="MADYA", kegiatan=traveling, tanggal=date(2026, 11, 13), mulai=time(8, 0), status="BUKA"
    )
    p = buat_peserta(kontingen_madya)
    isi_hadir(panitia, t, [p])
    c = Client()
    masuk(c, "panitia")
    halaman = [
        "/rekap/?tingkat=MADYA", f"/rekap/titik/{t.pk}/", "/rekap/kegiatan/", f"/rekap/kegiatan/{traveling.pk}/?tingkat=MADYA",
        "/rekap/kontingen/", f"/rekap/kontingen/{kontingen_madya.pk}/", "/rekap/orang/?q=ani", f"/rekap/orang/{p.pk}/",
        "/rekap/harian/?tanggal=2026-11-13", "/rekap/daftar-ulang/",
    ]  # fmt: skip
    for url in halaman:
        r = c.get(url)
        assert r.status_code == 200, url
        isi = r.content.decode()
        assert "NIK" not in isi and p.nik_samar not in isi  # tanpa data pribadi
    r = c.get(f"/rekap/kegiatan/{traveling.pk}/?tingkat=MADYA&unduh=xlsx")
    wb = openpyxl.load_workbook(__import__("io").BytesIO(r.content))
    teks = str([list(x) for x in wb.active.iter_rows(values_only=True)])
    assert "Poin kehadiran Traveling" in teks and "SMP Negeri Uji" in teks
    for url in ["/rekap/?tingkat=MADYA&unduh=xlsx", f"/rekap/titik/{t.pk}/?unduh=xlsx", f"/rekap/kontingen/{kontingen_madya.pk}/?unduh=xlsx",
                "/rekap/harian/?tanggal=2026-11-13&unduh=xlsx", "/rekap/daftar-ulang/?unduh=xlsx"]:  # fmt: skip
        assert c.get(url)["Content-Type"].startswith("application/vnd.openxmlformats"), url
    assert LogAktivitas.objects.filter(aksi="rekap.diunduh").count() == 6
    j = Client()
    masuk(j, "juri")
    assert j.get("/rekap/").status_code == 403


def test_kelola_kuota_kegiatan(klien_superadmin, kontingen_madya, traveling):
    r = klien_superadmin.post("/superadmin/absensi/kegiatan/", {f"kuota_{traveling.pk}": "7", "batasi": "1"})
    assert r.status_code == 302
    traveling.refresh_from_db()
    assert traveling.kuota_default == 7
    assert LogAktivitas.objects.filter(aksi="kegiatan.kuota_diubah").exists()
    klien_superadmin.post("/superadmin/absensi/kegiatan/", {f"kuota_{traveling.pk}": "7"})  # batasi dimatikan
    assert pengaturan.ambil("poin.batasi_ke_kuota") is False
    klien_superadmin.post("/superadmin/absensi/kegiatan/", {f"kuota_{traveling.pk}": "abc", "batasi": "1"})
    traveling.refresh_from_db()
    assert traveling.kuota_default == 7  # angka salah ditolak
    url = f"/superadmin/absensi/kegiatan/{traveling.pk}/kuota/"
    klien_superadmin.post(url, {f"k_{kontingen_madya.pk}": "3"})
    assert KuotaKegiatan.objects.get(kegiatan=traveling, kontingen=kontingen_madya).kuota == 3
    klien_superadmin.post(url, {f"k_{kontingen_madya.pk}": ""})
    assert not KuotaKegiatan.objects.exists()
    assert klien_superadmin.get(url).status_code == 200
