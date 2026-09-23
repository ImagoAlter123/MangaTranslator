@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run INSTALAR_TUDO.cmd to create the environment first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" reparar_pip.py
if errorlevel 1 (
  echo Repair failed. Check the message above.
  pause
  exit /b 1
)
echo pip is ready. Run INSTALAR_TUDO.cmd to continue installation.
pause
