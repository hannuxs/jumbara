"""Uji beban absensi: banyak HP memindai bersamaan ke server yang sedang berjalan (docs/14-ABSENSI.md).

Contoh (server dev di port 8010):
    python manage.py sigap_uji_beban --url http://127.0.0.1:8010
    python manage.py sigap_uji_beban --url http://127.0.0.1:8000 --perangkat 30 --titik 15 --pindaian 40

Yang dilakukan:
1. Membuat data uji yang tidak terlihat di form publik/rekap: satu kontingen tersembunyi (status terhapus)
   "UJI-BEBAN", sejumlah peserta uji, titik absen UB-xxxx-01.. (BUKA, tanpa poin), dan sesi login sementara
   untuk akun panitia yang ada (sandinya tidak diubah).
2. Setiap "HP" (thread) memakai sesi login sendiri, memindai kartu ke titiknya lewat POST /api/pindai
   dengan jeda acak, sambil memantau ringkasan titik (polling) seperti HP sungguhan.
   Sekitar 10% pindaian adalah kartu yang juga dipindai HP lain di titik yang sama (harus KUNING, bukan dobel),
   dan sekitar 5% adalah kiriman ulang client_uuid yang sama (harus idempoten).
3. Melaporkan rata-rata, p50, p95, maks waktu tanggap, jumlah galat, dan memeriksa database:
   tidak boleh ada baris kehadiran ganda dan setiap pasangan (titik, peserta) yang HIJAU tercatat tepat sekali.
4. Menghapus semua data uji yang dibuatnya sendiri (berdasarkan ID), kecuali --simpan-data.

Aman dijalankan di server produksi sebelum acara karena hanya menyentuh data yang dibuatnya sendiri,
tetapi wajib --ya bila DEBUG=False.
"""

from __future__ import annotations

import json
import random
import secrets
import statistics
import threading
import time
import urllib.error
import urllib.request
import uuid
from collections import Counter
from datetime import date
from datetime import time as jam

from django.conf import settings
from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from apps.absensi.models import Kehadiran, PindaianDitolak, StatusTitik, TitikAbsen
from apps.akun.middleware import KUNCI_LOGIN_PADA
from apps.akun.models import Pengguna, Peran
from apps.biodata.models import Peserta
from apps.kartu import services as kartu_svc
from apps.kontingen.models import Kontingen

KODE_KONTINGEN = "UJI-BEBAN"


class HP:
    """Satu perangkat pemindai: sesi sendiri, cookie sendiri."""

    def __init__(self, url: str, sesi: str, nama: str):
        self.url = url.rstrip("/")
        self.csrf = secrets.token_hex(16)
        self.cookie = f"{settings.SESSION_COOKIE_NAME}={sesi}; {settings.CSRF_COOKIE_NAME}={self.csrf}"
        self.nama = nama
        self.perangkat_id = uuid.uuid4().hex

    def _minta(self, metode: str, jalur: str, data: dict | None = None) -> tuple[int, dict | None, float]:
        badan = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(self.url + jalur, data=badan, method=metode)  # noqa: S310 (skema dicek di handle)
        req.add_header("Cookie", self.cookie)
        req.add_header("X-CSRFToken", self.csrf)
        req.add_header("X-Requested-With", "XMLHttpRequest")
        req.add_header("Referer", self.url + "/panitia/")
        if badan is not None:
            req.add_header("Content-Type", "application/json")
        mulai = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310
                isi = r.read()
                kode = r.status
        except urllib.error.HTTPError as e:
            isi, kode = e.read(), e.code
        except OSError:
            return 0, None, time.perf_counter() - mulai
        lama = time.perf_counter() - mulai
        try:
            return kode, json.loads(isi), lama
        except ValueError:
            return kode, None, lama

    def pindai(self, titik_id: int, qr: str, cu: str) -> tuple[int, dict | None, float]:
        return self._minta("POST", "/api/pindai", {
            "client_uuid": cu, "titik_absen_id": titik_id, "qr": qr, "nama_pemindai": self.nama,
            "perangkat_id": self.perangkat_id, "metode": "SCAN", "dipindai_pada": timezone.now().isoformat(),
        })  # fmt: skip

    def ringkas(self, titik_id: int) -> tuple[int, dict | None, float]:
        return self._minta("GET", f"/api/titik-absen/{titik_id}/ringkas/")


