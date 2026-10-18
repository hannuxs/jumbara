"""Tes form biodata publik (docs/11-FORM-BIODATA.md bagian "Tes yang wajib ada")."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from apps.biodata import nik as nik_mod
from apps.biodata.foto import path_lengkap
from apps.biodata.models import JenisPenanda, Peserta, TokenKiriman
from apps.inti import pengaturan
from apps.inti.models import LogAktivitas

from .conftest import NIK_CONTOH, data_valid, file_foto, gambar, token_lama

URL = "/daftar/"


def kirim(client, data, ajax=False):
    extra = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"} if ajax else {}
    return client.post(URL, data, **extra)


def jenis_tanda(p: Peserta) -> set[str]:
    return set(p.penanda.values_list("jenis", flat=True))


# --- Kiriman valid -------------------------------------------------------------


def test_kiriman_valid_tersimpan_dan_foto_600x800(client, kontingen_madya):
    r = kirim(client, data_valid(kontingen_madya, nama_lengkap="  Siti   Aminah ", foto=file_foto(gambar(exif=True))))
    assert r.status_code == 302 and "/daftar/bukti/" in r["Location"]
    p = Peserta.objects.get()
    assert p.nama_lengkap == "SITI AMINAH"
    assert p.nama_orang_tua == "BUDI SANTOSO"
    assert p.kode_pendaftaran.startswith("SJ-") and len(p.kode_pendaftaran) == 9
    assert p.telepon_orang_tua == "6281234567890"
    assert p.persetujuan_data_pada is not None
    # NIK tidak tersimpan sebagai teks biasa.
    assert NIK_CONTOH not in p.nik_terenkripsi
    assert nik_mod.dekripsi(p.nik_terenkripsi) == NIK_CONTOH
    assert p.nik_samar == "6501********0003"
    # Foto 600x800, JPEG, tanpa EXIF, di folder privat.
    path = path_lengkap(p.foto_path)
    assert path is not None and "privat" in str(path)
    with Image.open(path) as img:
        assert img.size == (600, 800)
        assert img.format == "JPEG"
        assert not img.getexif()
    assert jenis_tanda(p) == set()
    assert LogAktivitas.objects.filter(aksi="biodata.dibuat", subjek_id=str(p.pk)).exists()


def test_bukti_tampil_tanpa_nik(client, kontingen_madya):
    r = kirim(client, data_valid(kontingen_madya))
    bukti = client.get(r["Location"])
    p = Peserta.objects.get()
    isi = bukti.content.decode()
    assert bukti.status_code == 200
    assert p.kode_pendaftaran in isi and "SITI AMINAH" in isi
    assert NIK_CONTOH not in isi and "6501" not in isi
    pdf = client.get(r["Location"] + "pdf/")
    assert pdf["Content-Type"] == "application/pdf" and pdf.content.startswith(b"%PDF")


def test_bukti_token_palsu_404(client):
    assert client.get("/daftar/bukti/palsu123/").status_code == 404


def test_kiriman_ajax_mengembalikan_json(client, kontingen_madya):
    r = kirim(client, data_valid(kontingen_madya), ajax=True)
    assert r.status_code == 200 and r.json()["ok"] is True and "/daftar/bukti/" in r.json()["url"]
    r = kirim(client, data_valid(kontingen_madya, nik="123", token=token_lama()), ajax=True)
    assert r.status_code == 400 and "nik" in r.json()["galat"]


# --- NIK -------------------------------------------------------------------------


@pytest.mark.parametrize("nik", ["123456789012345", "12345678901234567", "65010141011200ab", "1111111111111111", ""])
def test_nik_tidak_valid_ditolak(client, kontingen_madya, nik):
    r = kirim(client, data_valid(kontingen_madya, nik=nik))
    assert r.status_code == 400
    assert "nik" in r.context["form"].errors
    assert Peserta.objects.count() == 0


def test_nik_dobel_ditolak_tanpa_membocorkan_data(client, kontingen_madya):
    kirim(client, data_valid(kontingen_madya, nama_lengkap="Pemilik Asli"))
    r = kirim(client, data_valid(kontingen_madya, nama_lengkap="Orang Lain", token=token_lama()))
    assert r.status_code == 400
    isi = r.content.decode()
    assert "NIK ini sudah terdaftar" in isi
    assert "Pemilik Asli" not in isi
    assert Peserta.objects.count() == 1


def test_nik_dengan_spasi_dirapikan(client, kontingen_madya):
    r = kirim(client, data_valid(kontingen_madya, nik="6501 0141 0112 0003"))
    assert r.status_code == 302


def test_nik_boleh_dipakai_lagi_setelah_dihapus(client, kontingen_madya):
    kirim(client, data_valid(kontingen_madya))
    Peserta.objects.get().hapus_lunak("uji")
    r = kirim(client, data_valid(kontingen_madya, token=token_lama()))
    assert r.status_code == 302
    assert Peserta.semua.count() == 2


# --- Jadwal -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "paksa,buka,tutup",
    [
        ("OTOMATIS", "2099-01-01T00:00:00+08:00", "2099-12-31T23:59:59+08:00"),  # belum buka
        ("OTOMATIS", "2020-01-01T00:00:00+08:00", "2020-12-31T23:59:59+08:00"),  # sudah tutup
        ("TUTUP", "2020-01-01T00:00:00+08:00", "2099-12-31T23:59:59+08:00"),  # paksa tutup
    ],
)
def test_form_tertutup_menolak_kiriman_di_server(client, kontingen_madya, paksa, buka, tutup):
    pengaturan.simpan("biodata.paksa_status", paksa)
    pengaturan.simpan("biodata.buka_pada", buka)
    pengaturan.simpan("biodata.tutup_pada", tutup)
    r = kirim(client, data_valid(kontingen_madya))
    assert r.status_code == 403
    assert Peserta.objects.count() == 0
    assert client.get(URL).templates[0].name == "biodata/tutup.html"


def test_form_terkunci_menolak(client, kontingen_madya):
    pengaturan.simpan("biodata.terkunci", True)
    assert kirim(client, data_valid(kontingen_madya)).status_code == 403


def test_jadwal_otomatis_menerima_saat_dibuka(client, kontingen_madya):
    pengaturan.simpan("biodata.paksa_status", "OTOMATIS")
    pengaturan.simpan("biodata.buka_pada", "2020-01-01T00:00:00+08:00")
    pengaturan.simpan("biodata.tutup_pada", "2099-12-31T23:59:59+08:00")
    assert kirim(client, data_valid(kontingen_madya)).status_code == 302


def test_paksa_buka_sebelum_jadwal(client, kontingen_madya):
    pengaturan.simpan("biodata.paksa_status", "BUKA")
    pengaturan.simpan("biodata.buka_pada", "2099-01-01T00:00:00+08:00")
    assert kirim(client, data_valid(kontingen_madya)).status_code == 302


def test_status_form_unit():
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from apps.biodata.services import status_form

    wita = ZoneInfo("Asia/Makassar")
    nilai = {
        "biodata.paksa_status": "OTOMATIS",
        "biodata.buka_pada": "2026-10-26T00:00:00+08:00",
        "biodata.tutup_pada": "2026-11-02T23:59:59+08:00",
    }
    assert status_form(nilai, datetime(2026, 10, 25, 23, 59, 59, tzinfo=wita)).alasan == "BELUM_BUKA"
    assert status_form(nilai, datetime(2026, 10, 26, 0, 0, 0, tzinfo=wita)).terbuka
    assert status_form(nilai, datetime(2026, 11, 2, 23, 59, 59, tzinfo=wita)).terbuka
    assert status_form(nilai, datetime(2026, 11, 3, 0, 0, 0, tzinfo=wita)).alasan == "SUDAH_TUTUP"


# --- Tanda (diterima + ditandai) --------------------------------------------------


def test_tingkat_beda_dengan_sekolah_ditolak(client, kontingen_madya):
    # REVISI R1: tingkat dipilih dulu; sekolah dari tingkat lain ditolak server.
    r = kirim(client, data_valid(kontingen_madya, tingkat="WIRA"))
    assert r.status_code == 400
    assert "bukan sekolah tingkat Wira" in r.context["form"].errors["kontingen"][0]
    assert Peserta.objects.count() == 0


def test_form_tingkat_tampil_sebelum_sekolah(client, kontingen_madya):
    isi = client.get(URL).content.decode()
    assert isi.index('data-isian="tingkat"') < isi.index('data-isian="kontingen"') < isi.index('data-isian="peran"')
    assert 'data-tingkat="MADYA"' in isi


def test_kuota_penuh_diterima_dan_ditandai(client, kontingen_madya):
    niks = ["6501014101120003", "6501014201120004", "6501014301120005", "6501014401120006"]
    for i, nik in enumerate(niks):
        hari = str(i + 1)
        r = kirim(
            client,
            data_valid(
                kontingen_madya,
                nik=nik,
                nama_lengkap=f"Anak Ke {'ABCD'[i]}uji",
                tanggal_lahir_0=hari,
                token=token_lama(),
            ),
        )
        assert r.status_code == 302
    urut = list(Peserta.objects.order_by("dibuat_pada", "id"))
    assert [JenisPenanda.KUOTA_PENUH in jenis_tanda(p) for p in urut] == [False, False, False, True]


def test_nik_tidak_dicocokkan_dengan_tanggal_lahir_dan_jk(client, kontingen_madya):
    # REVISI R4: tidak ada pencocokan isi NIK dengan tanggal lahir/jenis kelamin.
    r = kirim(client, data_valid(kontingen_madya, nik="6501019999990003", jenis_kelamin="L", tanggal_lahir_0="2"))
    assert r.status_code == 302
    assert jenis_tanda(Peserta.objects.get()) == set()
    assert "cocok dengan NIK" not in client.get(URL).content.decode()
    assert "cocok dengan NIK" not in Path("static/js/biodata.js").read_text(encoding="utf-8")
    assert not {"NIK_TGL_LAHIR_BEDA", "NIK_JK_BEDA"} & set(JenisPenanda.values)


def test_usia_tidak_wajar_ditandai(client, kontingen_madya):
    # Lahir 2004 -> 22 tahun, bukan usia peserta Madya (11-16).
    kirim(client, data_valid(kontingen_madya, nik="6501014101040003", tanggal_lahir_2="2004"))
    assert JenisPenanda.USIA_TIDAK_WAJAR in jenis_tanda(Peserta.objects.get())


def test_nama_mirip_dan_foto_duplikat_ditandai(client, kontingen_madya):
    foto = gambar(warna=(10, 20, 30))
    kirim(client, data_valid(kontingen_madya, nama_lengkap="Siti Aminah", foto=file_foto(foto)))
    kirim(client, data_valid(kontingen_madya, nik="6501014201120004", tanggal_lahir_0="2", nama_lengkap="SITI  aminah",
                              foto=file_foto(foto), token=token_lama()))  # fmt: skip
    for p in Peserta.objects.all():
        assert {JenisPenanda.NAMA_MIRIP, JenisPenanda.FOTO_DUPLIKAT} <= jenis_tanda(p)


# --- Aturan per peran --------------------------------------------------------------


@pytest.mark.parametrize("peran", ["PIMPINAN_KONTINGEN", "PEMBINA_PENDAMPING"])
def test_peran_dewasa_tanpa_data_ortu_diterima(client, kontingen_madya, peran):
    r = kirim(client, data_valid(kontingen_madya, peran=peran, nik="6501014101800003", tanggal_lahir_2="1980",
                                 nama_orang_tua="", telepon_orang_tua="", telepon="0812-1111-2222"))  # fmt: skip
    assert r.status_code == 302
    assert Peserta.objects.get().telepon == "6281211112222"


def test_peran_dewasa_tanpa_telepon_ditolak(client, kontingen_madya):
    r = kirim(client, data_valid(kontingen_madya, peran="PIMPINAN_KONTINGEN", telepon=""))
    assert r.status_code == 400 and "telepon" in r.context["form"].errors


@pytest.mark.parametrize("peran", ["PESERTA", "PENINJAU"])
def test_peserta_tanpa_data_ortu_ditolak(client, kontingen_madya, peran):
    r = kirim(client, data_valid(kontingen_madya, peran=peran, nama_orang_tua="", telepon_orang_tua=""))
    assert r.status_code == 400
    galat = r.context["form"].errors
    assert "nama_orang_tua" in galat and "telepon_orang_tua" in galat


# --- Isian ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "nama,disimpan",
    [
        ("M. Fuad", "M. FUAD"),
        ("As’ad", "AS'AD"),
        ("sri handayani, s.pd", "SRI HANDAYANI, S.PD"),
        ("Ni Luh Putu-Ayu", "NI LUH PUTU-AYU"),
        ("AHMAD FARHAN", "AHMAD FARHAN"),
    ],
)
def test_nama_wajar_diterima_dan_disimpan_kapital(client, kontingen_madya, nama, disimpan):
    # REVISI R3: nama (termasuk gelar) disimpan HURUF KAPITAL.
    r = kirim(client, data_valid(kontingen_madya, nama_lengkap=nama, nama_orang_tua="ibu siti, s.e"))
    assert r.status_code == 302, r.context["form"].errors if r.context else r
    p = Peserta.objects.get()
    assert p.nama_lengkap == disimpan
    assert p.nama_orang_tua == "IBU SITI, S.E"


@pytest.mark.parametrize("nama", ["Budi123", "Si", "<script>", "Budi@Mail", "...."])
def test_nama_aneh_ditolak(client, kontingen_madya, nama):
    r = kirim(client, data_valid(kontingen_madya, nama_lengkap=nama))
    assert r.status_code == 400 and "nama_lengkap" in r.context["form"].errors


@pytest.mark.parametrize(
    "tel,hasil",
    [("081234567890", "6281234567890"), ("+62 812-3456-7890", "6281234567890"), ("6281234567890", "6281234567890")],
)
def test_telepon_dinormalkan(tel, hasil):
    from apps.biodata.services import normalisasi_telepon

    assert normalisasi_telepon(tel) == hasil


@pytest.mark.parametrize("tel", ["12345", "0812abc", "021", "+1 555 1234 5678"])
def test_telepon_tidak_valid(tel):
    from apps.biodata.services import normalisasi_telepon

    assert normalisasi_telepon(tel) is None


def test_tanggal_lahir_tidak_ada_di_kalender(client, kontingen_madya):
    r = kirim(client, data_valid(kontingen_madya, tanggal_lahir_0="31", tanggal_lahir_1="2"))
    assert r.status_code == 400 and "tanggal_lahir" in r.context["form"].errors


def test_kontingen_tidak_ada_ditolak(client, kontingen_madya):
    r = kirim(client, data_valid(kontingen_madya, kontingen="999999"))
    assert r.status_code == 400 and "kontingen" in r.context["form"].errors


def test_kontingen_terhapus_tidak_bisa_dipilih(client, kontingen_madya):
    kontingen_madya.hapus_lunak("uji")
    r = kirim(client, data_valid(kontingen_madya))
    assert r.status_code == 400 and "kontingen" in r.context["form"].errors


def test_persetujuan_wajib(client, kontingen_madya):
    r = kirim(client, data_valid(kontingen_madya, persetujuan=None))
    assert r.status_code == 400 and "persetujuan" in r.context["form"].errors


# --- Foto ---------------------------------------------------------------------------------


def test_file_bukan_gambar_ditolak(client, kontingen_madya):
    palsu = file_foto(b"%PDF-1.4 bukan gambar" * 50, nama="foto.jpg")
    r = kirim(client, data_valid(kontingen_madya, foto=palsu))
    assert r.status_code == 400 and "foto" in r.context["form"].errors
    assert Peserta.objects.count() == 0


def test_gif_ditolak_walau_berekstensi_jpg(client, kontingen_madya):
    r = kirim(client, data_valid(kontingen_madya, foto=file_foto(gambar("GIF", mode="P", warna=1), nama="a.jpg")))
    assert r.status_code == 400 and "foto" in r.context["form"].errors


def test_foto_lebih_5mb_ditolak(client, kontingen_madya):
    besar = gambar() + b"\0" * (5 * 1024 * 1024)
    r = kirim(client, data_valid(kontingen_madya, foto=file_foto(besar)))
    assert r.status_code == 400 and "5 MB" in r.context["form"].errors["foto"][0]


def test_png_transparan_diterima(client, kontingen_madya):
    png = gambar("PNG", mode="RGBA", warna=(0, 0, 0, 0), ukuran=(500, 900))
    r = kirim(client, data_valid(kontingen_madya, foto=file_foto(png, nama="a.png", tipe="image/png")))
    assert r.status_code == 302
    with Image.open(path_lengkap(Peserta.objects.get().foto_path)) as img:
        assert img.size == (600, 800) and img.mode == "RGB"


def test_foto_wajib_mutlak(client, kontingen_madya):
    # REVISI R2: foto dicetak di kartu, jadi selalu wajib (pengaturan lama tidak berpengaruh).
    pengaturan.simpan("biodata.foto_wajib", False)
    r = kirim(client, data_valid(kontingen_madya, foto=None))
    assert r.status_code == 400 and "foto" in r.context["form"].errors
    assert Peserta.objects.count() == 0


def test_koordinat_potong_dipakai(client, kontingen_madya):
    # Separuh kiri merah, kanan biru; potong hanya bagian kanan -> hasil biru.
    img = Image.new("RGB", (1200, 800), (255, 0, 0))
    img.paste((0, 0, 255), (600, 0, 1200, 800))
    buf = io.BytesIO()
    img.save(buf, "JPEG")
    potong = '{"x": 650, "y": 0, "w": 540, "h": 720, "r": 0}'
    kirim(client, data_valid(kontingen_madya, foto=file_foto(buf.getvalue()), foto_potong=potong))
    with Image.open(path_lengkap(Peserta.objects.get().foto_path)) as hasil:
        r, g, b = hasil.getpixel((300, 400))
        assert b > 200 and r < 60


# --- Anti spam dan kiriman ganda ----------------------------------------------------------


def test_honeypot_ditolak(client, kontingen_madya):
    r = kirim(client, data_valid(kontingen_madya, situs_web="http://spam"))
    assert r.status_code == 400 and Peserta.objects.count() == 0


def test_terlalu_cepat_ditolak(client, kontingen_madya):
    from apps.biodata.forms import buat_token

    r = kirim(client, data_valid(kontingen_madya, token=buat_token()))
    assert r.status_code == 400 and Peserta.objects.count() == 0


def test_token_rusak_ditolak(client, kontingen_madya):
    r = kirim(client, data_valid(kontingen_madya, token="rusak"))
    assert r.status_code == 400 and Peserta.objects.count() == 0


def test_kiriman_ganda_token_sama_satu_biodata(client, kontingen_madya):
    token = token_lama()
    r1 = kirim(client, data_valid(kontingen_madya, token=token))
    r2 = kirim(client, data_valid(kontingen_madya, token=token))
    assert r1.status_code == r2.status_code == 302
    assert r1["Location"] == r2["Location"]
    assert Peserta.objects.count() == 1
    assert TokenKiriman.objects.count() == 1
