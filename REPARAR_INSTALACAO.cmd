@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Execute INSTALAR_TUDO.cmd para criar o ambiente primeiro.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" reparar_pip.py
if errorlevel 1 (
  echo Nao foi possivel reparar. Veja a mensagem acima.
  pause
  exit /b 1
)
echo pip pronto. Execute INSTALAR_TUDO.cmd para continuar a instalacao.
pause
