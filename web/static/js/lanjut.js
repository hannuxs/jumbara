/* Setelah masuk: minta nama pemakai (superadmin, sekali per perangkat), lalu kembali ke menu terakhir. */
document.addEventListener("DOMContentLoaded", function () {
  var el = document.getElementById("lanjut");
  if (!el || !window.SIGAP) { return; }
  var awalan = [];
  try { awalan = JSON.parse(document.getElementById("awalan-rute").textContent); } catch (e) { awalan = []; }

  function boleh(rute) {
    return typeof rute === "string" && rute.charAt(0) === "/" && rute.charAt(1) !== "/" &&
      awalan.some(function (a) { return rute.indexOf(a) === 0; });
  }

  function pergi() {
    var tujuan = el.dataset.next;
    if (!boleh(tujuan)) { tujuan = (window.SIGAP.ingatan() || {}).rute_terakhir; }
    if (!boleh(tujuan)) { tujuan = el.dataset.awal; }
    window.location.replace(tujuan);
  }

  if (el.dataset.mintaNama === "1" && !window.SIGAP.namaPelaku()) {
    document.getElementById("memuat").classList.add("hidden");
    document.getElementById("form-nama").classList.remove("hidden");
    var input = document.getElementById("nama-pelaku");
    input.focus();
    document.getElementById("isi-nama").addEventListener("submit", function (e) {
      e.preventDefault();
      if (window.SIGAP.aturNama(input.value)) { pergi(); }
    });
    return;
  }
  pergi();
});
