@echo off
cd /d "%~dp0"
py -3.12 --version >nul 2>&1
if errorlevel 1 (
  echo Install Python 3.12 for Windows from https://www.python.org/downloads/windows/
  echo Select the option to install Python Launcher.
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe py -3.12 -m venv .venv
.venv\Scripts\python.exe repair_pip.py
if errorlevel 1 (
  echo The Python environment needs repair. Check the message above.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
  echo Installation failed. Check your connection and the message above.
  pause
  exit /b 1
)
echo Editor installed. Use RUN.cmd. For automatic translation, use INSTALL_AI.cmd.
pause
