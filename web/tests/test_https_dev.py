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
