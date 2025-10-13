@echo off
echo Starting Analyze Chess Application...
cd /d "%~dp0"
echo Current directory: %cd%
call venv\Scripts\activate.bat
echo Virtual environment activated
python app.py
