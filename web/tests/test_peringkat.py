"""Tes R15: rekap peringkat per tingkat memakai nama sekolah, urut poin terbanyak (seri = peringkat sama)."""

from __future__ import annotations

from django.test import Client

from apps.absensi import rekap
from apps.absensi.models import Kegiatan
from apps.kontingen.models import Kontingen

from .conftest import masuk
from .test_absensi import buat_peserta, buat_titik, kirim


def test_peringkat_urut_poin_terbanyak_dengan_nama_sekolah(panitia, klien_superadmin):
    kg = Kegiatan.objects.create(kode="traveling", nama="Traveling Kepalangmerahan", kelompok="JUMPA", kuota_default=2)
    t = buat_titik(kode="TR-1", tingkat="MADYA", kegiatan=kg)
    a = Kontingen.objects.create(kode="MA-01", nama="SMP Negeri Uji A", tingkat="MADYA", kuota=5)
    b = Kontingen.objects.create(kode="MA-02", nama="SMP Negeri Uji B", tingkat="MADYA", kuota=5)
    c = Kontingen.objects.create(kode="MA-03", nama="MTs Uji C", tingkat="MADYA", kuota=5)
    for k, n in ((a, 1), (b, 2), (c, 1)):
        for i in range(n):
            kirim(panitia, t, "SJP:" + buat_peserta(k, nama=f"ORANG {k.kode} {i}").qr_token)
    kegiatan, data = rekap.peringkat_tingkat("MADYA")
    assert kegiatan == [kg]
    # B: 2 hadir dari kuota 2 = 2; A dan C: 1 hadir 1 absen = 0 (seri, urut nama: MTs sebelum SMP).
    assert [(d["peringkat"], d["k"].nama, d["total"]) for d in data] == [
        (1, "SMP Negeri Uji B", 2), (2, "MTs Uji C", 0), (2, "SMP Negeri Uji A", 0),
    ]  # fmt: skip
    isi = klien_superadmin.get("/rekap/peringkat/", {"tingkat": "MADYA"}).content.decode()
    assert isi.index("SMP Negeri Uji B") < isi.index("MTs Uji C") < isi.index("SMP Negeri Uji A")
    assert klien_superadmin.get("/rekap/peringkat/", {"tingkat": "MADYA", "unduh": "xlsx"}).status_code == 200
    # Tabel poin per kegiatan juga urut poin terbanyak.
    isi = klien_superadmin.get(f"/rekap/kegiatan/{kg.pk}/", {"tingkat": "MADYA"}).content.decode()
    assert isi.index("SMP Negeri Uji B") < isi.index("SMP Negeri Uji A")
    j = Client()
    masuk(j, "panitia")
    assert j.get("/rekap/peringkat/").status_code == 200
