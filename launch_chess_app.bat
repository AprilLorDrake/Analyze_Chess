@echo off
REM ============================================
REM      Analyze Chess - Flask Launcher
REM ============================================
cd /d "C:\Projects\stockfish\chess_analysis"

echo Starting Chess Analysis App...
echo.

REM Activate virtual environment
if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
    echo Virtual environment activated.
) else (
    echo Warning: Virtual environment not found. Using system Python.
)

REM Check if app is already running on port 5000
netstat -ano | findstr ":5000.*LISTENING" >NUL
if %ERRORLEVEL%==0 (
    echo App may already be running on port 5000. Opening browser...
    start "" http://127.0.0.1:5000/analyze_chess_move
    echo.
    echo Press any key to exit...
    pause >NUL
    exit
)

REM Start the Flask app and open browser
echo Starting Flask application...
start "" http://127.0.0.1:5000/analyze_chess_move
python app.py

echo.
echo Application stopped. Press any key to exit...
pause >NUL