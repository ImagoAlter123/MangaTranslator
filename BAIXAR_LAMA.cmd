@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Execute INSTALAR_TUDO.cmd primeiro.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" lama_local.py
if errorlevel 1 (
 echo A instalacao do LaMa falhou. Confira a mensagem acima.
 pause
 exit /b 1
)
echo Pronto. Abra o aplicativo e escolha Reconstruir com IA - LaMa.
pause
