@echo off
REM Instala las dependencias (solo la primera vez) y abre Optimizador.
cd /d "%~dp0"
python -m pip install --quiet -r requirements.txt
python main.py
