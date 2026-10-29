"""Tes pilihan kegiatan di form biodata: boleh lebih dari satu, tidak boleh bentrok jadwal, sesuai tingkat."""

from __future__ import annotations

import json
import re
from datetime import date, time

import pytest

from apps.absensi import jadwal
from apps.absensi.models import Kegiatan, TitikAbsen
from apps.biodata.models import Peserta
from apps.inti import pengaturan
from apps.inti.models import LogAktivitas

from .conftest import data_valid

URL = "/daftar/"
H13 = date(2026, 11, 13)
H14 = date(2026, 11, 14)


def kegiatan(kode: str, *sesi, bisa_dipilih: bool = True) -> Kegiatan:
    """sesi = (tanggal, mulai, selesai|None, tingkat)."""
    kg = Kegiatan.objects.create(kode=kode, nama=kode.title(), kelompok="JUMPA", bisa_dipilih=bisa_dipilih)
    for i, (tgl, mulai, selesai, tingkat) in enumerate(sesi):
        TitikAbsen.objects.create(
            kode=f"{kode[:12]}-{i}", kegiatan=kg, tingkat=tingkat, nama_tampil=kg.nama, tanggal=tgl,
            mulai=mulai, selesai=selesai,
        )  # fmt: skip
    return kg


@pytest.fixture
def jadwal_uji(db):
    """Potongan jadwal Jumbara V: pagi 13 Nov 08.00-selesai, sarasehan 08.00-11.30, sore 16-18, malam drama."""
    return {
        "traveling": kegiatan("traveling", (H13, time(8), None, "MADYA"), (H14, time(8), None, "MADYA")),
        "jurnalistik": kegiatan("jurnalistik", (H13, time(8), None, "SEMUA")),
        "sarasehan": kegiatan("sarasehan", (H13, time(8), time(11, 30), "MADYA")),
        "ngobrol": kegiatan("ngobrol", (H13, time(14), time(17), "MADYA")),
        "got-talent": kegiatan("got-talent", (H13, time(16), time(18), "SEMUA")),
        "drama": kegiatan("drama", (H13, time(20), time(23), "SEMUA")),
        "wira-saja": kegiatan("wira-saja", (H13, time(20), time(21), "WIRA")),
        "daftar-ulang": kegiatan("daftar-ulang", (H13, time(7), time(8), "SEMUA"), bisa_dipilih=False),
    }


def kirim(client, data):
    return client.post(URL, data)


def test_bentrok_dihitung_dari_titik_absen(jadwal_uji):
    pilihan = {p.kegiatan.kode: p for p in jadwal.pilihan("MADYA")}
    # Daftar ulang bukan pilihan; kegiatan khusus Wira tidak tampil untuk Madya.
    assert "daftar-ulang" not in pilihan and "wira-saja" not in pilihan
    kode = {p.kegiatan.pk: k for k, p in pilihan.items()}
    bentrok = {k: {kode[i] for i in p.bentrok} for k, p in pilihan.items()}
    # 08.00-selesai dianggap sampai 12.00, sehingga bentrok dengan sarasehan 08.00-11.30.
    assert bentrok["traveling"] == {"jurnalistik", "sarasehan"}
    # 14.00-17.00 bertumpuk dengan 16.00-18.00.
    assert bentrok["ngobrol"] == {"got-talent"}
    assert bentrok["drama"] == set()
    assert "Jumat 13 Nov 08.00-selesai" in pilihan["traveling"].jadwal


def test_jam_selesai_bawaan_bisa_diubah(jadwal_uji):
    pengaturan.simpan("kegiatan.selesai_bawaan", "08:30")
    pilihan = {p.kegiatan.kode: p for p in jadwal.pilihan("MADYA")}
    # Tetap bentrok dengan sarasehan (08.00-08.30 bertumpuk dengan 08.00-11.30), tidak dengan ngobrol.
    assert jadwal_uji["sarasehan"].pk in pilihan["traveling"].bentrok
    assert jadwal_uji["ngobrol"].pk not in pilihan["traveling"].bentrok


def test_bersentuhan_tidak_bentrok(db):
    a = kegiatan("a-kegiatan", (H13, time(8), time(10), "SEMUA"))
    b = kegiatan("b-kegiatan", (H13, time(10), time(12), "SEMUA"))
    assert jadwal.periksa("MADYA", [a, b]) == []


def test_pilih_beberapa_kegiatan_tanpa_bentrok_tersimpan(client, kontingen_madya, jadwal_uji):
    pilih = [jadwal_uji["traveling"].pk, jadwal_uji["ngobrol"].pk, jadwal_uji["drama"].pk]
    r = kirim(client, data_valid(kontingen_madya, kegiatan=[str(i) for i in pilih]))
    assert r.status_code == 302
    p = Peserta.objects.get()
    assert set(p.kegiatan.values_list("pk", flat=True)) == set(pilih)
    log = LogAktivitas.objects.get(aksi="biodata.dibuat")
    assert "Traveling" in str(log.data_baru) and "Drama" in str(log.data_baru)
    bukti = client.get(r["Location"])
    assert "Drama" in bukti.content.decode()


