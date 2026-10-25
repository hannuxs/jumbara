"""Tes alamat file statis berversi (mencegah CSS/JS lama dari cache browser, REVISI R1c)."""

import re

from apps.inti.templatetags.sigap import aset


def test_aset_berversi_saat_pengembangan(settings):
    settings.DEBUG = True
    assert re.fullmatch(r"/static/js/biodata\.js\?v=\d+", aset("js/biodata.js"))


def test_halaman_form_memakai_aset_berversi(client, settings):
    settings.DEBUG = True
    isi = client.get("/daftar/").content.decode()
    for nama in ("css/app.css", "js/biodata.js", "js/sigap.js", "vendor/alpine-3.14.9.min.js"):
        assert re.search(rf"/static/{re.escape(nama)}\?v=\d+", isi), nama


def test_logo_pmi_2026_dipakai_di_web_dan_pdf(client):
    """Logo PMI mendatar berlatar putih (R13) dipakai di semua halaman dan PDF; logo lama tidak dirujuk lagi."""
    from apps.biodata import pdf as bukti_pdf
    from apps.kartu import pdf as kartu_pdf
    from apps.piagam import pdf as piagam_pdf

    for url in ("/", "/masuk/", "/daftar/"):
        isi = client.get(url).content.decode()
        assert "img/pmi-logo-720.webp" in isi, url
        assert "pmi-logo.svg" not in isi and "pmi-logo-160" not in isi, url
    for modul in (bukti_pdf, kartu_pdf, piagam_pdf):
        assert (modul.FOLDER_IMG / modul.LOGO_PMI).is_file(), modul.__name__
