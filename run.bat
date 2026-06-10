@echo off
title Telegram Kino Bot - Runner
echo ===================================================
echo   Telegram Kino Botni ishga tushirish boshlandi...
echo ===================================================
echo.

echo [TIZIM] Kutubxonalar o'rnatilmoqda...
venv\\Scripts\\pip.exe install -r requirements.txt

echo [TIZIM] Bot ishga tushirilmoqda...
venv\\Scripts\\python.exe main.py

pause
