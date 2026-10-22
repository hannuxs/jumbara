"""Token QR kartu peserta (SJP:) dan QR kontingen (SJK:).

Token = 26 karakter acak dari 31 huruf/angka yang tidak membingungkan (tanpa 0/O, 1/I/L),
setara sekitar 128,8 bit entropi. QR hanya berisi awalan + token: tanpa NIK, nama, atau ID database.
`kode_kartu` = 8 karakter pertama token, ditulis `XXXX-XXXX` di bawah QR untuk diketik manual.
"""

from __future__ import annotations

import re
import secrets

from apps.inti.utils import ALFABET_KODE

PANJANG_TOKEN = 26
AWALAN_PESERTA = "SJP:"
AWALAN_KONTINGEN = "SJK:"


def token_acak() -> str:
    return "".join(secrets.choice(ALFABET_KODE) for _ in range(PANJANG_TOKEN))


def kode_dari_token(token: str) -> str:
    """Contoh: token 'K7Q2M4XA...' -> 'K7Q2-M4XA'."""
    return f"{token[:4]}-{token[4:8]}"


def isi_qr_peserta(token: str) -> str:
    return AWALAN_PESERTA + token


def isi_qr_kontingen(token: str) -> str:
    return AWALAN_KONTINGEN + token


POLA_TOKEN = re.compile(rf"^[{ALFABET_KODE}]{{{PANJANG_TOKEN}}}$")
POLA_KODE = re.compile(rf"^[{ALFABET_KODE}]{{8}}$")


def baca_qr(teks: str) -> tuple[str, str]:
    """Kenali isi QR atau kode yang diketik.

    Mengembalikan (jenis, nilai): ("PESERTA", token), ("KONTINGEN", token), ("KODE", "XXXX-XXXX"),
    atau ("ASING", "") bila bukan QR/kode SIGAP.
    """
    teks = (teks or "").strip()
    besar = teks.upper()
    if besar.startswith(AWALAN_PESERTA) and POLA_TOKEN.match(besar[4:]):
        return "PESERTA", besar[4:]
    if besar.startswith(AWALAN_KONTINGEN) and POLA_TOKEN.match(besar[4:]):
        return "KONTINGEN", besar[4:]
    # Kode tidak memakai 0/O/1/I/L, jadi kode ketikan cukup dibuang spasi dan tanda hubungnya.
    polos = re.sub(r"[\s\-]", "", besar)
    if POLA_KODE.match(polos):
        return "KODE", kode_dari_token(polos)
    return "ASING", ""
