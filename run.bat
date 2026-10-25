@echo off
setlocal
cd /d "%~dp0"
title MINION-FORTRESS CLI

set "PY_CMD="

if exist "%~dp0.venv\Scripts\python.exe" (
    set "PY_CMD=%~dp0.venv\Scripts\python.exe"
    goto :found
)
if exist "%~dp0venv\Scripts\python.exe" (
    set "PY_CMD=%~dp0venv\Scripts\python.exe"
    goto :found
)

python --version >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=python"
    goto :found
)

py -3 --version >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=py -3"
    goto :found
)

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :found
)

echo.
echo [HATA] Python bulunamadi!
echo Lutfen Python 3.10+ kurulu ve PATH ortam degiskenine ekli oldugundan emin olun.
pause
exit /b 1

:found
%PY_CMD% main.py %*
if errorlevel 1 (
    echo.
    echo [BILGI] Uygulama kapandi - Cikis Kodu: %errorlevel%
    pause
)
endlocal
