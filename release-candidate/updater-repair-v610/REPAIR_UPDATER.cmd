@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install_Updater_Repair.ps1"
set "RESULT=%ERRORLEVEL%"
echo.
pause
exit /b %RESULT%
