"""Logika kartu peserta dan QR kontingen (Tahap 2)."""

from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from apps.biodata.models import Peran, Peserta
from apps.inti import pengaturan
from apps.inti.log import catat
from apps.kontingen.models import Kontingen

from . import token as tk
from .models import KartuRiwayat

# Urutan kartu dalam satu kontingen (docs/13-KARTU-QR.md).
URUTAN_PERAN = {
    Peran.PIMPINAN_KONTINGEN: 0,
    Peran.PEMBINA_PENDAMPING: 1,
    Peran.PESERTA: 2,
    Peran.PENINJAU: 3,
}

# Isian yang tercetak di kartu: bila berubah setelah data dikunci, kartu perlu dicetak ulang.
ISIAN_TERCETAK = ("nama_lengkap", "peran", "kontingen_id", "tingkat", "foto_path")


# --- Token --------------------------------------------------------------------


def _token_peserta_unik() -> str:
    for _ in range(50):
        t = tk.token_acak()
        kode = tk.kode_dari_token(t)
        if (
            not Peserta.semua.filter(qr_token=t).exists()
            and not Peserta.semua.filter(kode_kartu=kode).exists()
            and not KartuRiwayat.objects.filter(qr_token_lama=t).exists()
            and not KartuRiwayat.objects.filter(kode_kartu_lama=kode).exists()
        ):
            return t
    raise RuntimeError("Gagal membuat token kartu unik")


def pasang_token(peserta: Peserta) -> None:
    """Isi qr_token dan kode_kartu (belum disimpan). Dipanggil saat biodata dibuat."""
    t = _token_peserta_unik()
    peserta.qr_token = t
    peserta.kode_kartu = tk.kode_dari_token(t)


def pasang_token_kontingen(kontingen: Kontingen) -> None:
    for _ in range(50):
        t = tk.token_acak()
        if not Kontingen.semua.filter(qr_token=t).exists():
            kontingen.qr_token = t
            kontingen.qr_token_dibuat_pada = timezone.now()
            return
    raise RuntimeError("Gagal membuat token kontingen unik")


def lengkapi_token() -> tuple[int, int]:
    """Isi token yang masih kosong (biodata/kontingen lama). Mengembalikan (peserta, kontingen)."""
    n_p = n_k = 0
    for p in Peserta.semua.filter(qr_token__isnull=True):
        pasang_token(p)
        p.save(update_fields=["qr_token", "kode_kartu"])
        n_p += 1
    for k in Kontingen.semua.filter(qr_token__isnull=True):
        pasang_token_kontingen(k)
        k.save(update_fields=["qr_token", "qr_token_dibuat_pada"])
        n_k += 1
    return n_p, n_k


# --- Kunci data -----------------------------------------------------------------


def data_terkunci() -> bool:
    return bool(pengaturan.ambil("biodata.terkunci"))


def atur_kunci(request, kunci: bool) -> None:
    """Kunci data biodata sebelum cetak massal: form publik tertutup, perubahan ditandai cetak ulang."""
    pengaturan.simpan("biodata.terkunci", kunci, getattr(request, "nama_pelaku", "") or request.user.username)
    catat(
        request,
        "biodata.dikunci" if kunci else "biodata.kunci_dibuka",
        keterangan="Data biodata dikunci untuk cetak kartu; form publik tertutup"
        if kunci
        else "Kunci data biodata dibuka; form publik kembali mengikuti jadwal",
    )


def perlu_cetak_ulang_karena_ubah(lama: dict, peserta: Peserta) -> bool:
    """True bila data dikunci dan isian yang tercetak di kartu berubah."""
    if not data_terkunci():
        return False
    return any(lama.get(f) != getattr(peserta, f) for f in ISIAN_TERCETAK)


def potret_isian_tercetak(peserta: Peserta) -> dict:
    return {f: getattr(peserta, f) for f in ISIAN_TERCETAK}


# --- Kartu satu orang --------------------------------------------------------------


def _pelaku(request) -> str:
    return (getattr(request, "nama_pelaku", "") or request.user.username)[:100]


