"""Penerbitan piagam: template bawaan, unggah latar, syarat berhak, nomor, data cetak."""

from __future__ import annotations

import io
import uuid
from datetime import date
from pathlib import Path

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from PIL import Image, UnidentifiedImageError

from apps.absensi.daftar_ulang import KODE_DAFTAR_ULANG
from apps.absensi.models import Kegiatan, Kehadiran
from apps.biodata.models import Peserta
from apps.inti import pengaturan
from apps.inti.log import catat
from apps.inti.utils import tanggal_id
from apps.kartu.services import urutkan_untuk_cetak
from apps.kontingen.models import Kontingen

from .models import JenisPiagam, Orientasi, PiagamTerbit, TemplatePiagam

UKURAN_LATAR_MAKS = 20 * 1024 * 1024
ACARA = "Jumbara PMR Tingkat Kabupaten Bulungan V Tahun 2026"
ACARA_PANJANG = (
    "Jumbara PMR Tingkat Kabupaten Bulungan V Tahun 2026, 12-15 November 2026, di Kebun Raya Bundayati, Tanjung Selor"
)
PLACEHOLDER = {
    "nama": "Nama penerima (orang, atau 'Kontingen ...' untuk juara kontingen)",
    "kontingen": "Nama kontingen (sekolah)",
    "peran": "Peran: Peserta, Pimpinan Kontingen, Pembina Pendamping, Peninjau",
    "tingkat": "Mula / Madya / Wira",
    "kegiatan": "Nama kegiatan/lomba (piagam juara)",
    "kegiatan_tingkat": "Kegiatan + 'Tingkat ...' (tanpa tingkat untuk Got Talent)",
    "juara": "Juara 1, Juara 2, ... (piagam juara)",
    "juara_romawi": "Juara I, Juara II, ...",
    "peringkat": "Angka peringkat",
    "nomor": "Nomor piagam",
    "tempat": "Tempat penerbitan (pengaturan)",
    "tanggal": "Tanggal penerbitan, misal 15 November 2026",
    "acara": ACARA,
    "acara_panjang": ACARA_PANJANG,
    "unit_pmr": "PMR <TINGKAT> UNIT <SEKOLAH>, misal PMR MADYA UNIT SMP NEGERI 1 BUNYU",
    "sebagai": "PESERTA, PIMPINAN KONTINGEN, ... atau JUARA I (piagam juara)",
    "tanggal_acara": "Tanggal kegiatan (pengaturan), misal 12 - 15 November 2026",
    "lokasi_acara": "Lokasi kegiatan (pengaturan)",
    "ttd_jabatan": "Jabatan penanda tangan (pengaturan), misal Ketua PMI Kabupaten Bulungan",
    "ttd_nama": "Nama penanda tangan (pengaturan)",
    "ttd_nip": "NIP/NIA penanda tangan (pengaturan, boleh kosong)",
}


class GagalPiagam(Exception):
    def __init__(self, pesan: str):
        super().__init__(pesan)
        self.pesan = pesan


def _e(kode, teks, y, font, ukuran, x=20, lebar=257, warna="#1F2937", rata="TENGAH", ukuran_min=None, baris_maks=1,
       kapital=False) -> dict:  # fmt: skip
    return {"kode": kode, "teks": teks, "x": x, "y": y, "lebar": lebar, "font": font, "ukuran": ukuran,
            "ukuran_min": ukuran_min or round(ukuran * 0.6, 1), "warna": warna, "rata": rata,
            "baris_maks": baris_maks, "kapital": kapital}  # fmt: skip


