@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar_vm.ps1"
if errorlevel 1 (
  echo.
  echo Installation did not finish. See logs\instalacao.txt.
  echo Run this file again to continue.
  pause
  exit /b 1
)
echo.
echo Installation complete. Open ABRIR.cmd.
pause
