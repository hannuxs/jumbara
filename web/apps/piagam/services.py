"""Penerbitan piagam: template bawaan, unggah latar, syarat berhak, nomor, data cetak."""

from __future__ import annotations

import io
import uuid
from datetime import date
from pathlib import Path

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from PIL import Image, UnidentifiedImageError

from apps.absensi.models import Kehadiran
from apps.absensi.rekap import KODE_DAFTAR_ULANG
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


def elemen_bawaan(jenis: str) -> list[dict]:
    """Tata letak awal untuk A4 mendatar (297 x 210 mm), cocok dengan desain bawaan."""
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


def pastikan_template_bawaan() -> list[TemplatePiagam]:
    """Buat template bawaan (peserta dan juara) bila belum ada sama sekali."""
    dibuat = []
    for jenis, nama in (
        (JenisPiagam.PESERTA, "Piagam peserta (desain bawaan)"),
        (JenisPiagam.JUARA, "Piagam juara (desain bawaan)"),
    ):
        if not TemplatePiagam.objects.filter(jenis=jenis).exists():
            dibuat.append(
                TemplatePiagam.objects.create(
                    nama=nama, jenis=jenis, elemen=elemen_bawaan(jenis), logo_y=17, logo_tinggi=20
                )
            )
    return dibuat


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
    }


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
        "tingkat": p.get_tingkat_display(),
    }  # fmt: skip


ROMAWI = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]


def data_juara(
    peringkat: int, kegiatan: str, tingkat: str, kontingen: Kontingen | None, peserta: Peserta | None
) -> dict:
    nama = peserta.nama_lengkap if peserta else f"Kontingen {kontingen.nama}" if kontingen else ""
    return {
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
            "nomor": nomor_dari_format(JenisPiagam(jenis), 123)}  # fmt: skip
    if jenis == JenisPiagam.JUARA:
        data.update(data_juara(1, "Wahana Kepalangmerahan - Voli Tutup Terpal", "Madya", None, None))
        data["nama"] = f"Kontingen {kontingen}"
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


def terbitkan_juara(
    request, sumber: str, baris: list[dict], template: TemplatePiagam, kegiatan: str
) -> list[PiagamTerbit]:
    """`baris`: {"peringkat", "tingkat", "kontingen" | "peserta"} (sudah disaring peringkat <= N)."""
    hasil = []
    for b in sorted(baris, key=lambda x: (x["peringkat"], getattr(x.get("kontingen"), "kode", ""))):
        k, p = b.get("kontingen"), b.get("peserta")
        subjek = f"P{p.pk}" if p else f"K{k.pk}"
        data = data_juara(b["peringkat"], kegiatan, b["tingkat"], k, p)
        hasil.append(_terbitkan(request, f"J:{sumber}:{subjek}"[:80], JenisPiagam.JUARA, template, data,
                                peserta=p, kontingen=k or (p.kontingen if p else None), sumber=sumber,
                                peringkat=b["peringkat"]))  # fmt: skip
    return hasil


@transaction.atomic
def atur_berhak(request, p: Peserta, berhak: bool, alasan: str) -> None:
    p.tidak_berhak_piagam = not berhak
    p.alasan_tidak_berhak_piagam = "" if berhak else " ".join(alasan.split())[:255]
    p.save(update_fields=["tidak_berhak_piagam", "alasan_tidak_berhak_piagam", "diubah_pada"])
    catat(request, "piagam.berhak_diubah", p,
          keterangan=f"{p.nama_lengkap}: {'berhak' if berhak else 'tidak berhak (' + p.alasan_tidak_berhak_piagam + ')'}")  # fmt: skip


def pdf_terbit(daftar: list[PiagamTerbit], judul: str) -> bytes:
    from .pdf import buat_pdf

    return buat_pdf([(x.template, x.data) for x in daftar], judul)


def waktu() -> str:
    return timezone.localtime().strftime("%Y%m%d-%H%M")
