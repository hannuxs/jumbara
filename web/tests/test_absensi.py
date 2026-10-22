"""Tes absensi: pindai, kunci unik, idempoten, pemindaian bersamaan, titik buka/tutup, API (docs/14-ABSENSI.md)."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, time, timedelta

import pytest
from django.db import close_old_connections
from django.test import Client
from django.utils import timezone

from apps.absensi import services
from apps.absensi.models import Kehadiran, PindaianDitolak, StatusTitik, TitikAbsen
from apps.biodata.models import Peserta
from apps.kartu import services as kartu_svc
from apps.kontingen.models import Kontingen

from .conftest import masuk

_nomor = iter(range(1, 10_000))


def buat_peserta(
    k: Kontingen, nama: str = "ANI LESTARI", tingkat: str | None = None, peran: str = "PESERTA"
) -> Peserta:
    n = next(_nomor)
    p = Peserta(
        kode_pendaftaran=f"SJ-T{n:05d}",
        kontingen=k,
        tingkat=tingkat or k.tingkat,
        peran=peran,
        nama_lengkap=nama,
        nik_terenkripsi="x",
        nik_hash=f"{n:064d}",
        nik_samar="6501********0001",
        nik_akhir4="0001",
        jenis_kelamin="P",
        tempat_lahir="Tanjung Selor",
        tanggal_lahir=datetime(2012, 1, 1).date(),
        alamat="Jl. Uji RT 01",
        golongan_darah="O",
    )
    kartu_svc.pasang_token(p)
    p.save()
    return p


def buat_titik(kode="TA-901", tingkat="MADYA", status=StatusTitik.BUKA, **ubah) -> TitikAbsen:
    data = {
        "kode": kode,
        "nama_tampil": f"Titik {kode}",
        "tingkat": tingkat,
        "tanggal": timezone.localdate(),
        "mulai": time(8, 0),
        "selesai": time(10, 0),
        "status": status,
    }
    data.update(ubah)
    return TitikAbsen.objects.create(**data)


def kirim(user, titik, qr, cu=None, **ubah):
    data = {
        "client_uuid": str(cu or uuid.uuid4()),
        "titik_absen_id": titik.pk,
        "qr": qr,
        "nama_pemindai": "Rina",
        "perangkat_id": "hp-1",
    }
    data.update(ubah)
    return services.pindai(user, data)


@pytest.fixture
def ani(kontingen_madya):
    return buat_peserta(kontingen_madya)


# --- Pindai --------------------------------------------------------------------------


def test_pindai_berhasil_lalu_sudah_tercatat(panitia, ani):
    t = buat_titik()
    h1 = kirim(panitia, t, "SJP:" + ani.qr_token)
    assert h1.status == "HIJAU" and h1.peserta["nama"] == "ANI LESTARI"
    assert set(h1.peserta) == {"id", "nama", "kontingen", "kode_kontingen", "tingkat", "peran"}  # tanpa data pribadi
    h2 = kirim(panitia, t, "SJP:" + ani.qr_token, nama_pemindai="Budi")
    assert h2.status == "KUNING" and h2.kode == "SUDAH_TERCATAT"
    assert h2.oleh == "Rina" and "oleh Rina" in h2.pesan
    assert Kehadiran.objects.count() == 1


def test_kiriman_ulang_client_uuid_sama_tidak_dobel(panitia, ani):
    t = buat_titik()
    cu = uuid.uuid4()
    h1 = kirim(panitia, t, "SJP:" + ani.qr_token, cu=cu)
    h2 = kirim(panitia, t, "SJP:" + ani.qr_token, cu=cu)
    assert h1.status == h2.status == "HIJAU"
    assert Kehadiran.objects.count() == 1


def test_pindai_dengan_kode_kartu(panitia, ani):
    t = buat_titik()
    assert kirim(panitia, t, ani.kode_kartu.lower()).status == "HIJAU"


@pytest.mark.parametrize(
    "kasus,kode",
    [("asing", "QR_ASING"), ("kontingen", "BUKAN_KARTU_PESERTA"), ("tak_dikenal", "KARTU_TIDAK_DIKENAL")],
)
def test_pindai_merah(panitia, ani, kontingen_madya, kasus, kode):
    t = buat_titik()
    qr = {
        "asing": "https://contoh.com",
        "kontingen": "SJK:" + kontingen_madya.qr_token,
        "tak_dikenal": "SJP:" + "Z" * 26,
    }[kasus]
    h = kirim(panitia, t, qr)
    assert h.status == "MERAH" and h.kode == kode
    assert PindaianDitolak.objects.filter(kode=kode).count() == 1
    assert not Kehadiran.objects.exists()


def test_tingkat_salah_merah(panitia, ani):
    t = buat_titik(tingkat="WIRA")
    h = kirim(panitia, t, "SJP:" + ani.qr_token)
    assert h.kode == "TINGKAT_BEDA" and "kartu ini Madya, titik absen ini Wira" in h.pesan


def test_titik_semua_tingkat_menerima_semua(panitia, ani):
    t = buat_titik(tingkat="SEMUA")
    assert kirim(panitia, t, "SJP:" + ani.qr_token).status == "HIJAU"


def test_kartu_lama_dan_nonaktif(panitia, superadmin, ani, rf):
    t = buat_titik()
    lama = ani.qr_token
    req = rf.post("/")
    req.user, req.nama_pelaku, req.perangkat_id = superadmin, "Farhan", ""
    kartu_svc.terbitkan_ulang(req, ani, "HILANG")
    h = kirim(panitia, t, "SJP:" + lama)
    assert h.kode == "KARTU_NONAKTIF" and "terbaru" in h.pesan
    ani.refresh_from_db()
    kartu_svc.atur_aktif(req, ani, False)
    assert kirim(panitia, t, "SJP:" + ani.qr_token).kode == "KARTU_NONAKTIF"


def test_titik_tutup_paksa(panitia, superadmin, ani):
    t = buat_titik(status=StatusTitik.TUTUP)
    assert kirim(panitia, t, "SJP:" + ani.qr_token).kode == "TITIK_TUTUP"
    assert kirim(superadmin, t, "SJP:" + ani.qr_token).status == "HIJAU"  # superadmin boleh


def test_jendela_otomatis(panitia, ani, kontingen_madya):
    sekarang = timezone.localtime()
    # Mulai 30 menit lagi: sudah terbuka (60 menit sebelum mulai).
    t1 = buat_titik("TA-A", status=StatusTitik.OTOMATIS, mulai=(sekarang + timedelta(minutes=30)).time(), selesai=None)
    assert services.titik_terbuka(t1)
    # Mulai 2 jam lagi: belum terbuka.
    if (sekarang + timedelta(hours=2)).date() == sekarang.date():
        t2 = buat_titik("TA-B", status=StatusTitik.OTOMATIS, mulai=(sekarang + timedelta(hours=2)).time(), selesai=None)
        assert not services.titik_terbuka(t2)
        assert kirim(panitia, t2, "SJP:" + ani.qr_token).kode == "TITIK_TUTUP"
    # Kemarin: tertutup, tetapi pindaian offline yang dipindai saat masih terbuka tetap diterima.
    kemarin = sekarang - timedelta(days=1)
    t3 = buat_titik("TA-C", status=StatusTitik.OTOMATIS, tanggal=kemarin.date(), mulai=time(0, 0), selesai=time(23, 0))
    assert not services.titik_terbuka(t3)
    dipindai = timezone.make_aware(datetime.combine(kemarin.date(), time(9, 0)))
    h = kirim(panitia, t3, "SJP:" + ani.qr_token, offline=True, dipindai_pada=dipindai.isoformat())
    assert h.status == "HIJAU"
    p2 = buat_peserta(kontingen_madya, "BUDI SANTOSO")
    assert kirim(panitia, t3, "SJP:" + p2.qr_token).kode == "TITIK_TUTUP"  # bukan offline


def test_absen_manual_dan_info_bentrok(panitia, ani):
    t1 = buat_titik("TA-1", mulai=time(8, 0), selesai=time(10, 0))
    t2 = buat_titik("TA-2", mulai=time(9, 0), selesai=time(11, 0))
    kirim(panitia, t1, "SJP:" + ani.qr_token)
    h = kirim(panitia, t2, "", metode="MANUAL", peserta_id=ani.pk)
    assert h.status == "HIJAU"
    assert "Juga tercatat di Titik TA-1" in h.info_bentrok
    assert Kehadiran.objects.get(titik_absen=t2).metode == "MANUAL"


def test_data_tidak_valid(panitia):
    t = buat_titik()
    with pytest.raises(services.DataTidakValid):
        services.pindai(panitia, {"client_uuid": "bukan-uuid", "titik_absen_id": t.pk, "nama_pemindai": "Rina"})
    with pytest.raises(services.DataTidakValid):
        services.pindai(panitia, {"client_uuid": str(uuid.uuid4()), "titik_absen_id": t.pk, "nama_pemindai": ""})


def test_jam_hp_aneh_diganti_jam_server(panitia, ani):
    t = buat_titik()
    kirim(panitia, t, "SJP:" + ani.qr_token, dipindai_pada="2030-01-01T08:00:00+08:00")
    k = Kehadiran.objects.get()
    assert abs((k.dipindai_pada - timezone.now()).total_seconds()) < 60


# --- Bersamaan (banyak HP) -------------------------------------------------------------


def _jalankan_bersamaan(fungsi, jumlah):
    hasil, galat = [], []
    mulai = threading.Barrier(jumlah)

    def kerja(i):
        try:
            mulai.wait()
            hasil.append(fungsi(i))
        except Exception as e:  # noqa: BLE001
            galat.append(e)
        finally:
            close_old_connections()

    utas = [threading.Thread(target=kerja, args=(i,)) for i in range(jumlah)]
    for u in utas:
        u.start()
    for u in utas:
        u.join()
    return hasil, galat


@pytest.mark.django_db(transaction=True)
def test_banyak_hp_kartu_sama_satu_baris(panitia, kontingen_madya):
    p = buat_peserta(kontingen_madya)
    t = buat_titik()
    hasil, galat = _jalankan_bersamaan(lambda i: kirim(panitia, t, "SJP:" + p.qr_token, nama_pemindai=f"HP{i}"), 20)
    assert not galat
    assert Kehadiran.objects.filter(titik_absen=t, peserta=p).count() == 1
    assert sorted(h.status for h in hasil) == ["HIJAU"] + ["KUNING"] * 19


@pytest.mark.django_db(transaction=True)
def test_kiriman_ulang_bersamaan_uuid_sama(panitia, kontingen_madya):
    p = buat_peserta(kontingen_madya)
    t = buat_titik()
    cu = uuid.uuid4()
    hasil, galat = _jalankan_bersamaan(lambda i: kirim(panitia, t, "SJP:" + p.qr_token, cu=cu), 10)
    assert not galat
    assert Kehadiran.objects.count() == 1
    assert {h.status for h in hasil} == {"HIJAU"}


@pytest.mark.django_db(transaction=True)
def test_banyak_titik_bersamaan(panitia, kontingen_madya):
    orang = [buat_peserta(kontingen_madya, f"ORANG {i}") for i in range(5)]
    titik = [buat_titik(f"TA-{i:03d}") for i in range(4)]
    tugas = [(t, o) for t in titik for o in orang] * 2  # setiap pasangan dipindai dua kali

    hasil, galat = _jalankan_bersamaan(lambda i: kirim(panitia, tugas[i][0], "SJP:" + tugas[i][1].qr_token), len(tugas))
    assert not galat
    assert Kehadiran.objects.count() == len(titik) * len(orang)
    assert sum(h.status == "HIJAU" for h in hasil) == len(titik) * len(orang)


# --- API -----------------------------------------------------------------------------------


def _api(client, url, data=None):
    if data is None:
        return client.get(url)
    return client.post(url, json.dumps(data), content_type="application/json")


def test_api_hak_akses(client, panitia, juri, ani):
    t = buat_titik()
    r = _api(client, "/api/pindai", {"titik_absen_id": t.pk})
    assert r.status_code == 401 and r.json()["galat"] == "BELUM_MASUK"
    masuk(client, "juri")
    assert _api(client, "/api/titik-absen/").status_code == 403


def test_api_wajib_csrf(panitia, ani):
    c = Client(enforce_csrf_checks=True)
    masuk_c = c.get("/masuk/")
    token = masuk_c.cookies["sigap_csrf"].value
    c.post("/masuk/", {"username": "panitia", "password": "SandiUji-12345", "csrfmiddlewaretoken": token})
    t = buat_titik()
    data = json.dumps(
        {"client_uuid": str(uuid.uuid4()), "titik_absen_id": t.pk, "qr": "SJP:" + ani.qr_token, "nama_pemindai": "Rina"}
    )
    assert c.post("/api/pindai", data, content_type="application/json").status_code == 403
    r = c.post("/api/pindai", data, content_type="application/json", HTTP_X_CSRFTOKEN=c.cookies["sigap_csrf"].value)
    assert r.status_code == 200 and r.json()["status"] == "HIJAU"


def test_api_pindai_dan_batch(client, panitia, ani, kontingen_madya):
    masuk(client, "panitia")
    t = buat_titik()
    r = _api(
        client,
        "/api/pindai",
        {
            "client_uuid": str(uuid.uuid4()),
            "titik_absen_id": t.pk,
            "qr": "SJP:" + ani.qr_token,
            "nama_pemindai": "Rina",
        },
    )
    assert r.json()["status"] == "HIJAU"
    p2 = buat_peserta(kontingen_madya, "BUDI")
    cu = str(uuid.uuid4())
    antrean = [
        {
            "client_uuid": cu,
            "titik_absen_id": t.pk,
            "qr": "SJP:" + p2.qr_token,
            "nama_pemindai": "Rina",
            "offline": True,
        },
        {
            "client_uuid": cu,
            "titik_absen_id": t.pk,
            "qr": "SJP:" + p2.qr_token,
            "nama_pemindai": "Rina",
            "offline": True,
        },
        {
            "client_uuid": str(uuid.uuid4()),
            "titik_absen_id": t.pk,
            "qr": "SJP:" + ani.qr_token,
            "nama_pemindai": "Rina",
        },
        {"client_uuid": "rusak", "titik_absen_id": t.pk, "nama_pemindai": "Rina"},
    ]
    hasil = _api(client, "/api/pindai/batch", {"pindaian": antrean}).json()["hasil"]
    assert [h["status"] for h in hasil] == ["HIJAU", "HIJAU", "KUNING", "GALAT"]
    assert hasil[0]["client_uuid"] == cu
    assert Kehadiran.objects.count() == 2
    terlalu = _api(client, "/api/pindai/batch", {"pindaian": antrean * 13})
    assert terlalu.status_code == 400


def test_api_daftar_ringkas_cari_ringan(client, panitia, ani, kontingen_wira):
    masuk(client, "panitia")
    t = buat_titik()
    buat_peserta(kontingen_wira, "ORANG WIRA")
    kirim(panitia, t, "SJP:" + ani.qr_token)
    d = _api(client, "/api/titik-absen/").json()
    item = next(x for x in d["titik"] if x["id"] == t.pk)
    assert item["hadir"] == 1 and item["kelompok"] == "BERLANGSUNG"
    r = _api(client, f"/api/titik-absen/{t.pk}/ringkas/").json()
    assert r["hadir"] == 1 and r["kontingen_hadir"] == 1 and r["kontingen_total"] == 1
    assert r["terakhir"][0]["oleh"] == "Rina"
    ringan = _api(client, f"/api/titik-absen/{t.pk}/peserta/").json()["peserta"]
    assert [x["nama"] for x in ringan] == ["ANI LESTARI"]  # hanya tingkat Madya
    teks = json.dumps(ringan)
    assert ani.qr_token not in teks and "nik" not in teks and "alamat" not in teks
    cari = _api(client, f"/api/cari-peserta/?q=lest&titik={t.pk}").json()["hasil"]
    assert cari[0]["sudah_hadir"] is True
    assert _api(client, f"/api/cari-peserta/?q={ani.kode_kartu}&titik={t.pk}").json()["hasil"][0]["id"] == ani.pk
    assert _api(client, f"/api/cari-peserta/?q=orang wira&titik={t.pk}").json()["hasil"] == []


def test_halaman_pemindai(client, panitia, juri):
    masuk(client, "panitia")
    isi = client.get("/panitia/").content.decode()
    assert "data-layar-status" in isi and "qr-scanner.umd.min.js" in isi and "pemindai.js" in isi
    c = Client()
    masuk(c, "juri")
    assert c.get("/panitia/").status_code == 403