def test_kegiatan_boleh_kosong(client, kontingen_madya, jadwal_uji):
    assert kirim(client, data_valid(kontingen_madya)).status_code == 302
    assert Peserta.objects.get().kegiatan.count() == 0


def test_kegiatan_bentrok_ditolak(client, kontingen_madya, jadwal_uji):
    pilih = [str(jadwal_uji["traveling"].pk), str(jadwal_uji["sarasehan"].pk)]
    r = kirim(client, data_valid(kontingen_madya, kegiatan=pilih))
    assert r.status_code == 400
    assert "bentrok dengan" in r.context["form"].errors["kegiatan"][0]
    assert not Peserta.objects.exists()


def test_kegiatan_tingkat_lain_dan_bukan_pilihan_ditolak(client, kontingen_madya, jadwal_uji):
    r = kirim(client, data_valid(kontingen_madya, kegiatan=[str(jadwal_uji["wira-saja"].pk)]))
    assert "tidak tersedia untuk tingkat Madya" in r.context["form"].errors["kegiatan"][0]
    r = kirim(client, data_valid(kontingen_madya, kegiatan=[str(jadwal_uji["daftar-ulang"].pk)]))
    assert "kegiatan" in r.context["form"].errors
    r = kirim(client, data_valid(kontingen_madya, kegiatan=["99999"]))
    assert "kegiatan" in r.context["form"].errors
    assert not Peserta.objects.exists()


def test_form_publik_memuat_jadwal_kegiatan(client, jadwal_uji):
    isi = client.get(URL).content.decode()
    assert 'id="data-kegiatan"' in isi and "08.00-selesai" in isi
    assert 'name="kegiatan"' in isi and "Daftar-Ulang" not in isi


def test_superadmin_ubah_kegiatan_dan_saring(klien_superadmin, client, kontingen_madya, jadwal_uji):
    kirim(client, data_valid(kontingen_madya, kegiatan=[str(jadwal_uji["drama"].pk)]))
    p = Peserta.objects.get()
    halaman = klien_superadmin.get(f"/superadmin/biodata/{p.pk}/ubah/")
    assert halaman.status_code == 200 and "Kegiatan yang diikuti" in halaman.content.decode()
    data = data_valid(kontingen_madya, kegiatan=[str(jadwal_uji["ngobrol"].pk), str(jadwal_uji["got-talent"].pk)])
    for nama in ("persetujuan", "situs_web", "token", "foto"):
        data.pop(nama)
    r = klien_superadmin.post(f"/superadmin/biodata/{p.pk}/ubah/", data)
    assert r.status_code == 200 and "kegiatan" in r.context["form"].errors  # bentrok juga ditolak untuk superadmin
    data["kegiatan"] = [str(jadwal_uji["ngobrol"].pk)]
    r = klien_superadmin.post(f"/superadmin/biodata/{p.pk}/ubah/", data)
    assert r.status_code == 302
    assert list(p.kegiatan.values_list("kode", flat=True)) == ["ngobrol"]
    log = LogAktivitas.objects.filter(aksi="biodata.diubah").latest("pk")
    assert "Ngobrol" in str(log.data_baru)
    daftar = klien_superadmin.get("/superadmin/biodata/", {"kegiatan": jadwal_uji["ngobrol"].pk})
    assert daftar.context["jumlah"] == 1
    daftar = klien_superadmin.get("/superadmin/biodata/", {"kegiatan": "kosong"})
    assert daftar.context["jumlah"] == 0


def test_superadmin_atur_kegiatan_bisa_dipilih(klien_superadmin, jadwal_uji):
    drama = jadwal_uji["drama"]
    data = {f"pilih_{kg.pk}": "1" for kg in Kegiatan.objects.filter(bisa_dipilih=True).exclude(pk=drama.pk)}
    r = klien_superadmin.post("/superadmin/absensi/kegiatan/", data)
    assert r.status_code == 302
    drama.refresh_from_db()
    assert drama.bisa_dipilih is False
    assert LogAktivitas.objects.filter(aksi="kegiatan.diubah").exists()
    assert "drama" not in {p.kegiatan.kode for p in jadwal.pilihan("MADYA")}


# --- R14: bentrok yang ditetapkan panitia (Traveling dan Got Talent) ---------------------------------


