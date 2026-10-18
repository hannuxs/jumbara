# Bangun static\css\app.css dari tailwind\input.css (Tailwind CLI standalone, tanpa Node.js).
#   powershell -ExecutionPolicy Bypass -File scripts\windows\bangun-css.ps1          (sekali, versi produksi)
#   powershell -ExecutionPolicy Bypass -File scripts\windows\bangun-css.ps1 -Pantau  (pengembangan, otomatis)
param([switch]$Pantau)
$ErrorActionPreference = "Stop"
$web = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $web
$tw = Join-Path $web "tools\tailwindcss.exe"
if (-not (Test-Path $tw)) { throw "tools\tailwindcss.exe belum ada. Jalankan scripts\windows\unduh-alat.ps1 dulu." }
$argumen = @("-c", "tailwind\tailwind.config.js", "-i", "tailwind\input.css", "-o", "static\css\app.css")
if ($Pantau) { $argumen += "--watch" } else { $argumen += "--minify" }
& $tw @argumen
