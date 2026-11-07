@echo off
echo ====================================================
echo BURPNAKE BASLATILIYOR (BACKEND + FRONTEND)
echo ====================================================

:: Port kullanımını kontrol et
echo.
echo [+] Backend sunucusu baslatiliyor (Port 8899)...
if exist "%~dp0venv\Scripts\activate.bat" (
    start cmd /k "cd /d %~dp0 && call venv\Scripts\activate.bat && python run.py"
) else (
    start cmd /k "cd /d %~dp0 && python run.py"
)

echo [+] Frontend sunucusu baslatiliyor (Port 3000)...
start cmd /k "cd /d %~dp0frontend && set "PATH=%PATH%;C:\Program Files\nodejs" && npm run dev"

echo.
echo [!] Sunucular ayri pencerelerde calisiyor.
echo [!] Sisteme erismek icin tarayicinizdan su adrese gidin:
echo [!] http://localhost:3000
echo.
pause
