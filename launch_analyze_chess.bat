@echo off
echo.
echo ========================================
echo    Starting Analyze Chess Application
echo ========================================
echo.
cd /d "%~dp0"
echo Current directory: %cd%
echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat
echo  Virtual environment activated
echo.
echo Starting Flask server...
echo  Server will start at http://127.0.0.1:5000
echo.
echo Opening browser in 3 seconds...
timeout /t 3 /nobreak >nul
start http://127.0.0.1:5000
echo  Browser launched
echo.
echo Starting Python application...
python app.py
echo.
echo Application stopped. Press any key to exit...
pause >nul
