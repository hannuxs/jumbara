@echo off
rem SIGAP JUMBARA: periksa kesiapan lalu jalankan server.
rem   jalankan.bat              pengembangan (laptop): HTTPS di port SIGAP_PORT (.env, bawaan 8585)
rem   jalankan.bat -Produksi    produksi (server): Caddy HTTPS asli + Waitress
rem   jalankan.bat -CekSaja     hanya periksa
rem   jalankan.bat -Tes         jalankan juga ruff dan pytest
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0web\scripts\windows\jalankan.ps1" %*
if errorlevel 1 (
  echo.
  echo Ada masalah. Baca pesan merah di atas.
  if "%~1"=="" pause
)
