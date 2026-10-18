/* Hitung mundur sampai form biodata dibuka. Memakai selisih jam server agar jam HP yang salah tidak berpengaruh. */
document.addEventListener("alpine:init", function () {
  window.Alpine.data("hitungMundur", function (bukaIso) {
    return {
      bagian: [
        { label: "hari", nilai: "-" }, { label: "jam", nilai: "-" },
        { label: "menit", nilai: "-" }, { label: "detik", nilai: "-" }
      ],
      selisih: 0,
      target: new Date(bukaIso).getTime(),
      mulai: function () {
        var self = this;
        fetch("/daftar/status/", { headers: { "Accept": "application/json" } })
          .then(function (r) { return r.json(); })
          .then(function (d) { self.selisih = new Date(d.sekarang).getTime() - Date.now(); if (d.terbuka) { location.reload(); } })
          .catch(function () { /* pakai jam HP */ });
        this.perbarui();
        setInterval(function () { self.perbarui(); }, 1000);
      },
      perbarui: function () {
        var sisa = Math.max(0, Math.floor((this.target - (Date.now() + this.selisih)) / 1000));
        if (sisa === 0 && this.bagian[3].nilai !== "-") { location.reload(); return; }
        var h = Math.floor(sisa / 86400), j = Math.floor((sisa % 86400) / 3600), m = Math.floor((sisa % 3600) / 60), d = sisa % 60;
        this.bagian = [
          { label: "hari", nilai: h }, { label: "jam", nilai: j },
          { label: "menit", nilai: m }, { label: "detik", nilai: d }
        ];
      }
    };
  });
});
