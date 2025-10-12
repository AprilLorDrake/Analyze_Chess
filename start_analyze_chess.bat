@echo off
REM ============================================
REM      Analyze Chess - Smart Flask Launcher
REM ============================================
cd /d C:\Projects\pyscripts

set LOGFILE=C:\Projects\pyscripts\launch_log.txt
echo. > "%LOGFILE%"
echo [%date% %time%] Starting Analyze Chess >> "%LOGFILE%"
echo -------------------------------------------- >> "%LOGFILE%"

REM --- Ensure venv exists & activate ---
IF NOT EXIST ".venv\Scripts\activate" (
    echo [%date% %time%] [!] venv missing, creating... >> "%LOGFILE%"
    python -m venv .venv >> "%LOGFILE%" 2>&1
)
call .venv\Scripts\activate >> "%LOGFILE%" 2>&1

REM --- Pip & deps ---
python -m pip install --upgrade pip >> "%LOGFILE%" 2>&1
IF EXIST requirements.txt (
    echo [%date% %time%] [*] Installing deps... >> "%LOGFILE%"
    pip install -r requirements.txt >> "%LOGFILE%" 2>&1
)

REM --- App env ---
set FLASK_APP=app.py
set FLASK_ENV=development
set STOCKFISH_PATH=C:\Projects\pyscripts\stockfish\stockfish.exe

REM --- Port selection logic using a REAL health check ---
set PORT=5000
set HEALTH_URL=http://127.0.0.1:%PORT%/__ac_health
set EXPECTED=analyze_chess_ok

REM Is 5000 listening?
netstat -ano | findstr /R /C:":%PORT% .*LISTENING" >NUL
IF %ERRORLEVEL%==0 (
    echo [%date% %time%] Port %PORT% is in use. Checking health... >> "%LOGFILE%"

    REM Call PowerShell to fetch health endpoint content
    for /f "usebackq delims=" %%H in (`powershell -NoProfile -Command ^
        "try { (Invoke-WebRequest -UseBasicParsing '%HEALTH_URL%').Content.Trim() } catch { '' }"`) do (
        set "HEALTH=%%H"
    )

    if /I "%HEALTH%"=="%EXPECTED%" (
        echo [%date% %time%] Detected existing Analyze Chess on %PORT%. Opening browser & exiting. >> "%LOGFILE%"
        start "" http://127.0.0.1:%PORT%/
        goto :EOF
    ) else (
        echo [%date% %time%] Port %PORT% is not our app. Searching for a free port... >> "%LOGFILE%"
        REM Find first free port from 5001..5099
        for /L %%P in (5001,1,5099) do (
            netstat -ano | findstr /R /C:":%%P .*LISTENING" >NUL || (
                set PORT=%%P
                goto :PORT_FOUND
            )
        )
        echo [%date% %time%] [!] No free port found in 5001-5099. >> "%LOGFILE%"
        echo No free port available. Close something and try again.
        pause
        goto :EOF
    )
)

:PORT_FOUND
echo [%date% %time%] Using port %PORT%. >> "%LOGFILE%"

REM --- Launch app ---
start "" http://127.0.0.1:%PORT%/
echo [%date% %time%] [*] Launching Flask on %PORT%... >> "%LOGFILE%"
flask run --port %PORT% >> "%LOGFILE%" 2>&1

IF %ERRORLEVEL% NEQ 0 (
    echo [%date% %time%] [!] Flask exited with code %ERRORLEVEL% >> "%LOGFILE%"
) ELSE (
    echo [%date% %time%] Flask stopped normally. >> "%LOGFILE%"
)
echo -------------------------------------------- >> "%LOGFILE%"
echo Log saved to %LOGFILE%
pause
