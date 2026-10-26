@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title MINION-FORTRESS LAUNCHER

set "PY_CMD="

if exist "%~dp0.venv\Scripts\python.exe" (
    set "PY_CMD=%~dp0.venv\Scripts\python.exe"
    goto :check_deps
)
if exist "%~dp0venv\Scripts\python.exe" (
    set "PY_CMD=%~dp0venv\Scripts\python.exe"
    goto :check_deps
)

rem Find base python to initialize virtualenv
set "BASE_PY="
python --version >nul 2>&1
if not errorlevel 1 (
    set "BASE_PY=python"
    goto :create_venv
)

py -3 --version >nul 2>&1
if not errorlevel 1 (
    set "BASE_PY=py -3"
    goto :create_venv
)

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "BASE_PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :create_venv
)

echo.
echo [HATA] Python bulunamadi!
echo Lutfen Python 3.10+ kurulu ve PATH ortam degiskenine ekli oldugundan emin olun.
pause
exit /b 1

:create_venv
echo [BILGI] Sanal ortam hazirlaniyor: .venv
%BASE_PY% -m venv .venv
if errorlevel 1 (
    echo [HATA] Sanal ortam olusturulamadi!
    pause
    exit /b 1
)
set "PY_CMD=%~dp0.venv\Scripts\python.exe"

:check_deps
rem Verify required dependencies
%PY_CMD% -c "import textual, psutil, rich" >nul 2>&1
if errorlevel 1 (
    echo [BILGI] Gerekli paketler yukleniyor: requirements.txt
    %PY_CMD% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [HATA] Paketler yuklenirken hata olustu!
        pause
        exit /b 1
    )
)

:run
echo [BILGI] MINION-FORTRESS yeni bir pencerede baslatiliyor...
start "MINION-FORTRESS CLI" "%PY_CMD%" main.py %*
endlocal
exit /b 0
