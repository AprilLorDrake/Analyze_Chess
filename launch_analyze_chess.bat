@echo off
cd /d "%~dp0"

REM Activate virtual environment and start Flask server in background
start /min "" cmd /c "call venv\Scripts\activate.bat && python app.py"

REM Wait a moment for server to start
timeout /t 3 /nobreak >nul

REM Open browser
start http://127.0.0.1:5000

REM Terminal closes automatically after this
