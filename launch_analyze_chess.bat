@echo off
cd /d "%~dp0"

REM Kill all running python.exe processes (ignore errors if none running)
taskkill /F /IM python.exe >nul 2>&1

REM Start Flask server using venv's python.exe in background
start /min "" cmd /c "venv\Scripts\python.exe app.py"

REM Wait a moment for server to start
timeout /t 3 /nobreak >nul

REM Open browser
start http://127.0.0.1:5000

REM Terminal closes automatically after this
