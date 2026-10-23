"""Filter tampilan form penilaian."""

from __future__ import annotations

from django import template

register = template.Library()

LABEL_BAWAAN = {
    "poin_kehadiran": "Poin hadir",
    "jumlah_hadir": "Hadir",
    "kuota": "Kuota",
    "jumlah_juri": "Juri",
}


@register.filter
def label_bawaan(kode: str) -> str:
    return LABEL_BAWAAN.get(kode, kode)


@register.filter
def angka_tampil(nilai, kolom=None) -> str:
    """Angka dengan koma desimal; jumlah desimal dari pengaturan kolom (bawaan 2)."""
    if nilai is None or nilai == "":
        return "-"
    try:
        nilai = float(nilai)
    except (TypeError, ValueError):
        return str(nilai)
    desimal = 2
    if kolom is not None and hasattr(kolom, "atur"):
        desimal = int(kolom.atur("tampil_desimal", 2) or 0)
    if nilai == int(nilai):
        return f"{int(nilai)}"
    return f"{nilai:.{desimal}f}".replace(".", ",")


@register.filter
def isi_tampil(nilai) -> str:
    if nilai is None or nilai == "":
        return "-"
    if isinstance(nilai, list):
        return ", ".join(map(str, nilai))
    if isinstance(nilai, bool):
        return "Ya" if nilai else "Tidak"
    if isinstance(nilai, dict):
        return nilai.get("nama", "file")
    return str(nilai)
