@echo off
REM ============================================
REM      Analyze Chess - Simple Flask Launcher
REM ============================================

REM Change to the directory where this batch file is located
cd /d "%~dp0"

echo Starting Chess Analysis App...
echo Working directory: %CD%
echo.

REM Check if virtual environment exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call "venv\Scripts\activate.bat"
) else (
    echo Warning: Virtual environment not found at venv\Scripts\activate.bat
    echo Using system Python...
)

REM Check if app is already running on port 5000
echo Checking if app is already running...
netstat -ano | findstr ":5000.*LISTENING" >NUL 2>&1
if %ERRORLEVEL%==0 (
    echo App appears to be running on port 5000. Opening browser...
    start "" "http://127.0.0.1:5000/analyze_chess_move"
    echo.
    echo If the app is not responding, close it and run this script again.
    pause
    exit /b
)

REM Start the Flask app and open browser
echo Starting Flask application...
echo Opening browser in 3 seconds...
timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:5000/analyze_chess_move"

REM Run the Python app
python app.py

echo.
echo Application stopped.
pause