def test_traveling_dan_got_talent_bentrok_setelah_ditandai(client, klien_superadmin, kontingen_madya, jadwal_uji):
    t, g = jadwal_uji["traveling"], jadwal_uji["got-talent"]
    # Jam titik absen tidak bertumpuk (08.00-selesai dianggap sampai 12.00), jadi belum bentrok.
    assert jadwal.periksa("MADYA", [t, g]) == []
    t.bentrok_dengan.add(g)
    pilihan = {p.kegiatan.kode: p for p in jadwal.pilihan("MADYA")}
    assert g.pk in pilihan["traveling"].bentrok and t.pk in pilihan["got-talent"].bentrok  # dua arah
    # Bentrok lain tidak berubah.
    assert jadwal_uji["ngobrol"].pk not in pilihan["traveling"].bentrok
    # Data untuk HP ikut memuat bentrok baru, sehingga kotak centang terkunci.
    isi = client.get(URL).content.decode()
    data_hp = json.loads(
        re.search(r'<script id="data-kegiatan" type="application/json">(.*?)</script>', isi, re.S).group(1)
    )
    travel_hp = next(x for x in data_hp["MADYA"] if x["id"] == t.pk)
    assert g.pk in travel_hp["bentrok"]
    # Form publik menolak.
    r = kirim(client, data_valid(kontingen_madya, kegiatan=[str(t.pk), str(g.pk)]))
    assert r.status_code == 400
    assert "berlangsung bersamaan" in r.context["form"].errors["kegiatan"][0]
    assert not Peserta.objects.exists()
    # Form superadmin juga menolak.
    data = data_valid(kontingen_madya, kegiatan=[str(t.pk), str(g.pk)])
    for nama in ("persetujuan", "situs_web", "token"):
        data.pop(nama)
    r = klien_superadmin.post("/superadmin/biodata/tambah/", data)
    assert r.status_code == 200 and "kegiatan" in r.context["form"].errors
    # Salah satu saja tetap boleh.
    assert (
        kirim(client, data_valid(kontingen_madya, kegiatan=[str(t.pk), str(jadwal_uji["drama"].pk)])).status_code == 302
    )


def test_biodata_lama_yang_bentrok_ditandai_untuk_superadmin(client, klien_superadmin, kontingen_madya, jadwal_uji):
    t, g = jadwal_uji["traveling"], jadwal_uji["got-talent"]
    kirim(client, data_valid(kontingen_madya, kegiatan=[str(t.pk), str(g.pk)]))  # sebelum aturan bentrok
    p = Peserta.objects.get()
    t.bentrok_dengan.add(g)
    assert list(jadwal.peserta_bentrok()) == [p.pk]
    assert "Lihat daftarnya" in klien_superadmin.get("/superadmin/").content.decode()
    assert klien_superadmin.get("/superadmin/biodata/", {"kegiatan": "bentrok"}).context["jumlah"] == 1
    assert "berlangsung bersamaan" in klien_superadmin.get(f"/superadmin/biodata/{p.pk}/").content.decode()
    p.kegiatan.remove(g)
    assert jadwal.peserta_bentrok() == {}
    assert "Lihat daftarnya" not in klien_superadmin.get("/superadmin/").content.decode()


def test_superadmin_atur_kegiatan_tidak_boleh_bersamaan(klien_superadmin, jadwal_uji):
    t, g, d = jadwal_uji["traveling"], jadwal_uji["got-talent"], jadwal_uji["drama"]
    assert klien_superadmin.get(f"/superadmin/absensi/kegiatan/{t.pk}/bentrok/").status_code == 200
    r = klien_superadmin.post(f"/superadmin/absensi/kegiatan/{t.pk}/bentrok/", {"bentrok": [str(g.pk), str(d.pk)]})
    assert r.status_code == 302
    assert set(g.bentrok_dengan.all()) == {t} and set(d.bentrok_dengan.all()) == {t}
    log = LogAktivitas.objects.get(aksi="kegiatan.bentrok_diubah")
    assert "Got-Talent" in str(log.data_baru)
    klien_superadmin.post(f"/superadmin/absensi/kegiatan/{t.pk}/bentrok/", {"bentrok": [str(g.pk)]})
    assert not d.bentrok_dengan.exists() and g.bentrok_dengan.exists()


def test_seed_memasang_bentrok_traveling_got_talent_hanya_saat_dibuat(db):
    from apps.inti import seed

    laporan: list[str] = []
    seed.seed_kegiatan(seed.FOLDER_DATA, laporan)
    t, g = Kegiatan.objects.get(kode="traveling"), Kegiatan.objects.get(kode="got-talent")
    assert set(t.bentrok_dengan.all()) == {g} and set(g.bentrok_dengan.all()) == {t}
    # Bila superadmin melepasnya, menjalankan seed lagi tidak memasangnya kembali.
    t.bentrok_dengan.remove(g)
    seed.seed_kegiatan(seed.FOLDER_DATA, laporan)
    assert not t.bentrok_dengan.exists()
