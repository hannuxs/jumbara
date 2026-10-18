"""Decorator hak akses per peran."""

from __future__ import annotations

from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


def peran_wajib(*peran: str):
    """Hanya peran tertentu yang boleh membuka view. Belum login -> ke halaman masuk."""

    def pembungkus(view):
        @wraps(view)
        def _view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if request.user.peran not in peran:
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return _view

    return pembungkus


def superadmin_wajib(view):
    return peran_wajib("SUPERADMIN")(view)