def elemen_bawaan(jenis: str, orientasi: str = Orientasi.TEGAK) -> list[dict]:
    """Tata letak awal: tegak (bawaan sejak R15) atau A4 mendatar (297 x 210 mm)."""
    if orientasi == Orientasi.TEGAK:
        return elemen_tegak(jenis)
    umum_atas = [
        _e("judul", "PIAGAM PENGHARGAAN", 58, "POPPINS_TEBAL", 32, warna="#E2451F"),
        _e("nomor", "Nomor: {nomor}", 66, "INTER", 10, warna="#6B7280"),
        _e("pengantar", "diberikan kepada:", 80, "INTER", 13),
    ]
    ttd = [
        _e("tempat_tanggal", "{tempat}, {tanggal}", 160, "INTER", 11, x=180, lebar=95),
        _e("jabatan", "Ketua Panitia Jumbara V 2026", 166, "INTER_SEMI", 11, x=180, lebar=95),
        _e("penanda_tangan", "(................................)", 192, "INTER_SEMI", 11, x=180, lebar=95),
    ]
    if jenis == JenisPiagam.JUARA:
        isi = [
            _e("nama", "{nama}", 97, "POPPINS_TEBAL", 28, ukuran_min=14, warna="#1F2937"),
            _e("juara", "sebagai {juara}", 112, "POPPINS_SEMI", 20, warna="#E2451F"),
            _e("kegiatan", "{kegiatan_tingkat}", 123, "INTER_SEMI", 14),
            _e("acara", "pada {acara_panjang}.", 134, "INTER", 11.5, x=40, lebar=217, baris_maks=2),
        ]
    else:
        isi = [
            _e("nama", "{nama}", 97, "POPPINS_TEBAL", 28, ukuran_min=14, warna="#1F2937"),
            _e("peran", "sebagai {peran} dari Kontingen {kontingen}", 111, "INTER_SEMI", 14, x=30, lebar=237),
            _e("tingkat", "Tingkat {tingkat}", 120, "INTER", 12),
            _e("acara", "pada {acara_panjang}.", 132, "INTER", 11.5, x=40, lebar=217, baris_maks=2),
        ]
    return umum_atas + isi + ttd


def _t(kode, teks, y, font, ukuran, **kw) -> dict:
    """Elemen untuk A4 tegak (210 x 297 mm): lebar penuh dengan tepi 15 mm, rata tengah."""
    return _e(kode, teks, y, font, ukuran, x=kw.pop("x", 15), lebar=kw.pop("lebar", 180), **kw)


MERAH = "#E53935"


def elemen_tegak(jenis: str) -> list[dict]:
    """Tata letak piagam tegak sesuai contoh panitia (R15): pita warna, logo, PENGHARGAAN, nomor, nama, unit PMR,
    sebagai, kegiatan, tanggal, lalu tanda tangan satu orang (Ketua PMI)."""
    atas = [
        _t("judul", "PENGHARGAAN", 72, "POPPINS_TEBAL", 36, warna=MERAH),
        _t("nomor", "No: {nomor}", 80, "INTER_SEMI", 9.5, warna="#3B5B8C"),
        _t("pengantar", "Diberikan Kepada :", 96, "INTER", 14, warna="#111111"),
        _t("nama", "{nama}", 108, "POPPINS_TEBAL", 22, ukuran_min=12, warna="#111111", kapital=True),
        _t("unit", "{unit_pmr}", 116, "INTER_SEMI", 11, ukuran_min=8, warna="#111111", kapital=True),
        _t("sebagai_label", "Sebagai :", 132, "INTER", 14, warna="#111111"),
        _t("sebagai", "{sebagai}", 145, "POPPINS_TEBAL", 24, ukuran_min=14, warna=MERAH, kapital=True),
    ]
    if jenis == JenisPiagam.JUARA:
        atas.append(_t("kegiatan", "{kegiatan_tingkat}", 154, "INTER_SEMI", 14, ukuran_min=10, warna="#111111"))
    y = 168 if jenis == JenisPiagam.JUARA else 162
    isi = [
        _t("pada", "Pada Kegiatan", y, "INTER", 14, warna="#111111"),
        _t("acara", ACARA, y + 8, "INTER", 14, ukuran_min=10, warna="#111111"),
        _t("lokasi", "{lokasi_acara}", y + 15, "INTER", 13, ukuran_min=9, warna="#111111"),
        _t("tanggal_acara", "pada Tanggal {tanggal_acara}", y + 25, "INTER_SEMI", 14, warna="#111111"),
    ]
    ttd = [
        _t("tempat_tanggal", "{tempat}, {tanggal}", 222, "INTER", 11, warna="#111111"),
        _t("jabatan", "{ttd_jabatan}", 229, "INTER_SEMI", 12, ukuran_min=9, warna="#111111"),
        _t("ttd_nama", "{ttd_nama}", 262, "POPPINS_SEMI", 13, ukuran_min=9, warna="#111111"),
        _t("ttd_nip", "{ttd_nip}", 268, "INTER", 10, warna="#374151"),
    ]
    return atas + isi + ttd


