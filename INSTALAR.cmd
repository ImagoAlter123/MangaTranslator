@echo off
cd /d "%~dp0"
py -3.12 --version >nul 2>&1
if errorlevel 1 (
  echo Instale Python 3.12 para Windows em https://www.python.org/downloads/windows/
  echo Marque a opcao de instalar o Python Launcher.
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe py -3.12 -m venv .venv
.venv\Scripts\python.exe reparar_pip.py
if errorlevel 1 (
  echo O ambiente Python precisa de reparo. Veja a mensagem acima.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
  echo A instalacao falhou. Confira a conexao e a mensagem acima.
  pause
  exit /b 1
)
echo Editor instalado. Use ABRIR.cmd. Para traducao automatica, use INSTALAR_IA.cmd.
pause
