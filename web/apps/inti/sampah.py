"""Tempat sampah umum untuk data soft delete selain biodata dan kontingen:
form, kiriman form, kehadiran yang dibatalkan, dan review Anjangsana."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.db.models import Model, QuerySet

from apps.inti.log import catat


class GagalSampah(Exception):
    def __init__(self, pesan: str):
        super().__init__(pesan)
        self.pesan = pesan


@dataclass
class JenisSampah:
    kode: str
    judul: str
    qs: Callable[[], QuerySet]
    label: Callable[[Model], str]
    keterangan: Callable[[Model], str]
    cek_pulihkan: Callable[[Model], None] = lambda o: None  # noqa: E731
    cek_hapus: Callable[[Model], None] = lambda o: None  # noqa: E731
    sebelum_hapus: Callable[[Model], None] = lambda o: None  # noqa: E731


def _jenis() -> dict[str, JenisSampah]:
    from apps.absensi.models import Kehadiran
    from apps.anjangsana.models import Review
    from apps.penilaian.models import Formulir, Kiriman

    def cek_kiriman(x: Kiriman) -> None:
        if x.formulir.terhapus:
            raise GagalSampah(f'Form "{x.formulir.judul}" ada di tempat sampah. Pulihkan form-nya dulu.')
        sama = Kiriman.objects.filter(formulir=x.formulir, kontingen=x.kontingen_id, peserta=x.peserta_id)
        if x.formulir.penilaian and any(k.nama_pengisi.casefold() == x.nama_pengisi.casefold() for k in sama):
            raise GagalSampah(
                f"{x.nama_pengisi} sudah punya kiriman aktif untuk subjek ini. Hapus yang aktif dulu bila ingin memulihkan."
            )

    def cek_hapus_form(f: Formulir) -> None:
        if Kiriman.semua.filter(formulir=f).exists():
            raise GagalSampah(
                "Form ini masih punya kiriman. Pulihkan form untuk melihat/mengunduh kiriman, atau hapus permanen kirimannya dulu."
            )

    def hapus_berkas(x: Kiriman) -> None:
        from apps.penilaian.services import path_berkas

        for v in (x.data or {}).values():
            if isinstance(v, dict) and "file" in v and (p := path_berkas(x.formulir, v["file"])):
                p.unlink(missing_ok=True)

    return {
        "form": JenisSampah(
            "form", "Form dan penilaian",
            lambda: Formulir.semua.filter(dihapus_pada__isnull=False).order_by("-dihapus_pada"),
            lambda f: f.judul, lambda f: f"{f.slug} · {f.get_mode_display()} · {f.get_tingkat_display()}",
            cek_hapus=cek_hapus_form,
        ),
        "kiriman": JenisSampah(
            "kiriman", "Kiriman form",
            lambda: Kiriman.semua.filter(dihapus_pada__isnull=False).select_related("formulir", "kontingen", "peserta").order_by("-dihapus_pada"),
            lambda x: f"{x.nama_pengisi or '(tanpa nama)'} · {x.formulir.judul}",
            lambda x: (x.kontingen.nama if x.kontingen_id else x.peserta.nama_lengkap if x.peserta_id else "") + f" · dikirim {x.dikirim_pada:%d/%m %H.%M}",
            cek_pulihkan=cek_kiriman, sebelum_hapus=hapus_berkas,
        ),
        "kehadiran": JenisSampah(
            "kehadiran", "Kehadiran yang dibatalkan",
            lambda: Kehadiran.semua.filter(dihapus_pada__isnull=False).select_related("peserta__kontingen", "titik_absen").order_by("-dihapus_pada"),
            lambda k: f"{k.peserta.nama_lengkap} · {k.titik_absen.kode}",
            lambda k: f"{k.peserta.kontingen.nama} · {k.titik_absen.nama_tampil} · dipindai {k.nama_pemindai}",
        ),
        "review": JenisSampah(
            "review", "Review Anjangsana",
            lambda: Review.semua.filter(dihapus_pada__isnull=False).select_related("kontingen_tamu", "kontingen_tuan_rumah").order_by("-dihapus_pada"),
            lambda r: f"{r.kontingen_tamu.nama} → {r.kontingen_tuan_rumah.nama}",
            lambda r: f"Nilai {r.nilai_pengetahuan}/{r.nilai_keterampilan}/{r.nilai_sikap}" + (f" · {r.komentar[:60]}" if r.komentar else ""),
        ),
    }  # fmt: skip


PESAN_BENTROK = {
    "form": "Slug form sudah dipakai form lain yang aktif. Ubah slug form aktif itu dulu.",
    "kehadiran": "Orang ini sudah tercatat hadir lagi di titik yang sama.",
    "review": "Kontingen tamu ini sudah punya review aktif untuk tuan rumah yang sama.",
    "kiriman": "Kiriman bentrok dengan data aktif.",
}


def daftar() -> list[dict]:
    return [{"j": j, "isi": list(j.qs()[:200])} for j in _jenis().values()]


def ambil(jenis: str, pk: int) -> tuple[JenisSampah, Model]:
    j = _jenis().get(jenis)
    if j is None:
        raise GagalSampah("Jenis data tidak dikenal.")
    obj = j.qs().filter(pk=pk).first()
    if obj is None:
        raise GagalSampah("Data tidak ada di tempat sampah.")
    return j, obj


def pulihkan(request, jenis: str, pk: int) -> str:
    j, obj = ambil(jenis, pk)
    j.cek_pulihkan(obj)
    label = j.label(obj)
    try:
        with transaction.atomic():
            obj.pulihkan()
            catat(request, f"sampah.{jenis}_dipulihkan", obj, keterangan=label[:255])
    except IntegrityError:
        raise GagalSampah(PESAN_BENTROK.get(jenis, "Bentrok dengan data aktif.")) from None
    return label


def hapus_permanen(request, jenis: str, pk: int) -> str:
    j, obj = ambil(jenis, pk)
    j.cek_hapus(obj)
    label = j.label(obj)
    with transaction.atomic():
        catat(request, f"sampah.{jenis}_dihapus_permanen", obj, keterangan=label[:255])
        j.sebelum_hapus(obj)
        obj.delete()
    return label
