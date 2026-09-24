@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_windows.ps1"
if errorlevel 1 (
  echo.
  echo Installation did not finish. See logs\installation.txt.
  echo Run this file again to continue.
  pause
  exit /b 1
)
echo.
echo Installation complete. Open RUN.cmd.
pause
