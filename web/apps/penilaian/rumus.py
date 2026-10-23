"""Mesin rumus form penilaian (docs/16-FORM-BUILDER.md). TANPA eval/exec.

Alur: teks -> `token()` -> `urai()` (recursive descent) -> pohon `Simpul` -> `hitung()`.

Bahasa:
- Angka `12`, `0.25`, `0,25` (koma desimal hanya di luar fungsi; di dalam fungsi `1,2` ditolak karena
  membingungkan: tulis `1.2` untuk desimal, atau `1, 2` untuk dua angka).
- Pemisah argumen fungsi: koma atau titik koma: `MAX(1, 2)`, `MAX(1;2)`.
- Kolom `[kode]`, teks `"..."` (hanya untuk argumen REF/PERINGKAT).
- Operator `+ - * /`, juga `x` dan `×` untuk kali; perbandingan `= <> < <= > >=`.
- Fungsi: SUM AVG MIN MAX ROUND ABS IF COALESCE ISBLANK AND OR NOT REF PERINGKAT POIN_PERINGKAT.

Nilai kosong (`None`): dianggap 0 dalam hitungan (+ - * / perbandingan, SUM), diabaikan oleh AVG/MIN/MAX,
dan bisa diperiksa dengan ISBLANK / COALESCE. Pembagian dengan nol membuat hasil kolom kosong + peringatan.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

BATAS_PANJANG = 2000
BATAS_KEDALAMAN = 60


class GalatRumus(Exception):
    """Galat penulisan rumus (ditampilkan ke superadmin saat menyimpan)."""

    def __init__(self, pesan: str, posisi: int | None = None):
        super().__init__(pesan)
        self.pesan = pesan
        self.posisi = posisi

    def __str__(self) -> str:
        return self.pesan if self.posisi is None else f"{self.pesan} (posisi {self.posisi + 1})"


class BagiNol(Exception):
    """Pembagian dengan nol saat menghitung; kolom menjadi kosong."""


# --- Token --------------------------------------------------------------------------------------------


@dataclass
class Token:
    jenis: str  # ANGKA, TEKS, KOLOM, NAMA, OP, BANDING, KURUNG_BUKA, KURUNG_TUTUP, PISAH, AKHIR
    nilai: object
    posisi: int


_SPASI = re.compile(r"\s+")
_ANGKA = re.compile(r"\d+(?:[.,]\d+)?|\.\d+")
_NAMA = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_KODE_KOLOM = re.compile(r"[a-z][a-z0-9_]{0,39}")


def token(teks: str) -> list[Token]:
    if teks is None or not str(teks).strip():
        raise GalatRumus("Rumus masih kosong.")
    teks = str(teks)
    if len(teks) > BATAS_PANJANG:
        raise GalatRumus(f"Rumus terlalu panjang (maksimal {BATAS_PANJANG} karakter).")
    hasil: list[Token] = []
    kurung_fungsi: list[bool] = []  # True = kurung milik fungsi
    i = 0
    n = len(teks)
    while i < n:
        c = teks[i]
        m = _SPASI.match(teks, i)
        if m:
            i = m.end()
            continue
        if c.isdigit() or (c == "." and i + 1 < n and teks[i + 1].isdigit()):
            m = _ANGKA.match(teks, i)
            if "," in m.group() and any(kurung_fungsi):
                raise GalatRumus(
                    f"'{m.group()}' membingungkan di dalam fungsi: tulis {m.group().replace(',', '.')} untuk angka desimal, "
                    f"atau beri spasi setelah koma ({m.group().replace(',', ', ')}) untuk dua angka.",
                    i,
                )
            hasil.append(Token("ANGKA", float(m.group().replace(",", ".")), i))
            i = m.end()
            continue
        if c == "[":
            tutup = teks.find("]", i)
            if tutup == -1:
                raise GalatRumus("Kurung siku [ belum ditutup ].", i)
            kode = teks[i + 1 : tutup].strip().lower()
            if not _KODE_KOLOM.fullmatch(kode):
                raise GalatRumus(f"Nama kolom [{kode}] tidak valid (huruf kecil, angka, garis bawah).", i)
            hasil.append(Token("KOLOM", kode, i))
            i = tutup + 1
            continue
        if c in "\"'“”":
            akhir_kutip = {'"': '"', "'": "'", "“": "”", "”": "”"}[c]
            tutup = teks.find(akhir_kutip, i + 1)
            if tutup == -1 and c in "“”":
                tutup = teks.find('"', i + 1)
            if tutup == -1:
                raise GalatRumus("Tanda kutip belum ditutup.", i)
            hasil.append(Token("TEKS", teks[i + 1 : tutup], i))
            i = tutup + 1
            continue
        if c.isalpha() or c == "_":
            m = _NAMA.match(teks, i)
            kata = m.group()
            if kata.lower() == "x":
                hasil.append(Token("OP", "*", i))
            else:
                hasil.append(Token("NAMA", kata.upper(), i))
            i = m.end()
            continue
        if c in "+-*/":
            hasil.append(Token("OP", c, i))
            i += 1
            continue
        if c in "×·":
            hasil.append(Token("OP", "*", i))
            i += 1
            continue
        if c == ":" or c == "÷":
            hasil.append(Token("OP", "/", i))
            i += 1
            continue
        if c in "<>=!":
            dua = teks[i : i + 2]
            if dua in ("<=", ">=", "<>", "!=", "=="):
                hasil.append(Token("BANDING", {"!=": "<>", "==": "="}.get(dua, dua), i))
                i += 2
            elif c == "!":
                raise GalatRumus("Tanda ! tidak dikenal. Pakai <> untuk 'tidak sama dengan'.", i)
            else:
                hasil.append(Token("BANDING", c, i))
                i += 1
            continue
        if c == "(":
            kurung_fungsi.append(bool(hasil) and hasil[-1].jenis == "NAMA")
            hasil.append(Token("KURUNG_BUKA", c, i))
            i += 1
            continue
        if c == ")":
            if kurung_fungsi:
                kurung_fungsi.pop()
            hasil.append(Token("KURUNG_TUTUP", c, i))
            i += 1
            continue
        if c in ",;":
            hasil.append(Token("PISAH", c, i))
            i += 1
            continue
        raise GalatRumus(f"Karakter '{c}' tidak dikenal.", i)
    hasil.append(Token("AKHIR", None, n))
    return hasil


# --- Pohon ekspresi ---------------------------------------------------------------------------------


@dataclass
class Simpul:
    jenis: str  # ANGKA, TEKS, KOLOM, NEG, OP, BANDING, FUNGSI
    nilai: object = None
    anak: list[Simpul] = field(default_factory=list)
    posisi: int = 0


FUNGSI = {
    # nama: (minimal argumen, maksimal argumen atau None)
    "SUM": (1, None),
    "AVG": (1, None),
    "AVERAGE": (1, None),
    "MIN": (1, None),
    "MAX": (1, None),
    "ROUND": (1, 2),
    "ABS": (1, 1),
    "IF": (3, 3),
    "COALESCE": (2, None),
    "ISBLANK": (1, 1),
    "AND": (1, None),
    "OR": (1, None),
    "NOT": (1, 1),
    "REF": (2, 3),
    "PERINGKAT": (1, 2),
    "POIN_PERINGKAT": (2, None),
}
NAMA_FUNGSI_INDONESIA = {"JUMLAH": "SUM", "RATA": "AVG", "RATARATA": "AVG", "BULAT": "ROUND", "JIKA": "IF"}


class _Pengurai:
    def __init__(self, daftar: list[Token]):
        self.t = daftar
        self.i = 0
        self.kedalaman = 0

    def lihat(self) -> Token:
        return self.t[self.i]

    def ambil(self) -> Token:
        tk = self.t[self.i]
        self.i += 1
        return tk

    def harap(self, jenis: str, pesan: str) -> Token:
        if self.lihat().jenis != jenis:
            raise GalatRumus(pesan, self.lihat().posisi)
        return self.ambil()

    def ekspresi(self) -> Simpul:
        self.kedalaman += 1
        if self.kedalaman > BATAS_KEDALAMAN:
            raise GalatRumus("Rumus terlalu bertingkat (terlalu banyak kurung).", self.lihat().posisi)
        kiri = self.tambah()
        if self.lihat().jenis == "BANDING":
            op = self.ambil()
            kanan = self.tambah()
            kiri = Simpul("BANDING", op.nilai, [kiri, kanan], op.posisi)
            if self.lihat().jenis == "BANDING":
                raise GalatRumus("Perbandingan berantai tidak didukung. Pakai AND(...).", self.lihat().posisi)
        self.kedalaman -= 1
        return kiri

    def tambah(self) -> Simpul:
        kiri = self.kali()
        while self.lihat().jenis == "OP" and self.lihat().nilai in "+-":
            op = self.ambil()
            kiri = Simpul("OP", op.nilai, [kiri, self.kali()], op.posisi)
        return kiri

    def kali(self) -> Simpul:
        kiri = self.unari()
        while self.lihat().jenis == "OP" and self.lihat().nilai in "*/":
            op = self.ambil()
            kiri = Simpul("OP", op.nilai, [kiri, self.unari()], op.posisi)
        return kiri

    def unari(self) -> Simpul:
        tk = self.lihat()
        if tk.jenis == "OP" and tk.nilai in "+-":
            self.ambil()
            self.kedalaman += 1
            if self.kedalaman > BATAS_KEDALAMAN:
                raise GalatRumus("Terlalu banyak tanda + atau - berturut-turut.", tk.posisi)
            isi = self.unari()
            self.kedalaman -= 1
            return Simpul("NEG", None, [isi], tk.posisi) if tk.nilai == "-" else isi
        return self.utama()

    def utama(self) -> Simpul:
        tk = self.ambil()
        if tk.jenis == "ANGKA":
            return Simpul("ANGKA", tk.nilai, posisi=tk.posisi)
        if tk.jenis == "TEKS":
            return Simpul("TEKS", tk.nilai, posisi=tk.posisi)
        if tk.jenis == "KOLOM":
            return Simpul("KOLOM", tk.nilai, posisi=tk.posisi)
        if tk.jenis == "KURUNG_BUKA":
            isi = self.ekspresi()
            self.harap("KURUNG_TUTUP", "Kurung ( belum ditutup ).")
            return isi
        if tk.jenis == "NAMA":
            nama = NAMA_FUNGSI_INDONESIA.get(tk.nilai, tk.nilai)
            if nama == "AVERAGE":
                nama = "AVG"
            if nama not in FUNGSI:
                if self.lihat().jenis == "KURUNG_BUKA":
                    raise GalatRumus(f"Fungsi {tk.nilai} tidak dikenal.", tk.posisi)
                raise GalatRumus(
                    f"Kata '{tk.nilai}' tidak dikenal. Kolom ditulis dalam kurung siku, misalnya [{tk.nilai.lower()}].",
                    tk.posisi,
                )
            self.harap("KURUNG_BUKA", f"Setelah {nama} harus ada kurung (.")
            if nama == "REF" and self.lihat().jenis in ("NAMA", "KOLOM"):
                raise GalatRumus(
                    'REF ditulis dengan tanda kutip, misalnya REF("slug-form", "kode_kolom").', self.lihat().posisi
                )
            argumen: list[Simpul] = []
            if self.lihat().jenis != "KURUNG_TUTUP":
                argumen.append(self.ekspresi())
                while self.lihat().jenis == "PISAH":
                    self.ambil()
                    argumen.append(self.ekspresi())
            self.harap("KURUNG_TUTUP", f"Kurung fungsi {nama} belum ditutup ) atau pemisah argumen kurang.")
            minimal, maksimal = FUNGSI[nama]
            if len(argumen) < minimal or (maksimal is not None and len(argumen) > maksimal):
                jumlah = (
                    f"{minimal}"
                    if minimal == maksimal
                    else f"{minimal} sampai {maksimal}"
                    if maksimal
                    else f"minimal {minimal}"
                )
                raise GalatRumus(f"Fungsi {nama} butuh {jumlah} argumen, tertulis {len(argumen)}.", tk.posisi)
            simpul = Simpul("FUNGSI", nama, argumen, tk.posisi)
            _cek_argumen(simpul)
            return simpul
        if tk.jenis == "AKHIR":
            raise GalatRumus("Rumus berakhir terlalu cepat (ada yang kurang di akhir).", tk.posisi)
        if tk.jenis == "KURUNG_TUTUP":
            raise GalatRumus("Ada kurung ) yang tidak berpasangan atau isi kurung kosong.", tk.posisi)
        if tk.jenis == "PISAH":
            raise GalatRumus("Tanda koma/titik koma di tempat yang salah.", tk.posisi)
        raise GalatRumus(f"Tanda '{tk.nilai}' di tempat yang salah.", tk.posisi)


def _cek_argumen(s: Simpul) -> None:
    nama = s.nilai
    if nama == "REF":
        for a in s.anak:
            if a.jenis != "TEKS":
                raise GalatRumus('REF ditulis dengan tanda kutip, misalnya REF("slug-form", "kode_kolom").', a.posisi)
        if len(s.anak) == 3 and s.anak[2].nilai.upper() not in ("TINGKAT_INI",):
            raise GalatRumus('Argumen ketiga REF hanya boleh "TINGKAT_INI".', s.anak[2].posisi)
    elif nama == "PERINGKAT":
        if s.anak[0].jenis != "KOLOM":
            raise GalatRumus("PERINGKAT butuh kolom, misalnya PERINGKAT([nilai_akhir]).", s.anak[0].posisi)
        if len(s.anak) == 2 and (s.anak[1].jenis != "TEKS" or s.anak[1].nilai.upper() not in ("NAIK", "TURUN")):
            raise GalatRumus(
                'Arah PERINGKAT hanya "TURUN" (terbesar juara) atau "NAIK" (terkecil juara).', s.anak[1].posisi
            )
    else:
        for a in s.anak:
            if a.jenis == "TEKS":
                raise GalatRumus(f"Teks dalam kutip tidak bisa dipakai di fungsi {nama}.", a.posisi)


def urai(teks: str) -> Simpul:
    p = _Pengurai(token(teks))
    hasil = p.ekspresi()
    sisa = p.lihat()
    if sisa.jenis != "AKHIR":
        if sisa.jenis == "KURUNG_TUTUP":
            raise GalatRumus("Ada kurung ) yang tidak berpasangan.", sisa.posisi)
        if sisa.jenis == "PISAH":
            raise GalatRumus(
                "Koma di luar fungsi. Untuk angka desimal tulis 0,25 tanpa spasi atau pakai titik (0.25).", sisa.posisi
            )
        raise GalatRumus("Ada yang kurang di antara dua bagian rumus (misalnya tanda + atau *).", sisa.posisi)
    if hasil.jenis == "TEKS":
        raise GalatRumus("Rumus tidak boleh hanya berisi teks.")
    return hasil


# --- Analisis ---------------------------------------------------------------------------------------


@dataclass
class Rujukan:
    kolom: set[str] = field(default_factory=set)  # [kode] di form yang sama (termasuk di dalam PERINGKAT)
    ref: list[tuple[str, str, bool]] = field(default_factory=list)  # (slug, kode, tingkat_ini)


def rujukan(simpul: Simpul) -> Rujukan:
    r = Rujukan()

    def jalan(s: Simpul) -> None:
        if s.jenis == "KOLOM":
            r.kolom.add(s.nilai)
        elif s.jenis == "FUNGSI" and s.nilai == "REF":
            r.ref.append((s.anak[0].nilai.strip(), s.anak[1].nilai.strip().lower(), len(s.anak) == 3))
            return
        for a in s.anak:
            jalan(a)

    jalan(simpul)
    return r


def urutan_hitung(rumus_per_kolom: dict[str, set[str]]) -> list[str]:
    """Urutan topologis kolom rumus. Galat bila ada rumus melingkar (A memakai B, B memakai A)."""
    hasil: list[str] = []
    status: dict[str, int] = {}  # 1 = sedang dikunjungi, 2 = selesai

    def kunjungi(kode: str, jalur: list[str]) -> None:
        if status.get(kode) == 2:
            return
        if status.get(kode) == 1:
            putaran = jalur[jalur.index(kode) :] + [kode]
            raise GalatRumus("Rumus melingkar: " + " -> ".join(f"[{k}]" for k in putaran))
        status[kode] = 1
        for dep in sorted(rumus_per_kolom.get(kode, ())):
            if dep in rumus_per_kolom:
                kunjungi(dep, [*jalur, kode])
        status[kode] = 2
        hasil.append(kode)

    for kode in rumus_per_kolom:
        kunjungi(kode, [])
    return hasil


# --- Hitung -----------------------------------------------------------------------------------------


Angka = float | None


@dataclass
class Konteks:
    """Yang dibutuhkan evaluator untuk SATU subjek."""

    nilai: Callable[[str], Angka]  # nilai kolom form ini untuk subjek ini
    ref: Callable[[str, str, bool], Angka] = lambda slug, kode, ti: None  # noqa: E731
    peringkat: Callable[[str, bool], Angka] = lambda kode, naik: None  # noqa: E731
    peringatan: list[str] = field(default_factory=list)


def _angka(v) -> float:
    return 0.0 if v is None else float(v)


def _benar(v) -> bool:
    return v is not None and v != 0


def _bulat(x: float, desimal: int) -> float:
    q = Decimal(1).scaleb(-desimal)
    return float(Decimal(repr(x)).quantize(q, rounding=ROUND_HALF_UP))


def hitung(s: Simpul, k: Konteks) -> Angka:
    j = s.jenis
    if j == "ANGKA":
        return s.nilai
    if j == "KOLOM":
        v = k.nilai(s.nilai)
        return None if v is None else float(v)
    if j == "NEG":
        v = hitung(s.anak[0], k)
        return None if v is None else -v
    if j == "OP":
        a = _angka(hitung(s.anak[0], k))
        b = _angka(hitung(s.anak[1], k))
        if s.nilai == "+":
            return a + b
        if s.nilai == "-":
            return a - b
        if s.nilai == "*":
            return a * b
        if b == 0:
            raise BagiNol()
        return a / b
    if j == "BANDING":
        a = _angka(hitung(s.anak[0], k))
        b = _angka(hitung(s.anak[1], k))
        hasil = {
            "=": math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9),
            "<>": not math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9),
            "<": a < b,
            "<=": a <= b,
            ">": a > b,
            ">=": a >= b,
        }[s.nilai]
        return 1.0 if hasil else 0.0
    if j == "FUNGSI":
        return _fungsi(s, k)
    raise GalatRumus("Bagian rumus tidak bisa dihitung.", s.posisi)


def _fungsi(s: Simpul, k: Konteks) -> Angka:
    nama = s.nilai
    if nama == "IF":
        return hitung(s.anak[1], k) if _benar(hitung(s.anak[0], k)) else hitung(s.anak[2], k)
    if nama == "REF":
        return k.ref(s.anak[0].nilai.strip(), s.anak[1].nilai.strip().lower(), len(s.anak) == 3)
    if nama == "PERINGKAT":
        naik = len(s.anak) == 2 and s.anak[1].nilai.upper() == "NAIK"
        return k.peringkat(s.anak[0].nilai, naik)
    if nama == "COALESCE":
        for a in s.anak:
            v = hitung(a, k)
            if v is not None:
                return v
        return None
    if nama == "ISBLANK":
        return 1.0 if hitung(s.anak[0], k) is None else 0.0
    if nama == "AND":
        return 1.0 if all(_benar(hitung(a, k)) for a in s.anak) else 0.0
    if nama == "OR":
        return 1.0 if any(_benar(hitung(a, k)) for a in s.anak) else 0.0
    if nama == "NOT":
        return 0.0 if _benar(hitung(s.anak[0], k)) else 1.0
    nilai = [hitung(a, k) for a in s.anak]
    if nama == "SUM":
        return sum(_angka(v) for v in nilai)
    isi = [v for v in nilai if v is not None]
    if nama == "AVG":
        return sum(isi) / len(isi) if isi else None
    if nama == "MIN":
        return min(isi) if isi else None
    if nama == "MAX":
        return max(isi) if isi else None
    if nama == "ABS":
        return None if nilai[0] is None else abs(nilai[0])
    if nama == "ROUND":
        if nilai[0] is None:
            return None
        desimal = int(_angka(nilai[1])) if len(nilai) == 2 else 0
        return _bulat(nilai[0], max(-6, min(10, desimal)))
    if nama == "POIN_PERINGKAT":
        p = nilai[0]
        if p is None or p != int(p) or p < 1:
            return 0.0
        poin = nilai[1:]
        return _angka(poin[int(p) - 1]) if int(p) <= len(poin) else 0.0
    raise GalatRumus(f"Fungsi {nama} tidak dikenal.", s.posisi)


def hitung_aman(s: Simpul, k: Konteks, kode_kolom: str = "") -> Angka:
    """Hitung satu kolom untuk satu subjek; bagi nol -> kosong + peringatan."""
    try:
        v = hitung(s, k)
    except BagiNol:
        k.peringatan.append(f"Pembagian dengan nol di kolom [{kode_kolom}]; hasil dikosongkan.")
        return None
    except (OverflowError, ValueError):
        k.peringatan.append(f"Angka di kolom [{kode_kolom}] terlalu besar; hasil dikosongkan.")
        return None
    if v is not None and (math.isnan(v) or math.isinf(v)):
        return None
    return v
