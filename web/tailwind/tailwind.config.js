/** Konfigurasi Tailwind CSS (CLI standalone v3.4, tanpa Node.js). Lihat docs/20-TAMPILAN.md. */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./apps/**/templates/**/*.html",
    "./apps/**/*.py",
    "./static/js/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        oranye: { DEFAULT: "#F26B1D", tua: "#E2451F", judul: "#E8590C", muda: "#FDE3CF" },
        amber: { DEFAULT: "#FFB21A" },
        navy: "#1F2937",
        teks: "#374151",
        abu: "#6B7280",
        krem: "#FFF3E4",
        zebra: "#FFF9F2",
        garis: "#F5D2B3",
        pmr: "#D7262E",
        mula: { DEFAULT: "#16A34A", muda: "#DCFCE7" },
        madya: { DEFAULT: "#2563EB", muda: "#DBEAFE" },
        wira: { DEFAULT: "#EAB308", muda: "#FEF9C3" },
        hijau: "#16A34A",
        kuning: "#F59E0B",
        merah: "#DC2626",
      },
      fontFamily: {
        judul: ["Poppins", "ui-sans-serif", "system-ui", "sans-serif"],
        sans: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
      },
      boxShadow: {
        kartu: "0 1px 2px rgba(31,41,55,.06), 0 4px 16px rgba(242,107,29,.08)",
      },
    },
  },
  // Kelas yang namanya dibentuk dinamis di template (badge-{{ tingkat }}).
  safelist: ["badge-MULA", "badge-MADYA", "badge-WIRA", "badge-SEMUA"],
  plugins: [],
};
