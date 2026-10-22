@echo off
rem SIGAP JUMBARA: periksa kesiapan lalu jalankan server.
rem   jalankan.bat              periksa semua lalu jalankan server (port 8000)
rem   jalankan.bat -CekSaja     hanya periksa
rem   jalankan.bat -Port 8080   pakai port lain
rem   jalankan.bat -Produksi    jalankan dengan Waitress seperti di server
rem   jalankan.bat -Tes         jalankan juga ruff dan pytest
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0web\scripts\windows\jalankan.ps1" %*
if errorlevel 1 (
  echo.
  echo Ada masalah. Baca pesan merah di atas.
  if "%~1"=="" pause
)
