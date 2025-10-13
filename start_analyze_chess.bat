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

REM --- Pip & deps (install only when requirements change or UPDATE_DEPS=1) ---
set "REQ_FILE=requirements.txt"
set "REQ_HASH_FILE=.requirements.sha256"
set "UPDATE_DEPS=%UPDATE_DEPS%"

REM Honor deferred updates requested from the web UI
IF EXIST ".update_deps" (
    set "UPDATE_DEPS=1"
    del /q ".update_deps" 2>NUL
)

IF EXIST "%REQ_FILE%" (
    for /f "tokens=1" %%H in ('certutil -hashfile "%REQ_FILE%" SHA256 ^| find /i /v "hash" ^| find /i /v "certutil"') do set "REQ_HASH=%%H"
    set "DO_INSTALL=0"
    IF NOT EXIST "%REQ_HASH_FILE%" (
        set "DO_INSTALL=1"
    ) ELSE (
        set /p OLD_HASH=<"%REQ_HASH_FILE%"
        if /I not "%OLD_HASH%"=="%REQ_HASH%" set "DO_INSTALL=1"
    )
    if "%UPDATE_DEPS%"=="1" set "DO_INSTALL=1"
    if %DO_INSTALL%==1 (
        echo [%date% %time%] [*] Installing deps (changes detected or forced)... >> "%LOGFILE%"
        pip install -r "%REQ_FILE%" >> "%LOGFILE%" 2>&1
        >"%REQ_HASH_FILE%" echo %REQ_HASH%
    ) ELSE (
        echo [%date% %time%] [=] Deps up-to-date (no install). >> "%LOGFILE%"
    )
)

REM --- App env ---
REM set FLASK_APP=app.py
REM set FLASK_ENV=development
REM Do not hardcode STOCKFISH_PATH; allow app auto-discovery/installer to run
REM set STOCKFISH_PATH=C:\path\to\stockfish.exe
set HOST=127.0.0.1

REM --- Port selection logic using a REAL health check ---
set PORT=5000
set HEALTH_URL=http://127.0.0.1:%PORT%/__ac_health
set EXPECTED=analyze_chess_ok

REM Is 5000 listening?
netstat -ano | findstr /R /C:":%PORT% .*LISTENING" >NUL
IF %ERRORLEVEL%==0 (
    echo [%date% %time%] Port %PORT% is in use. Checking health... >> "%LOGFILE%"

    REM Call PowerShell to fetch health endpoint content
    for /f "usebackq delims=" %%H in (`powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing '%HEALTH_URL%'; $r.Content.Trim() } catch { '' }"`) do (
        set "HEALTH=%%H"
    )

    if /I "%HEALTH%"=="%EXPECTED%" (
    echo [%date% %time%] Detected existing Analyze Chess on %PORT%. Opening browser & exiting. >> "%LOGFILE%"
    start "" http://127.0.0.1:%PORT%/analyze_chess_move
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

REM --- Optional: force Stockfish refresh if requested ---
IF EXIST ".update_engine" (
    set "UPDATE_ENGINE=1"
    del /q ".update_engine" 2>NUL
)
IF "%UPDATE_ENGINE%"=="1" (
    echo [%date% %time%] [*] UPDATE_ENGINE=1: removing existing engine to refresh... >> "%LOGFILE%"
    del /q "bin\stockfish*.exe" 2>NUL
)

REM --- Launch app ---
start "" http://127.0.0.1:%PORT%/analyze_chess_move
echo [%date% %time%] [*] Launching app (python app.py) on %PORT%... >> "%LOGFILE%"
set PORT=%PORT%
"C:\Projects\pyscripts\.venv\Scripts\python.exe" "C:\Projects\pyscripts\app.py" >> "%LOGFILE%" 2>&1

IF %ERRORLEVEL% NEQ 0 (
    echo [%date% %time%] [!] Flask exited with code %ERRORLEVEL% >> "%LOGFILE%"
) ELSE (
    echo [%date% %time%] Flask stopped normally. >> "%LOGFILE%"
)
echo -------------------------------------------- >> "%LOGFILE%"
echo Log saved to %LOGFILE%
pause