NAMA_TEGAK = {
    JenisPiagam.PESERTA: "Piagam peserta 2026 (tegak, desain bawaan)",
    JenisPiagam.JUARA: "Piagam juara 2026 (tegak, desain bawaan)",
}


def pastikan_template_tegak() -> list[TemplatePiagam]:
    """R15: piagam tegak (portrait) menjadi template bawaan. Template lama tidak dihapus; template bawaan
    mendatar tanpa latar panitia dinonaktifkan agar tidak terpilih otomatis (masih bisa diaktifkan lagi)."""
    dibuat = []
    for jenis, nama in NAMA_TEGAK.items():
        if TemplatePiagam.semua.filter(jenis=jenis, nama=nama).exists():
            continue
        dibuat.append(TemplatePiagam.objects.create(
            nama=nama, jenis=jenis, ukuran_kertas="A4", orientasi=Orientasi.TEGAK, desain_bawaan=True,
            tempel_logo=True, logo_x=0, logo_y=24, logo_tinggi=24, elemen=elemen_tegak(jenis),
        ))  # fmt: skip
        TemplatePiagam.objects.filter(jenis=jenis, orientasi=Orientasi.MENDATAR, desain_bawaan=True, latar="",
                                      aktif=True).exclude(nama=nama).update(aktif=False)  # fmt: skip
    return dibuat


def pastikan_template_bawaan() -> list[TemplatePiagam]:
    """Buat template bawaan (peserta dan juara, tegak sejak R15) bila belum ada."""
    return pastikan_template_tegak()


# --- Latar dari panitia ------------------------------------------------------------------------------------


def simpan_latar(request, t: TemplatePiagam, berkas) -> None:
    """Gambar PNG/JPG atau PDF satu halaman. PDF diubah menjadi gambar 200 dpi. Orientasi disesuaikan."""
    if berkas.size > UKURAN_LATAR_MAKS:
        raise GagalPiagam("Ukuran file paling besar 20 MB.")
    isi = berkas.read()
    if isi[:4] == b"%PDF":
        try:
            import pypdfium2 as pdfium

            doc = pdfium.PdfDocument(isi)
            if len(doc) < 1:
                raise GagalPiagam("PDF kosong.")
            img = doc[0].render(scale=200 / 72).to_pil().convert("RGB")
        except GagalPiagam:
            raise
        except Exception:  # noqa: BLE001 (PDF rusak/terkunci)
            raise GagalPiagam(
                "PDF tidak bisa dibaca. Kirim PDF satu halaman tanpa kata sandi, atau gambar PNG/JPG."
            ) from None
    else:
        try:
            Image.MAX_IMAGE_PIXELS = 80_000_000
            img = Image.open(io.BytesIO(isi))
            img.load()
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
            raise GagalPiagam("File harus gambar PNG/JPG atau PDF.") from None
        if img.format not in ("PNG", "JPEG", "MPO"):
            raise GagalPiagam("File harus gambar PNG/JPG atau PDF.")
        img = img.convert("RGB")
    if min(img.size) < 600:
        raise GagalPiagam(
            "Resolusi gambar terlalu kecil (minimal 600 piksel). Minta file resolusi tinggi dari panitia."
        )
    folder = Path(settings.SIGAP_FOLDER_PRIVAT) / "piagam"
    folder.mkdir(parents=True, exist_ok=True)
    nama = f"{uuid.uuid4().hex}.png"
    img.save(folder / nama, format="PNG", optimize=True)
    lama = t.latar
    t.latar = nama
    t.latar_asli = Path(berkas.name).name[:255]
    t.orientasi = Orientasi.MENDATAR if img.width >= img.height else Orientasi.TEGAK
    t.desain_bawaan = False
    t.save(update_fields=["latar", "latar_asli", "orientasi", "desain_bawaan", "diubah_pada"])
    if lama and (p := folder / lama).is_file() and not TemplatePiagam.semua.filter(latar=lama).exists():
        p.unlink()
    catat(request, "piagam.latar_diunggah", t, keterangan=f"{t.nama}: {t.latar_asli} ({img.width}x{img.height})")


