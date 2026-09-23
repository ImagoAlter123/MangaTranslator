@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Run INSTALAR_TUDO.cmd first.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" lama_local.py
if errorlevel 1 (
 echo LaMa installation failed. Check the message above.
 pause
 exit /b 1
)
echo Ready. Open the app and select Reconstruct with AI - LaMa.
pause