class Command(BaseCommand):
    help = "Uji beban absensi: banyak HP memindai bersamaan ke server yang berjalan, lalu periksa tidak ada data dobel."

    def add_arguments(self, parser):
        parser.add_argument("--url", default="http://127.0.0.1:8000", help="Alamat server yang sedang berjalan.")
        parser.add_argument("--perangkat", type=int, default=30, help="Jumlah HP pemindai bersamaan (bawaan 30).")
        parser.add_argument("--titik", type=int, default=15, help="Jumlah titik absen bersamaan (bawaan 15).")
        parser.add_argument("--pindaian", type=int, default=40, help="Pindaian per HP (bawaan 40).")
        parser.add_argument("--jeda", type=float, default=0.5, help="Rata-rata jeda antarpindaian per HP, detik.")
        parser.add_argument("--dobel", type=float, default=0.10, help="Porsi kartu yang juga dipindai HP lain.")
        parser.add_argument("--ulang", type=float, default=0.05, help="Porsi kiriman ulang client_uuid yang sama.")
        parser.add_argument("--simpan-data", action="store_true", help="Jangan hapus data uji setelah selesai.")
        parser.add_argument("--ya", action="store_true", help="Wajib bila DEBUG=False (server produksi).")

    def handle(self, *args, **o):
        if not settings.DEBUG and not o["ya"]:
            raise CommandError("DEBUG=False (produksi). Tambahkan --ya bila yakin; data uji dihapus lagi setelahnya.")
        if o["perangkat"] < 1 or o["titik"] < 1 or o["pindaian"] < 1:
            raise CommandError("Angka --perangkat, --titik, dan --pindaian minimal 1.")
        url = o["url"].rstrip("/")
        if not url.startswith(("http://", "https://")):
            raise CommandError("--url harus diawali http:// atau https://")
        try:
            urllib.request.urlopen(url + "/", timeout=10).read(1)  # noqa: S310
        except OSError as e:
            raise CommandError(f"Server {url} tidak bisa dihubungi ({e}). Jalankan dulu servernya.") from None

        data = self._siapkan(o)
        try:
            laporan = self._jalankan(url, data, o)
            ok = self._periksa(data, laporan)
        finally:
            if o["simpan_data"]:
                self.stdout.write(self.style.WARNING(f"Data uji disimpan (kontingen {KODE_KONTINGEN}, titik UB-*)."))
            else:
                self._bersihkan(data)
        if not ok:
            raise CommandError("Uji beban GAGAL. Lihat catatan di atas.")
        self.stdout.write(self.style.SUCCESS("Uji beban LULUS."))

    # --- Persiapan dan pembersihan ----------------------------------------------------------------------

    def _siapkan(self, o) -> dict:
        n_titik, n_hp, n_pindai = o["titik"], o["perangkat"], o["pindaian"]
        hp_per_titik = max(1, -(-n_hp // n_titik))
        n_peserta = max(20, hp_per_titik * n_pindai)
        akhiran = secrets.token_hex(2).upper()
        # Akun per peran tunggal: pakai akun panitia yang ada (sandinya tidak disentuh), hanya sesi sementara.
        akun = Pengguna.objects.filter(peran=Peran.PANITIA, is_active=True).first()
        if akun is None:
            raise CommandError("Akun panitia belum ada atau nonaktif. Jalankan sigap_seed dulu.")
        with transaction.atomic():
            k = Kontingen(kode=KODE_KONTINGEN[:10], nama="Kontingen Uji Beban (sementara)", tingkat="MADYA")
            k.save()
            k.hapus_lunak(oleh="sigap_uji_beban")  # tersembunyi dari form publik dan rekap
            peserta = []
            for i in range(n_peserta):
                p = Peserta(
                    kode_pendaftaran=f"UB{akhiran}{i:05d}", kontingen=k, tingkat="MADYA", peran="PESERTA",
                    nama_lengkap=f"UJI BEBAN {i + 1:04d}", nik_terenkripsi="uji-beban",
                    nik_hash=f"ub{akhiran}{i:058d}", nik_samar="UJI*BEBAN", nik_akhir4="0000",
                    jenis_kelamin="L", tempat_lahir="Uji", tanggal_lahir=date(2010, 1, 1), alamat="Uji beban",
                    golongan_darah="O",
                )  # fmt: skip
                kartu_svc.pasang_token(p)
                p.save()
                peserta.append(p)
            titik = [
                TitikAbsen.objects.create(
                    kode=f"UB-{akhiran}-{i + 1:02d}",
                    nama_tampil=f"Uji beban {i + 1}",
                    tingkat="SEMUA",
                    tanggal=timezone.localdate(),
                    mulai=jam(0, 0),
                    selesai=jam(23, 59),
                    status=StatusTitik.BUKA,
                    hitung_poin=False,
                    catatan="Dibuat sigap_uji_beban, dihapus otomatis.",
                )  # fmt: skip
                for i in range(n_titik)
            ]
        sesi = []
        for _ in range(n_hp):
            s = SessionStore()
            s[SESSION_KEY] = str(akun.pk)
            s[BACKEND_SESSION_KEY] = "django.contrib.auth.backends.ModelBackend"
            s[HASH_SESSION_KEY] = akun.get_session_auth_hash()
            s[KUNCI_LOGIN_PADA] = int(time.time())
            s.create()
            sesi.append(s.session_key)
        self.stdout.write(
            f"Data uji: {len(peserta)} peserta, {len(titik)} titik, {n_hp} HP ({hp_per_titik} HP per titik), "
            f"{n_pindai} pindaian per HP."
        )
        return {"kontingen": k, "peserta": peserta, "titik": titik, "akun": akun, "sesi": sesi}

    def _bersihkan(self, data: dict) -> None:
        """Hapus HANYA data yang dibuat perintah ini (berdasarkan ID)."""
        id_titik = [t.pk for t in data["titik"]]
        id_peserta = [p.pk for p in data["peserta"]]
        with transaction.atomic():
            n_hadir = Kehadiran.semua.filter(titik_absen_id__in=id_titik, peserta_id__in=id_peserta).delete()[0]
            n_tolak = PindaianDitolak.objects.filter(titik_absen_id__in=id_titik).delete()[0]
            TitikAbsen.objects.filter(pk__in=id_titik).delete()
            Peserta.semua.filter(pk__in=id_peserta, kontingen=data["kontingen"]).delete()
            Kontingen.semua.filter(pk=data["kontingen"].pk, kode=KODE_KONTINGEN[:10]).delete()
            Session.objects.filter(session_key__in=data["sesi"]).delete()
        self.stdout.write(
            f"Data uji dihapus ({n_hadir} kehadiran, {n_tolak} pindaian ditolak, titik, peserta, sesi sementara)."
        )

    # --- Menjalankan -------------------------------------------------------------------------------------

    def _jalankan(self, url: str, data: dict, o) -> dict:
        titik, peserta = data["titik"], data["peserta"]
        n_hp = len(data["sesi"])
        # HP ke-i bertugas di titik i % jumlah titik. HP di titik yang sama berbagi daftar kartu.
        hp_di_titik: dict[int, list[int]] = {}
        for i in range(n_hp):
            hp_di_titik.setdefault(i % len(titik), []).append(i)
        kunci = threading.Lock()
        hasil: list[dict] = []
        polling: list[float] = []
        galat_polling = [0]
        mulai_serentak = threading.Barrier(n_hp)

        def kerja(i: int) -> None:
            rng = random.Random(i)
            hp = HP(url, data["sesi"][i], f"HP {i + 1:02d}")
            t = titik[i % len(titik)]
            rekan = hp_di_titik[i % len(titik)]
            urutan = rekan.index(i)
            # Bagian kartu milik HP ini; kartu "dobel" diambil dari bagian HP lain di titik yang sama.
            milik = peserta[urutan :: len(rekan)][: o["pindaian"]]
            lain = [p for j, p in enumerate(peserta) if j % len(rekan) != urutan] or peserta
            terkirim: list[tuple[str, str]] = []
            mulai_serentak.wait()
            terakhir_poll = 0.0
            for n in range(o["pindaian"]):
                r = rng.random()
                if terkirim and r < o["ulang"]:
                    jenis = "ulang"
                    qr, cu = rng.choice(terkirim)
                elif r < o["ulang"] + o["dobel"]:
                    jenis = "dobel"
                    qr, cu = "SJP:" + rng.choice(lain).qr_token, str(uuid.uuid4())
                else:
                    jenis = "baru"
                    qr, cu = "SJP:" + milik[n % len(milik)].qr_token, str(uuid.uuid4())
                kode, j, lama = hp.pindai(t.pk, qr, cu)
                terkirim.append((qr, cu))
                with kunci:
                    hasil.append({"hp": i, "titik": t.pk, "jenis": jenis, "kode": kode, "lama": lama, "cu": cu,
                                  "status": (j or {}).get("status", "GALAT")})  # fmt: skip
                if time.monotonic() - terakhir_poll > 5:
                    terakhir_poll = time.monotonic()
                    k2, _, l2 = hp.ringkas(t.pk)
                    with kunci:
                        polling.append(l2)
                        if k2 != 200:
                            galat_polling[0] += 1
                time.sleep(rng.uniform(0, 2 * o["jeda"]))

        benang = [threading.Thread(target=kerja, args=(i,), daemon=True) for i in range(n_hp)]
        t0 = time.perf_counter()
        for b in benang:
            b.start()
        for b in benang:
            b.join()
        durasi = time.perf_counter() - t0
        return {"hasil": hasil, "polling": polling, "galat_polling": galat_polling[0], "durasi": durasi}

    # --- Laporan dan pemeriksaan ------------------------------------------------------------------------------

    def _periksa(self, data: dict, lap: dict) -> bool:
        hasil = lap["hasil"]
        lama = sorted(h["lama"] * 1000 for h in hasil)

        def p(q: float) -> float:
            return lama[min(len(lama) - 1, int(q * len(lama)))] if lama else 0.0

        galat = [h for h in hasil if h["kode"] != 200 or h["status"] not in ("HIJAU", "KUNING")]
        status = Counter(h["status"] for h in hasil)
        jenis = Counter(h["jenis"] for h in hasil)
        w = self.stdout.write
        w("")
        w(
            f"Durasi {lap['durasi']:.1f} detik, {len(hasil)} pindaian ({len(hasil) / max(lap['durasi'], 0.001):.1f} per detik)."
        )
        w(
            f"Jenis: {jenis['baru']} kartu baru, {jenis['dobel']} kartu dobel antar-HP, {jenis['ulang']} kiriman ulang client_uuid."
        )
        w(
            f"Hasil: {status['HIJAU']} hijau, {status['KUNING']} kuning, lainnya {len(hasil) - status['HIJAU'] - status['KUNING']}."
        )
        w(
            f"Waktu tanggap pindai (ms): rata-rata {statistics.fmean(lama):.0f}, p50 {p(0.5):.0f}, "
            f"p95 {p(0.95):.0f}, maks {lama[-1]:.0f}."
            if lama
            else "Tidak ada pindaian."
        )
        if lap["polling"]:
            w(f"Polling ringkasan: {len(lap['polling'])} kali, rata-rata {statistics.fmean(lap['polling']) * 1000:.0f} ms, "
              f"galat {lap['galat_polling']}.")  # fmt: skip
        ok = True
        if galat:
            ok = False
            contoh = Counter((h["kode"], h["status"]) for h in galat).most_common(5)
            w(self.style.ERROR(f"GALAT: {len(galat)} pindaian gagal. Contoh (kode HTTP, status): {contoh}"))
        # Pemeriksaan database.
        id_titik = [t.pk for t in data["titik"]]
        dobel = (
            Kehadiran.semua.filter(titik_absen_id__in=id_titik, aktif_key=1)
            .values("titik_absen_id", "peserta_id")
            .annotate(n=Count("id"))
            .filter(n__gt=1)
            .count()
        )
        baris = Kehadiran.semua.filter(titik_absen_id__in=id_titik).count()
        cu_hijau = {h["cu"] for h in hasil if h["status"] == "HIJAU"}
        cu_db = {
            str(c) for c in Kehadiran.semua.filter(titik_absen_id__in=id_titik).values_list("client_uuid", flat=True)
        }
        w(f"Database: {baris} baris kehadiran, {dobel} pasangan (titik, peserta) ganda.")
        if dobel:
            ok = False
            w(self.style.ERROR("GAGAL: ada kehadiran ganda."))
        if cu_db != cu_hijau:
            # Setiap client_uuid yang dijawab HIJAU harus ada di DB, dan sebaliknya.
            ok = False
            w(
                self.style.ERROR(
                    f"GAGAL: HIJAU tanpa baris {len(cu_hijau - cu_db)}, baris tanpa HIJAU {len(cu_db - cu_hijau)}."
                )
            )
        p95 = p(0.95)
        if p95 > 1000:
            w(
                self.style.WARNING(
                    f"Peringatan: p95 {p95:.0f} ms di atas 1 detik. Periksa jumlah thread Waitress dan MariaDB."
                )
            )
        return ok