def simpan_ttd(request, berkas) -> None:
    """Gambar tanda tangan PNG/JPG. Latar putih/terang dibuat transparan agar menyatu dengan piagam."""
    if berkas.size > 5 * 1024 * 1024:
        raise GagalPiagam("Ukuran gambar tanda tangan paling besar 5 MB.")
    try:
        img = Image.open(io.BytesIO(berkas.read()))
        img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise GagalPiagam("File tanda tangan harus gambar PNG atau JPG.") from None
    if img.format not in ("PNG", "JPEG", "MPO"):
        raise GagalPiagam("File tanda tangan harus gambar PNG atau JPG.")
    img = img.convert("RGBA")
    img.thumbnail((1600, 1600))
    piksel = [(r, g, b, 0 if min(r, g, b) > 225 else a) for r, g, b, a in img.getdata()]
    img.putdata(piksel)
    if img.getbbox():
        img = img.crop(img.getbbox())
    folder = Path(settings.SIGAP_FOLDER_PRIVAT) / "piagam"
    folder.mkdir(parents=True, exist_ok=True)
    nama = f"ttd-{uuid.uuid4().hex}.png"
    img.save(folder / nama, format="PNG", optimize=True)
    lama = str(pengaturan.ambil("piagam.ttd_gambar") or "")
    pengaturan.simpan("piagam.ttd_gambar", nama, oleh=getattr(request.user, "username", ""))
    if lama.startswith("ttd-") and (p := folder / lama).is_file():
        p.unlink()
    catat(request, "piagam.ttd_diunggah", keterangan=f"{Path(berkas.name).name[:120]} ({img.width}x{img.height})")


def hapus_ttd(request) -> None:
    lama = str(pengaturan.ambil("piagam.ttd_gambar") or "")
    pengaturan.simpan("piagam.ttd_gambar", "", oleh=getattr(request.user, "username", ""))
    p = Path(settings.SIGAP_FOLDER_PRIVAT) / "piagam" / lama
    if lama.startswith("ttd-") and p.is_file():
        p.unlink()
    catat(request, "piagam.ttd_dihapus", keterangan="Gambar tanda tangan dihapus")


# --- Syarat dan data ------------------------------------------------------------------------------------------


def _tanggal() -> str:
    teks = str(pengaturan.ambil("piagam.tanggal") or "")
    try:
        return tanggal_id(date.fromisoformat(teks), hari=False)
    except ValueError:
        return teks


def data_umum() -> dict:
    return {
        "tempat": pengaturan.ambil("piagam.tempat") or "",
        "tanggal": _tanggal(),
        "acara": ACARA,
        "acara_panjang": ACARA_PANJANG,
        "tanggal_acara": pengaturan.ambil("piagam.tanggal_acara") or "",
        "lokasi_acara": pengaturan.ambil("piagam.lokasi_acara") or "",
        "ttd_jabatan": pengaturan.ambil("piagam.ttd_jabatan") or "",
        "ttd_nama": pengaturan.ambil("piagam.ttd_nama") or "(................................)",
        "ttd_nip": pengaturan.ambil("piagam.ttd_nip") or "",
    }


def unit_pmr(tingkat_label: str, kontingen_nama: str) -> str:
    """Seperti di daftar nomor sertifikat panitia: PMR MADYA UNIT SMP NEGERI 1 BUNYU."""
    return f"PMR {tingkat_label} UNIT {kontingen_nama}".upper() if kontingen_nama else ""


def sudah_daftar_ulang_ids(kontingen: Kontingen | None = None) -> set[int]:
    qs = Kehadiran.objects.filter(titik_absen__kegiatan__kode=KODE_DAFTAR_ULANG)
    if kontingen is not None:
        qs = qs.filter(peserta__kontingen=kontingen)
    return set(qs.values_list("peserta_id", flat=True))


def alasan_tidak_berhak(p: Peserta, daftar_ulang: set[int] | None = None) -> str:
    if p.tidak_berhak_piagam:
        return "Tidak berhak (sanksi): " + (p.alasan_tidak_berhak_piagam or "tanpa keterangan")
    if pengaturan.ambil("piagam.syarat_daftar_ulang") and daftar_ulang is not None and p.pk not in daftar_ulang:
        return "Belum daftar ulang"
    return ""


