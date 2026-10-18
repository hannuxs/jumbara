/* Bantuan halaman superadmin: ingat saringan tabel per perangkat, konfirmasi aksi, lihat NIK. */
(function () {
  "use strict";

  window.SIGAP_ADMIN = {
    lihatNik: function (url) {
      return fetch(url, { method: "POST", headers: { "X-CSRFToken": window.SIGAP.csrf(), "X-Requested-With": "XMLHttpRequest" }, credentials: "same-origin" })
        .then(function (r) { if (!r.ok) { throw new Error("gagal"); } return r.json(); })
        .then(function (d) { return d.nik; });
    }
  };

  document.addEventListener("DOMContentLoaded", function () {
    // Saringan tabel diingat per perangkat (lihat docs/10-AKUN-SESI.md).
    document.querySelectorAll("form[data-filter-halaman]").forEach(function (f) {
      var halaman = f.getAttribute("data-filter-halaman");
      var params = new URLSearchParams(location.search);
      if (params.get("reset")) {
        window.SIGAP.simpanFilter(halaman, "");
        history.replaceState(null, "", location.pathname);
        return;
      }
      if (!location.search) {
        var tersimpan = window.SIGAP.filter(halaman);
        if (tersimpan) { location.replace(location.pathname + "?" + tersimpan); return; }
      } else {
        params.delete("hal");
        window.SIGAP.simpanFilter(halaman, params.toString());
      }
    });

    document.querySelectorAll("form[data-konfirmasi]").forEach(function (f) {
      f.addEventListener("submit", function (e) {
        if (!window.confirm(f.getAttribute("data-konfirmasi"))) { e.preventDefault(); }
      });
    });
  });
})();
