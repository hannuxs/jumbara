/* Halaman bukti: hapus draf form (kiriman berhasil) dan ingat sekolah + tingkat untuk "Isi untuk orang lain". */
document.addEventListener("DOMContentLoaded", function () {
  try {
    window.localStorage.removeItem("sigap:biodata:draf");
    var a = document.querySelector("[data-isi-lagi]");
    if (a) {
      window.localStorage.setItem("sigap:biodata:lanjutan", JSON.stringify({ kontingen: a.dataset.kontingen, tingkat: a.dataset.tingkat }));
    }
  } catch (e) { /* abaikan */ }
});