def daftar_peserta(kontingen: Kontingen) -> list[dict]:
    du = sudah_daftar_ulang_ids(kontingen)
    terbit = {
        x.peserta_id: x for x in PiagamTerbit.objects.filter(jenis=JenisPiagam.PESERTA, peserta__kontingen=kontingen)
    }
    return [{"p": p, "alasan": alasan_tidak_berhak(p, du), "terbit": terbit.get(p.pk)}
            for p in urutkan_untuk_cetak(Peserta.objects.filter(kontingen=kontingen))]  # fmt: skip


def data_peserta(p: Peserta) -> dict:
    return {
        **data_umum(), "nama": p.nama_lengkap, "kontingen": p.kontingen.nama, "peran": p.get_peran_display(),
        "tingkat": p.get_tingkat_display(), "unit_pmr": unit_pmr(p.get_tingkat_display(), p.kontingen.nama),
        "sebagai": p.get_peran_display().upper(),
    }  # fmt: skip


ROMAWI = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]


def data_juara(
    peringkat: int, kegiatan: str, tingkat: str, kontingen: Kontingen | None, peserta: Peserta | None
) -> dict:
    nama = peserta.nama_lengkap if peserta else f"Kontingen {kontingen.nama}" if kontingen else ""
    k_nama = peserta.kontingen.nama if peserta else kontingen.nama if kontingen else ""
    t_label = peserta.get_tingkat_display() if peserta else (kontingen.get_tingkat_display() if kontingen else tingkat)
    romawi = f"Juara {ROMAWI[peringkat] if peringkat < len(ROMAWI) else peringkat}"
    return {
        "unit_pmr": unit_pmr(t_label, k_nama), "sebagai": romawi.upper(),
        **data_umum(), "nama": nama, "kontingen": (peserta.kontingen.nama if peserta else kontingen.nama if kontingen else ""),
        "peran": peserta.get_peran_display() if peserta else "", "tingkat": tingkat, "kegiatan": kegiatan,
        "kegiatan_tingkat": f"{kegiatan} Tingkat {tingkat}" if tingkat else kegiatan,
        "peringkat": peringkat, "juara": f"Juara {peringkat}",
        "juara_romawi": f"Juara {ROMAWI[peringkat] if peringkat < len(ROMAWI) else peringkat}",
    }  # fmt: skip


def data_contoh(jenis: str) -> dict:
    """Data terpanjang untuk pratinjau tata letak."""
    terpanjang = max(Peserta.objects.values_list("nama_lengkap", flat=True), key=len, default="")
    nama = max([terpanjang, "MUHAMMAD RIZKY ALFAREZA PRATAMA SAPUTRA WIJAYA"], key=len)
    kontingen = max(
        Kontingen.objects.values_list("nama", flat=True), key=len, default="SD Negeri 003 Tanjung Palas Utara"
    )
    data = {**data_umum(), "nama": nama, "kontingen": kontingen, "peran": "Pembina Pendamping", "tingkat": "Madya",
            "unit_pmr": unit_pmr("Madya", kontingen), "sebagai": "PEMBINA PENDAMPING",
            "nomor": nomor_dari_format(JenisPiagam(jenis), 123)}  # fmt: skip
    if jenis == JenisPiagam.JUARA:
        data.update(data_juara(1, "Wahana Kepalangmerahan - Voli Tutup Terpal", "Madya", None, None))
        data["nama"] = nama
        data["unit_pmr"] = unit_pmr("Madya", kontingen)
        data["nomor"] = nomor_dari_format(JenisPiagam.JUARA, 7)
    return data


# --- Nomor dan penerbitan ---------------------------------------------------------------------------------------


def nomor_dari_format(jenis: str, urut: int) -> str:
    kunci = "piagam.format_nomor_juara" if jenis == JenisPiagam.JUARA else "piagam.format_nomor_peserta"
    pola = str(pengaturan.ambil(kunci) or "{urut}")
    try:
        digit = max(1, min(6, int(pengaturan.ambil("piagam.digit_urut") or 3)))
    except (TypeError, ValueError):
        digit = 3
    return pola.replace("{urut}", str(urut).zfill(digit)) if "{urut}" in pola else f"{str(urut).zfill(digit)}{pola}"


