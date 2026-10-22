/* Pantauan langsung (superadmin): polling data setiap 10 detik. */
document.addEventListener("alpine:init", function () {
  window.Alpine.data("pantauan", function (url) {
    return {
      data: { titik: [], merah: [], hp_aktif: 0, pindaian_5_menit: 0, jam: "" },
      galat: false,
      mulai: function () {
        var self = this;
        this.muat();
        setInterval(function () { if (document.visibilityState === "visible") { self.muat(); } }, 10000);
      },
      muat: function () {
        var self = this;
        fetch(url, { credentials: "same-origin", headers: { "X-Requested-With": "XMLHttpRequest" } })
          .then(function (r) { if (r.status === 401) { location.reload(); } return r.ok ? r.json() : Promise.reject(r.status); })
          .then(function (d) { self.data = d; self.galat = false; })
          .catch(function () { self.galat = true; });
      }
    };
  });
});
