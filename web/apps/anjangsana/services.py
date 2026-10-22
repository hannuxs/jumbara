"""Anjangsana (docs/17-ANJANGSANA.md): sesi, alur kunjungan, review, peringkat.

Alur publik tanpa login memakai "tiket" bertanda tangan (django.core.signing) agar server tidak
perlu menyimpan sesi untuk pengunjung:
  - tiket identitas: peserta pengunjung (berlaku 30 menit, untuk "Kunjungi kontingen lain"),
  - tiket kunjungan: kunjungan yang sudah tercatat (berlaku 60 menit, untuk mengirim review).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.core import signing
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, F
from django.utils import timezone

from apps.biodata.models import Peserta
from apps.inti import pengaturan
from apps.inti.log import catat
from apps.inti.pengaturan import StatusPaksa
from apps.inti.utils import ip_klien, user_agent
from apps.kartu import token as tk
from apps.kartu.services import kenali
from apps.kontingen.models import Kontingen

from .models import Kunjungan, Review, SesiAnjangsana

GARAM_IDENTITAS = "sigap.anjangsana.identitas"
GARAM_KUNJUNGAN = "sigap.anjangsana.kunjungan"
UMUR_IDENTITAS = 30 * 60
UMUR_KUNJUNGAN = 60 * 60
BATAS_KUNJUNGAN_PER_JAM = 30  # per kartu, mencegah iseng

ASPEK = {
    "pengetahuan": "Pemahaman isu remaja yang dikampanyekan.",
    "keterampilan": "Pengemasan kampanye, suasana kontingen yang nyaman, bersih, dan rapi.",
    "sikap": "Kerja sama tim, keaktifan, cara menyambut tamu.",
}


class GagalAnjangsana(Exception):
    def __init__(self, kode: str, pesan: str, status: int = 400):
        super().__init__(pesan)
        self.kode = kode
        self.pesan = pesan
        self.status = status


# --- Sesi ------------------------------------------------------------------------


def _waktu(sesi: SesiAnjangsana) -> tuple[datetime, datetime]:
    tz = timezone.get_current_timezone()
    return (
        timezone.make_aware(datetime.combine(sesi.tanggal, sesi.mulai), tz),
        timezone.make_aware(datetime.combine(sesi.tanggal, sesi.selesai), tz),
    )


def sesi_berlangsung(pada: datetime | None = None) -> SesiAnjangsana | None:
    pada = pada or timezone.now()
    for s in SesiAnjangsana.objects.filter(tanggal=timezone.localdate(pada)):
        mulai, selesai = _waktu(s)
        if mulai <= pada <= selesai:
            return s
    return None


def sesi_berikutnya(pada: datetime | None = None) -> SesiAnjangsana | None:
    pada = pada or timezone.now()
    for s in SesiAnjangsana.objects.filter(tanggal__gte=timezone.localdate(pada)).order_by("tanggal", "mulai"):
        if _waktu(s)[0] > pada:
            return s
    return None


@dataclass
class StatusAnjangsana:
    terbuka: bool
    sesi: SesiAnjangsana | None
    berikutnya: SesiAnjangsana | None
    paksa: str


def status(pada: datetime | None = None) -> StatusAnjangsana:
    paksa = pengaturan.ambil("anjangsana.paksa_status") or StatusPaksa.OTOMATIS
    sesi = sesi_berlangsung(pada)
    berikutnya = sesi_berikutnya(pada)
    if paksa == StatusPaksa.BUKA:
        return StatusAnjangsana(True, sesi, berikutnya, paksa)
    if paksa == StatusPaksa.TUTUP:
        return StatusAnjangsana(False, None, berikutnya, paksa)
    return StatusAnjangsana(sesi is not None, sesi, berikutnya, paksa)


def wajib_terbuka() -> StatusAnjangsana:
    st = status()
    if not st.terbuka:
        raise GagalAnjangsana("TIDAK_BERLANGSUNG", "Anjangsana sedang tidak berlangsung.", 403)
    return st


# --- Tiket ---------------------------------------------------------------------------


def _baca_tiket(tiket: str, garam: str, umur: int) -> dict:
    try:
        return signing.loads(tiket or "", salt=garam, max_age=umur)
    except signing.SignatureExpired:
        raise GagalAnjangsana("TIKET_KEDALUWARSA", "Waktu habis. Pindai kartu Anda lagi.", 400) from None
    except signing.BadSignature:
        raise GagalAnjangsana("TIKET_SALAH", "Data tidak valid. Pindai kartu Anda lagi.", 400) from None


def _pengunjung_dari_tiket(tiket: str) -> Peserta:
    data = _baca_tiket(tiket, GARAM_IDENTITAS, UMUR_IDENTITAS)
    p = (
        Peserta.objects.select_related("kontingen")
        .filter(pk=data.get("p"), qr_token=data.get("t"), kartu_aktif=True)
        .first()
    )
    if p is None:
        raise GagalAnjangsana("KARTU_NONAKTIF", "Kartu sudah tidak berlaku. Pindai kartu terbaru Anda.", 400)
    return p


# --- Alur --------------------------------------------------------------------------


def pindai_kartu(teks: str) -> dict:
    """Langkah 2: pengunjung memindai kartunya sendiri (atau mengetik kode kartu)."""
    wajib_terbuka()
    hasil = kenali(teks)
    if hasil.kode == "BUKAN_KARTU_PESERTA":
        raise GagalAnjangsana(hasil.kode, "Ini QR kontingen. Pindai kartu peserta Anda dulu.")
    if hasil.kode != "BERHASIL":
        raise GagalAnjangsana(hasil.kode, hasil.pesan)
    p = hasil.peserta
    tiket = signing.dumps({"p": p.pk, "t": p.qr_token}, salt=GARAM_IDENTITAS)
    return {
        "tiket": tiket,
        "nama": p.nama_lengkap,
        "kontingen": p.kontingen.nama,
        "berlaku_menit": UMUR_IDENTITAS // 60,
    }


def pindai_tuan_rumah(tiket: str, teks: str) -> dict:
    """Langkah 4: pindai QR kontingen tuan rumah di tenda."""
    wajib_terbuka()
    p = _pengunjung_dari_tiket(tiket)
    jenis, _ = tk.baca_qr(teks)
    if jenis in ("PESERTA", "KODE"):
        raise GagalAnjangsana(
            "BUKAN_QR_KONTINGEN", "Ini kartu peserta. Pindai QR kontingen tuan rumah yang ditempel di tenda."
        )
    hasil = kenali(teks)
    if hasil.kode != "BUKAN_KARTU_PESERTA" or hasil.kontingen is None:
        raise GagalAnjangsana(
            "QR_TIDAK_DIKENAL", "QR kontingen tidak dikenal. Pindai QR yang ditempel di tenda tuan rumah."
        )
    tuan = hasil.kontingen
    if tuan.pk == p.kontingen_id:
        raise GagalAnjangsana("KONTINGEN_SENDIRI", "Anda tidak bisa mengunjungi kontingen sendiri.")
    lama = Review.objects.filter(kontingen_tamu_id=p.kontingen_id, kontingen_tuan_rumah=tuan).first()
    data = {
        "tuan_rumah": tuan.nama,
        "tuan_rumah_id": tuan.pk,
        "tamu": p.kontingen.nama,
        "tiket_tuan": signing.dumps({"p": p.pk, "t": p.qr_token, "h": tuan.pk}, salt=GARAM_IDENTITAS),
        "peringatan": "",
    }
    if lama:
        data["peringatan"] = (
            f"Kontingen Anda sudah memberi review ke Kontingen {tuan.nama} pada "
            f"{timezone.localtime(lama.dikirim_pada):%d/%m pukul %H.%M}. Jika Anda lanjut, review sebelumnya akan diganti."
        )
    return data


def catat_kunjungan(request, tiket_tuan: str) -> dict:
    """Langkah 6 (setelah konfirmasi kedua): kunjungan tercatat."""
    st = wajib_terbuka()
    data = _baca_tiket(tiket_tuan, GARAM_IDENTITAS, UMUR_IDENTITAS)
    p = (
        Peserta.objects.select_related("kontingen")
        .filter(pk=data.get("p"), qr_token=data.get("t"), kartu_aktif=True)
        .first()
    )
    tuan = Kontingen.objects.filter(pk=data.get("h")).first()
    if p is None or tuan is None:
        raise GagalAnjangsana("TIKET_SALAH", "Data tidak valid. Pindai kartu Anda lagi.")
    if tuan.pk == p.kontingen_id:
        raise GagalAnjangsana("KONTINGEN_SENDIRI", "Anda tidak bisa mengunjungi kontingen sendiri.")
    sejam = timezone.now() - timedelta(hours=1)
    if Kunjungan.objects.filter(pengunjung=p, dipindai_pada__gte=sejam).count() >= BATAS_KUNJUNGAN_PER_JAM:
        raise GagalAnjangsana(
            "TERLALU_SERING", "Kartu ini sudah terlalu banyak kunjungan dalam satu jam. Coba lagi nanti.", 429
        )
    k = Kunjungan.objects.create(
        pengunjung=p,
        kontingen_tamu_id=p.kontingen_id,
        kontingen_tuan_rumah=tuan,
        sesi=st.sesi,
        ip=ip_klien(request),
        user_agent=user_agent(request),
    )
    return {
        "tiket_kunjungan": signing.dumps({"k": k.pk}, salt=GARAM_KUNJUNGAN),
        "tuan_rumah": tuan.nama,
        "tamu": p.kontingen.nama,
        "aspek": ASPEK,
    }


def kirim_review(request, tiket_kunjungan: str, nilai: dict, komentar: str, ganti: bool) -> dict:
    """Langkah 7: satu review per kontingen tamu untuk setiap tuan rumah; review lama disimpan di riwayat."""
    data = _baca_tiket(tiket_kunjungan, GARAM_KUNJUNGAN, UMUR_KUNJUNGAN)
    k = (
        Kunjungan.objects.select_related("pengunjung", "kontingen_tamu", "kontingen_tuan_rumah")
        .filter(pk=data.get("k"))
        .first()
    )
    if k is None:
        raise GagalAnjangsana("TIKET_SALAH", "Kunjungan tidak ditemukan. Ulangi dari awal.")
    angka = {}
    for aspek in ASPEK:
        try:
            v = int(nilai.get(aspek))
        except (TypeError, ValueError):
            raise GagalAnjangsana("NILAI_SALAH", "Pilih nilai 1 sampai 5 untuk setiap aspek.") from None
        if not 1 <= v <= 5:
            raise GagalAnjangsana("NILAI_SALAH", "Pilih nilai 1 sampai 5 untuk setiap aspek.")
        angka[aspek] = v
    komentar = " ".join((komentar or "").split())[:500]
    with transaction.atomic():
        lama = (
            Review.objects.select_for_update()
            .filter(kontingen_tamu=k.kontingen_tamu, kontingen_tuan_rumah=k.kontingen_tuan_rumah)
            .first()
        )
        if lama and not ganti:
            raise GagalAnjangsana(
                "SUDAH_ADA",
                f"Kontingen Anda sudah memberi review ke Kontingen {k.kontingen_tuan_rumah.nama} pada "
                f"{timezone.localtime(lama.dikirim_pada):%d/%m pukul %H.%M}. Jika Anda lanjut, review sebelumnya akan diganti.",
                409,
            )
        if lama:
            riwayat = list(lama.riwayat or [])
            riwayat.append({
                "pengunjung": lama.pengunjung_id, "pengetahuan": lama.nilai_pengetahuan,
                "keterampilan": lama.nilai_keterampilan, "sikap": lama.nilai_sikap,
                "komentar": lama.komentar, "dikirim_pada": lama.dikirim_pada.isoformat(),
            })  # fmt: skip
            lama.riwayat = riwayat
            lama.pengunjung = k.pengunjung
            lama.nilai_pengetahuan, lama.nilai_keterampilan, lama.nilai_sikap = (
                angka["pengetahuan"],
                angka["keterampilan"],
                angka["sikap"],
            )
            lama.komentar = komentar
            lama.dikirim_pada = timezone.now()
            lama.save()
            review = lama
        else:
            try:
                with transaction.atomic():
                    review = Review.objects.create(
                        kontingen_tamu=k.kontingen_tamu,
                        kontingen_tuan_rumah=k.kontingen_tuan_rumah,
                        pengunjung=k.pengunjung,
                        nilai_pengetahuan=angka["pengetahuan"],
                        nilai_keterampilan=angka["keterampilan"],
                        nilai_sikap=angka["sikap"],
                        komentar=komentar,
                    )
            except IntegrityError:  # anggota lain kontingen yang sama mengirim pada saat bersamaan
                raise GagalAnjangsana(
                    "SUDAH_ADA",
                    "Kontingen Anda baru saja memberi review ke tuan rumah ini. Kirim lagi untuk mengganti.",
                    409,
                ) from None
        catat(
            request,
            "anjangsana.review",
            review,
            keterangan=f"{k.kontingen_tamu.kode} -> {k.kontingen_tuan_rumah.kode}{' (mengganti review lama)' if lama else ''}",
            nama_pelaku=k.pengunjung.nama_lengkap,
        )
    return {"diganti": bool(lama), "tuan_rumah": k.kontingen_tuan_rumah.nama}


# --- Peringkat ---------------------------------------------------------------------------


def peringkat(tingkat: str | None = None) -> list[dict]:
    """Rata-rata nilai review; seri: jumlah kontingen tamu berbeda, lalu jumlah kunjungan."""
    kontingen = Kontingen.objects.all()
    if tingkat:
        kontingen = kontingen.filter(tingkat=tingkat)
    rata = {
        r["kontingen_tuan_rumah"]: r
        for r in Review.objects.values("kontingen_tuan_rumah")
        .annotate(
            rata=Avg((F("nilai_pengetahuan") + F("nilai_keterampilan") + F("nilai_sikap")) / 3.0), jumlah=Count("id")
        )
        .order_by()
    }
    tamu = dict(
        Kunjungan.objects.values_list("kontingen_tuan_rumah")
        .annotate(n=Count("kontingen_tamu", distinct=True))
        .order_by()
    )
    total = dict(Kunjungan.objects.values_list("kontingen_tuan_rumah").annotate(n=Count("id")).order_by())
    hasil = []
    for k in kontingen:
        r = rata.get(k.pk)
        hasil.append({
            "k": k,
            "rata_rata": round(float(r["rata"]), 3) if r else 0.0,
            "jumlah_review": r["jumlah"] if r else 0,
            "tamu_berbeda": tamu.get(k.pk, 0),
            "jumlah_kunjungan": total.get(k.pk, 0),
        })  # fmt: skip
    hasil.sort(key=lambda x: (-x["rata_rata"], -x["tamu_berbeda"], -x["jumlah_kunjungan"], x["k"].kode))
    nomor = 0
    sebelum = None
    for i, h in enumerate(hasil, start=1):
        kunci = (h["rata_rata"], h["tamu_berbeda"], h["jumlah_kunjungan"])
        if kunci != sebelum:
            nomor = i
            sebelum = kunci
        h["peringkat"] = nomor
    return hasil


def hapus_review(request, review: Review) -> None:
    with transaction.atomic():
        review.hapus_lunak(oleh=getattr(request, "nama_pelaku", "") or request.user.username)
        catat(request, "anjangsana.review_dihapus", review,
              keterangan=f"Review {review.kontingen_tamu.kode} -> {review.kontingen_tuan_rumah.kode} dihapus")  # fmt: skip


def jendela_waktu(sesi: SesiAnjangsana) -> tuple[datetime, datetime]:
    return _waktu(sesi)
