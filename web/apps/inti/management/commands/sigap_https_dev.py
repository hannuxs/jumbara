"""HTTPS sementara untuk menguji kamera di HP lewat Wi-Fi yang sama (HANYA pengembangan/uji coba).

Kamera browser (getUserMedia) hanya mau jalan di https:// atau localhost. Perintah ini menjalankan
server pengembangan Django dengan TLS memakai sertifikat self-signed yang dibuat otomatis untuk
localhost dan semua IP laptop. Tanpa Cloudflare, tanpa paket tambahan.

    python manage.py sigap_https_dev            (https://<IP-laptop>:8443)
    python manage.py sigap_https_dev 0.0.0.0:9443

Di HP: buka https://<IP-laptop>:8443, akan muncul peringatan sertifikat (wajar, sertifikat buatan sendiri):
- Chrome Android: Lanjutan > Lanjutkan ke <IP> (tidak aman).
- Safari iPhone: Tampilkan Detail > kunjungi situs web ini.
Setelah itu kamera bisa dipakai. Produksi TIDAK memakai ini, melainkan Apache + sertifikat asli (docs/21).
"""

from __future__ import annotations

import ipaddress
import json
import socket
import ssl
from datetime import datetime, timedelta
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
from django.conf import settings
from django.core.management.commands.runserver import Command as RunserverCommand
from django.core.servers.basehttp import WSGIServer
from django.utils import timezone

UMUR_HARI = 30


def ip_laptop() -> list[str]:
    """Semua IPv4 laptop (Wi-Fi/LAN), tanpa loopback dan link-local."""
    hasil = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            hasil.add(info[4][0])
    except OSError:
        pass
    try:  # IP yang dipakai untuk keluar jaringan (tanpa benar-benar mengirim data)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            hasil.add(s.getsockname()[0])
    except OSError:
        pass
    return sorted(ip for ip in hasil if not ip.startswith(("127.", "169.254.", "0.")))


def siapkan_sertifikat(folder: Path, ips: list[str]) -> tuple[Path, Path, bool]:
    """Buat ulang sertifikat bila belum ada, hampir kedaluwarsa, atau IP laptop berubah."""
    folder.mkdir(parents=True, exist_ok=True)
    sert, kunci, info = folder / "sertifikat.pem", folder / "kunci.pem", folder / "info.json"
    nama = ["localhost", socket.gethostname()]
    alamat = ["127.0.0.1", *ips]
    try:
        lama = json.loads(info.read_text(encoding="utf-8"))
        masih = (
            sert.exists()
            and kunci.exists()
            and lama.get("alamat") == alamat
            and datetime.fromisoformat(lama["sampai"]) > timezone.now() + timedelta(days=1)
        )
    except (OSError, ValueError, KeyError):
        masih = False
    if masih:
        return sert, kunci, False
    k = ec.generate_private_key(ec.SECP256R1())
    subjek = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "SIGAP JUMBARA (uji lokal)"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "HANS PROJECT"),
    ])  # fmt: skip
    sekarang = timezone.now()
    sampai = sekarang + timedelta(days=UMUR_HARI)
    san = [x509.DNSName(n) for n in dict.fromkeys(nama)] + [x509.IPAddress(ipaddress.ip_address(a)) for a in alamat]
    c = (
        x509.CertificateBuilder()
        .subject_name(subjek)
        .issuer_name(subjek)
        .public_key(k.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(sekarang - timedelta(minutes=5))
        .not_valid_after(sampai)
        .add_extension(x509.SubjectAlternativeName(san), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(k, hashes.SHA256())
    )
    sert.write_bytes(c.public_bytes(serialization.Encoding.PEM))
    kunci.write_bytes(
        k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    )
    info.write_text(json.dumps({"alamat": alamat, "sampai": sampai.isoformat()}), encoding="utf-8")
    return sert, kunci, True


class ServerHTTPS(WSGIServer):
    """WSGIServer Django yang socket-nya dibungkus TLS. Handshake terjadi di thread permintaan."""

    konteks: ssl.SSLContext | None = None

    def server_bind(self):
        super().server_bind()
        self.socket = self.konteks.wrap_socket(self.socket, server_side=True, do_handshake_on_connect=False)

    def setup_environ(self):
        super().setup_environ()
        self.base_environ["HTTPS"] = "on"  # wsgi.url_scheme = https -> request.is_secure()

    def handle_error(self, request, client_address):
        import sys

        e = sys.exc_info()[1]
        if isinstance(e, (ssl.SSLError, ConnectionError, TimeoutError)):
            return  # HP menolak sertifikat sebelum pengguna menekan "Lanjutkan": wajar, abaikan
        super().handle_error(request, client_address)


class Command(RunserverCommand):
    help = "Server pengembangan dengan HTTPS self-signed agar kamera bisa diuji di HP (bukan untuk produksi)."
    default_port = "8443"
    default_addr = "0.0.0.0"
    server_cls = ServerHTTPS

    def inner_run(self, *args, **options):
        ips = ip_laptop()
        folder = Path(settings.SIGAP_FOLDER_PRIVAT) / "https-dev"
        sert, kunci, baru = siapkan_sertifikat(folder, ips)
        konteks = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        konteks.load_cert_chain(sert, kunci)
        ServerHTTPS.konteks = konteks
        port = self.port
        w = self.stdout.write
        w(
            self.style.WARNING(
                "HTTPS SEMENTARA untuk uji kamera di HP (sertifikat buatan sendiri, BUKAN untuk produksi)."
            )
        )
        w(f"Sertifikat {'baru dibuat' if baru else 'dipakai ulang'}: {sert} (berlaku {UMUR_HARI} hari).")
        w(f"Buka di laptop : https://localhost:{port}/")
        for ip in ips:
            host_ok = ip in settings.ALLOWED_HOSTS or "*" in settings.ALLOWED_HOSTS
            catatan = "" if host_ok else f"  <- tambahkan {ip} ke DJANGO_ALLOWED_HOSTS di web\\.env"
            w(f"Buka di HP     : https://{ip}:{port}/{catatan}")
        w(
            "Di HP akan muncul peringatan sertifikat: Chrome > Lanjutan > Lanjutkan; Safari > Tampilkan Detail > kunjungi."
        )
        w("HP dan laptop harus di Wi-Fi yang sama, dan Windows Firewall mengizinkan port ini.")
        w("")
        self.stdout.flush()
        super().inner_run(*args, **options)
