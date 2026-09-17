@echo off
echo ====================================================
echo BURPNAKE BASLATILIYOR (BACKEND + FRONTEND)
echo ====================================================

:: Port kullanımını kontrol et
echo.
echo [+] Backend sunucusu baslatiliyor (Port 8899)...
start cmd /k "cd %~dp0 && venv\Scripts\activate && python run.py"

echo [+] Frontend sunucusu baslatiliyor (Port 3000)...
start cmd /k "cd %~dp0\frontend && set "PATH=C:\Program Files\nodejs;%PATH%" && npm run dev"

echo.
echo [!] Sunucular ayri pencerelerde calisiyor.
echo [!] Sisteme erismek icin tarayicinizdan su adrese gidin:
echo [!] http://localhost:3000
echo.
pause
