@echo off
rem Launch Analyze_Chess from the script's directory so it works no matter where it's cloned.
pushd "%~dp0"
python app.py
popd
pause