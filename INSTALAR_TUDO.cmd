@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar_vm.ps1"
if errorlevel 1 (
  echo.
  echo A instalacao nao terminou. Veja logs\instalacao.txt.
  echo Execute este arquivo novamente para continuar.
  pause
  exit /b 1
)
echo.
echo Instalacao concluida. Abra ABRIR.cmd.
pause