def _terbitkan(request, kunci: str, jenis: str, template: TemplatePiagam, data: dict, **kw) -> PiagamTerbit:
    """Ambil piagam yang sudah ada (nomor tetap, data diperbarui) atau terbitkan dengan nomor urut berikut."""
    lama = PiagamTerbit.objects.filter(kunci=kunci).first()
    if lama is not None:
        baru = {**data, "nomor": lama.nomor}
        if lama.data != baru or lama.template_id != template.pk:
            lama.data, lama.template = baru, template
            lama.save(update_fields=["data", "template", "diubah_pada"])
        return lama
    for _ in range(5):
        try:
            with transaction.atomic():
                terakhir = PiagamTerbit.objects.select_for_update().filter(jenis=jenis).order_by("-urut").first()
                urut = (terakhir.urut if terakhir else 0) + 1
                nomor = nomor_dari_format(jenis, urut)
                x = PiagamTerbit.objects.create(
                    kunci=kunci, jenis=jenis, urut=urut, nomor=nomor, template=template, data={**data, "nomor": nomor},
                    diterbitkan_oleh=getattr(request, "nama_pelaku", "") or getattr(getattr(request, "user", None), "username", ""),
                    **kw,
                )  # fmt: skip
                catat(request, "piagam.terbit", x, keterangan=f"{nomor} · {data.get('nama', '')}"[:255])
                return x
        except IntegrityError:
            if (lama := PiagamTerbit.objects.filter(kunci=kunci).first()) is not None:
                return lama
            continue  # nomor urut bentrok dengan penerbitan bersamaan: coba lagi
    raise GagalPiagam("Gagal memberi nomor piagam (terlalu banyak penerbitan bersamaan). Coba lagi.")


def template_aktif(jenis: str, pk: int | None = None) -> TemplatePiagam:
    pastikan_template_bawaan()
    qs = TemplatePiagam.objects.filter(jenis=jenis, aktif=True)
    t = qs.filter(pk=pk).first() if pk else qs.order_by("-diubah_pada").first()
    if t is None:
        raise GagalPiagam("Belum ada template piagam aktif untuk jenis ini.")
    return t


def terbitkan_peserta(
    request, peserta: list[Peserta], template: TemplatePiagam
) -> tuple[list[PiagamTerbit], list[tuple[Peserta, str]]]:
    """Terbitkan untuk yang berhak; kembalikan (piagam, dilewati beserta alasan)."""
    du = sudah_daftar_ulang_ids()
    hasil, lewat = [], []
    for p in urutkan_untuk_cetak(peserta):
        alasan = alasan_tidak_berhak(p, du)
        if alasan:
            lewat.append((p, alasan))
            continue
        hasil.append(_terbitkan(request, f"P:{p.pk}", JenisPiagam.PESERTA, template, data_peserta(p), peserta=p,
                                kontingen=p.kontingen))  # fmt: skip
    return hasil, lewat


def anggota_kegiatan(k: Kontingen, kegiatan: Kegiatan | None) -> list[Peserta]:
    """Anggota kontingen yang mengikuti kegiatan: memilihnya di biodata ATAU tercatat hadir di titik absennya.
    Tanpa kegiatan (misalnya Anjangsana): semua anggota kontingen. Yang tidak berhak piagam dilewati."""
    qs = Peserta.objects.filter(kontingen=k)
    if kegiatan is not None:
        hadir = Kehadiran.objects.filter(titik_absen__kegiatan=kegiatan, peserta__kontingen=k).values("peserta_id")
        qs = qs.filter(Q(kegiatan=kegiatan) | Q(pk__in=hadir)).distinct()
    du = sudah_daftar_ulang_ids(k)
    return [p for p in urutkan_untuk_cetak(qs) if not alasan_tidak_berhak(p, du)]


class Penerima:
    ORANG = "ORANG"  # setiap anggota yang mengikuti kegiatan (bawaan, R15: juara mendapat 2 piagam)
    KONTINGEN = "KONTINGEN"  # satu piagam atas nama kontingen


