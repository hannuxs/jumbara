"""Filter template: tanggal dan jam gaya Indonesia, angka ribuan dengan titik."""

from django import template

from apps.inti import utils

register = template.Library()


@register.filter
def tanggal(nilai, hari=True):
    """{{ x|tanggal }} -> 'Senin, 26 Oktober 2026'; {{ x|tanggal:False }} tanpa hari."""
    return utils.tanggal_id(nilai, hari=bool(hari))


@register.filter
def jam(nilai):
    """{{ x|jam }} -> '08.00 WITA'."""
    return utils.jam_id(nilai)


@register.filter
def angka(nilai):
    """{{ x|angka }} -> '1.000'."""
    try:
        return utils.angka_id(int(nilai))
    except (TypeError, ValueError):
        return nilai


@register.filter
def wa(nomor, pesan=""):
    return utils.tautan_wa(nomor, pesan)


@register.simple_tag(takes_context=True)
def url_ganti(context, **kwargs):
    """Query string saat ini dengan beberapa parameter diganti (untuk paginasi/urutan)."""
    request = context["request"]
    q = request.GET.copy()
    for k, v in kwargs.items():
        if v in (None, ""):
            q.pop(k, None)
        else:
            q[k] = v
    return "?" + q.urlencode() if q else "?"


@register.filter
def get_item(kamus, kunci):
    """{{ kamus|get_item:kunci }} untuk dict di template."""
    if isinstance(kamus, dict):
        return kamus.get(kunci, "")
    return ""