@transaction.atomic
def terbitkan_ulang(request, peserta: Peserta, alasan: str) -> Peserta:
    """Kartu hilang/rusak: token lama masuk riwayat (dipindai -> merah), token baru dibuat."""
    peserta = Peserta.objects.select_for_update().get(pk=peserta.pk)
    lama_kode = peserta.kode_kartu or ""
    if peserta.qr_token:
        KartuRiwayat.objects.create(
            peserta=peserta,
            versi=peserta.versi_kartu,
            qr_token_lama=peserta.qr_token,
            kode_kartu_lama=lama_kode,
            alasan=alasan,
            oleh=_pelaku(request),
        )
    pasang_token(peserta)
    peserta.versi_kartu += 1
    peserta.kartu_aktif = True
    peserta.perlu_cetak_ulang = True
    peserta.save(
        update_fields=["qr_token", "kode_kartu", "versi_kartu", "kartu_aktif", "perlu_cetak_ulang", "diubah_pada"]
    )
    catat(
        request,
        "kartu.diterbitkan_ulang",
        peserta,
        keterangan=f"{peserta.kode_pendaftaran}: kartu {lama_kode} dinonaktifkan ({alasan}), kartu baru {peserta.kode_kartu} versi {peserta.versi_kartu}",
    )
    return peserta


def atur_aktif(request, peserta: Peserta, aktif: bool) -> None:
    """Nonaktifkan kartu tanpa menerbitkan baru (misalnya orang batal ikut), atau aktifkan lagi."""
    peserta.kartu_aktif = aktif
    peserta.save(update_fields=["kartu_aktif", "diubah_pada"])
    catat(
        request,
        "kartu.diaktifkan" if aktif else "kartu.dinonaktifkan",
        peserta,
        keterangan=f"{peserta.kode_pendaftaran}: kartu {peserta.kode_kartu} {'diaktifkan' if aktif else 'dinonaktifkan'}",
    )


def tandai_tercetak(request, qs, keterangan: str) -> int:
    """Hapus tanda perlu_cetak_ulang setelah kartu benar-benar dicetak ulang."""
    jumlah = qs.filter(perlu_cetak_ulang=True).update(perlu_cetak_ulang=False)
    if jumlah:
        catat(
            request,
            "kartu.ditandai_tercetak",
            keterangan=f"{jumlah} kartu ditandai sudah dicetak ulang ({keterangan})"[:255],
        )
    return jumlah


@transaction.atomic
def ganti_qr_kontingen(request, kontingen: Kontingen) -> Kontingen:
    kontingen = Kontingen.objects.select_for_update().get(pk=kontingen.pk)
    pasang_token_kontingen(kontingen)
    kontingen.save(update_fields=["qr_token", "qr_token_dibuat_pada", "diubah_pada"])
    catat(
        request,
        "kontingen.qr_diganti",
        kontingen,
        keterangan=f"QR kontingen {kontingen.kode} diganti; QR lama tidak berlaku",
    )
    return kontingen


# --- Urutan cetak --------------------------------------------------------------------


def urutkan_untuk_cetak(peserta) -> list[Peserta]:
    """Pimpinan Kontingen, Pembina Pendamping, Peserta (urut nama), Peninjau."""
    return sorted(peserta, key=lambda p: (URUTAN_PERAN.get(p.peran, 9), p.nama_lengkap.upper(), p.pk))


# --- Mengenali kartu dari isi QR (dipakai pemindai di Tahap 3) ---------------------------


@dataclass
class HasilKartu:
    kode: str  # BERHASIL, KARTU_NONAKTIF, KARTU_TIDAK_DIKENAL, BUKAN_KARTU_PESERTA, QR_ASING
    pesan: str
    peserta: Peserta | None = None
    kontingen: Kontingen | None = None


def kenali(teks: str) -> HasilKartu:
    jenis, nilai = tk.baca_qr(teks)
    if jenis == "KONTINGEN":
        k = Kontingen.objects.filter(qr_token=nilai).first()
        return HasilKartu("BUKAN_KARTU_PESERTA", "Ini QR kontingen, bukan kartu peserta.", kontingen=k)
    if jenis == "ASING":
        return HasilKartu("QR_ASING", "Ini bukan kartu SIGAP JUMBARA.")
    if jenis == "PESERTA":
        p = Peserta.objects.select_related("kontingen").filter(qr_token=nilai).first()
        lama = None if p else KartuRiwayat.objects.filter(qr_token_lama=nilai).first()
    else:
        p = Peserta.objects.select_related("kontingen").filter(kode_kartu=nilai).first()
        lama = None if p else KartuRiwayat.objects.filter(kode_kartu_lama=nilai).first()
    if p is None and lama is not None:
        return HasilKartu("KARTU_NONAKTIF", "Kartu sudah dinonaktifkan. Gunakan kartu terbaru.", peserta=lama.peserta)
    if p is None:
        return HasilKartu("KARTU_TIDAK_DIKENAL", "Kartu tidak dikenal.")
    if not p.kartu_aktif:
        return HasilKartu("KARTU_NONAKTIF", "Kartu sudah dinonaktifkan. Hubungi superadmin.", peserta=p)
    return HasilKartu("BERHASIL", "Kartu dikenali.", peserta=p, kontingen=p.kontingen)
