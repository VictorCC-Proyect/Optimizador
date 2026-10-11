@echo off
REM Genera dist\Optimizador.exe (un solo archivo, pide administrador al abrir).
cd /d "%~dp0"
python -m pip install --quiet -r requirements.txt pyinstaller
python -m PyInstaller --noconfirm --onefile --windowed --uac-admin ^
  --name Optimizador --collect-all customtkinter main.py
echo.
echo Listo: dist\Optimizador.exe
pause