def terbitkan_juara(
    request, sumber: str, baris: list[dict], template: TemplatePiagam, kegiatan: str,
    kegiatan_obj: Kegiatan | None = None, penerima: str = Penerima.ORANG,
) -> list[PiagamTerbit]:  # fmt: skip
    """`baris`: {"peringkat", "tingkat", "kontingen" | "peserta"} (sudah disaring peringkat <= N).

    Juara kontingen dengan penerima ORANG: setiap anggota yang mengikuti kegiatan mendapat piagam juara atas
    namanya (selain piagam pesertanya). Bila tidak ada anggota yang tercatat, piagam atas nama kontingen."""
    hasil = []
    for b in sorted(baris, key=lambda x: (x["peringkat"], getattr(x.get("kontingen"), "kode", ""))):
        k, p = b.get("kontingen"), b.get("peserta")
        orang = [p] if p else (anggota_kegiatan(k, kegiatan_obj) if penerima == Penerima.ORANG else [])
        for o in orang:
            data = data_juara(b["peringkat"], kegiatan, b["tingkat"], None, o)
            hasil.append(_terbitkan(request, f"J:{sumber}:P{o.pk}"[:80], JenisPiagam.JUARA, template, data,
                                    peserta=o, kontingen=o.kontingen, sumber=sumber, peringkat=b["peringkat"]))  # fmt: skip
        if not orang:
            data = data_juara(b["peringkat"], kegiatan, b["tingkat"], k, None)
            hasil.append(_terbitkan(request, f"J:{sumber}:K{k.pk}"[:80], JenisPiagam.JUARA, template, data,
                                    kontingen=k, sumber=sumber, peringkat=b["peringkat"]))  # fmt: skip
    return hasil


def data_terkini(x: PiagamTerbit) -> dict:
    """Data cetak dari biodata terbaru (nama yang diperbaiki ikut berubah); nomor tetap."""
    if x.jenis == JenisPiagam.PESERTA and x.peserta_id:
        data = data_peserta(x.peserta)
    elif x.jenis == JenisPiagam.JUARA:
        d = x.data or {}
        data = data_juara(x.peringkat or d.get("peringkat") or 1, d.get("kegiatan", ""), d.get("tingkat", ""),
                          None if x.peserta_id else x.kontingen, x.peserta)  # fmt: skip
    else:
        data = dict(x.data or {})
    return {**data, "nomor": x.nomor}


def piagam_kontingen(k: Kontingen, peserta: list[PiagamTerbit]) -> list[PiagamTerbit]:
    """Piagam peserta kontingen + piagam juara anggotanya (setelah piagam peserta masing-masing) + juara
    atas nama kontingen di akhir: satu PDF untuk dibagikan ke kontingen."""
    juara = list(PiagamTerbit.objects.filter(jenis=JenisPiagam.JUARA, kontingen=k).select_related("template",
                                                                                                 "peserta"))  # fmt: skip
    per_orang: dict[int, list[PiagamTerbit]] = {}
    for j in juara:
        if j.peserta_id:
            per_orang.setdefault(j.peserta_id, []).append(j)
    hasil = []
    for x in peserta:
        hasil.append(x)
        hasil += sorted(per_orang.pop(x.peserta_id, []), key=lambda j: j.urut)
    for sisa in per_orang.values():
        hasil += sisa
    return hasil + [j for j in juara if not j.peserta_id]


@transaction.atomic
def atur_berhak(request, p: Peserta, berhak: bool, alasan: str) -> None:
    p.tidak_berhak_piagam = not berhak
    p.alasan_tidak_berhak_piagam = "" if berhak else " ".join(alasan.split())[:255]
    p.save(update_fields=["tidak_berhak_piagam", "alasan_tidak_berhak_piagam", "diubah_pada"])
    catat(request, "piagam.berhak_diubah", p,
          keterangan=f"{p.nama_lengkap}: {'berhak' if berhak else 'tidak berhak (' + p.alasan_tidak_berhak_piagam + ')'}")  # fmt: skip


def pdf_terbit(daftar: list[PiagamTerbit], judul: str) -> bytes:
    from .pdf import buat_pdf

    return buat_pdf([(x.template, data_terkini(x)) for x in daftar], judul)


def waktu() -> str:
    return timezone.localtime().strftime("%Y%m%d-%H%M")
