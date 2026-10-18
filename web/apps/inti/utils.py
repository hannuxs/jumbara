"""Fungsi bantu umum: IP klien di balik proxy, format tanggal Indonesia, kode acak."""

from __future__ import annotations

import ipaddress
import secrets
from datetime import date, datetime

from django.utils import timezone

# Huruf dan angka tanpa yang mudah tertukar (0/O, 1/I/L).
ALFABET_KODE = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"

NAMA_HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
NAMA_BULAN = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]  # fmt: skip


def kode_acak(panjang: int) -> str:
    return "".join(secrets.choice(ALFABET_KODE) for _ in range(panjang))


def _ip_valid(teks: str) -> str | None:
    teks = teks.strip()
    try:
        return str(ipaddress.ip_address(teks))
    except ValueError:
        return None


def _loopback(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip).is_loopback
    except ValueError:
        return False


def ip_klien(request) -> str:
    """IP asli pengunjung.

    Waitress hanya mendengar 127.0.0.1, jadi permintaan selalu datang dari Apache atau
    cloudflared di mesin yang sama. Jika REMOTE_ADDR loopback, percayai CF-Connecting-IP lalu
    entri X-Forwarded-For paling kanan yang bukan loopback (entri kiri bisa dipalsukan klien).
    """
    remote = request.META.get("REMOTE_ADDR", "") or "0.0.0.0"
    if not _loopback(remote):
        return remote
    cf = _ip_valid(request.META.get("HTTP_CF_CONNECTING_IP", ""))
    if cf:
        return cf
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    for bagian in reversed(xff.split(",")):
        ip = _ip_valid(bagian)
        if ip and not _loopback(ip):
            return ip
    return remote


# Dipakai django-ratelimit (RATELIMIT_IP_META_KEY).
ip_klien_meta = ip_klien


def user_agent(request) -> str:
    return request.META.get("HTTP_USER_AGENT", "")[:255]


def tanggal_id(nilai: date | datetime | None, hari: bool = True) -> str:
    """Contoh: 'Senin, 26 Oktober 2026'."""
    if nilai is None:
        return ""
    if isinstance(nilai, datetime):
        nilai = timezone.localtime(nilai) if timezone.is_aware(nilai) else nilai
        nilai_tgl = nilai.date()
    else:
        nilai_tgl = nilai
    teks = f"{nilai_tgl.day} {NAMA_BULAN[nilai_tgl.month - 1]} {nilai_tgl.year}"
    if hari:
        teks = f"{NAMA_HARI[nilai_tgl.weekday()]}, {teks}"
    return teks


def jam_id(nilai: datetime | None) -> str:
    """Contoh: '08.00 WITA'."""
    if nilai is None:
        return ""
    if timezone.is_aware(nilai):
        nilai = timezone.localtime(nilai)
    return f"{nilai:%H.%M} WITA"


def angka_id(nilai: int | float | None) -> str:
    """Angka ribuan dengan titik: 1.000."""
    if nilai is None:
        return ""
    return f"{nilai:,}".replace(",", ".")


def tautan_wa(nomor: str, pesan: str = "") -> str:
    """Tautan WhatsApp dari nomor 62..., kosong jika nomor belum diisi."""
    from urllib.parse import quote

    digit = "".join(c for c in (nomor or "") if c.isdigit())
    if not digit:
        return ""
    if digit.startswith("0"):
        digit = "62" + digit[1:]
    url = f"https://wa.me/{digit}"
    if pesan:
        url += "?text=" + quote(pesan)
    return url
