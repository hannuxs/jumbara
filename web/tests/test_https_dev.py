"""Tes sertifikat HTTPS sementara (sigap_https_dev) untuk uji kamera di HP."""

from __future__ import annotations

import ipaddress

from cryptography import x509

from apps.inti.management.commands.sigap_https_dev import siapkan_sertifikat


def _san(path) -> x509.SubjectAlternativeName:
    c = x509.load_pem_x509_certificate(path.read_bytes())
    return c.extensions.get_extension_for_class(x509.SubjectAlternativeName).value


def test_sertifikat_dibuat_dipakai_ulang_dan_diperbarui(tmp_path):
    sert, kunci, baru = siapkan_sertifikat(tmp_path, ["192.168.1.18"])
    assert baru and sert.exists() and kunci.exists()
    ip = _san(sert).get_values_for_type(x509.IPAddress)
    assert ipaddress.ip_address("192.168.1.18") in ip and ipaddress.ip_address("127.0.0.1") in ip
    assert "localhost" in _san(sert).get_values_for_type(x509.DNSName)
    assert siapkan_sertifikat(tmp_path, ["192.168.1.18"])[2] is False  # IP sama: dipakai ulang
    _, _, baru = siapkan_sertifikat(tmp_path, ["10.0.0.5"])  # IP laptop berubah: dibuat ulang
    assert baru and ipaddress.ip_address("10.0.0.5") in _san(sert).get_values_for_type(x509.IPAddress)


def test_http_biasa_dialihkan_ke_https():
    import socket

    from apps.inti.management.commands.sigap_https_dev import ServerHTTPS

    server = ServerHTTPS.__new__(ServerHTTPS)
    server.server_address = ("0.0.0.0", 8000)
    a, b = socket.socketpair()
    b.sendall(b"GET /panitia/?x=1 HTTP/1.1\r\nHost: 192.168.1.18:8000\r\n\r\n")
    server._alihkan_ke_https(a)
    a.close()
    jawab = b.recv(4096).decode()
    b.close()
    assert jawab.startswith("HTTP/1.1 301") and "Location: https://192.168.1.18:8000/panitia/?x=1\r\n" in jawab
