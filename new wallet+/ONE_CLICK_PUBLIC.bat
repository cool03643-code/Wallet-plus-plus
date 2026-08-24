@echo off
title Wallet+ Public Server
echo.
echo ===================================================
echo   WALLET+ - Making your computer a public server
echo ===================================================
echo.
cd /d "%~dp0"

echo [Step 1] Installing needed packages...
python -m pip install flask requests pyngrok --quiet

echo.
echo [Step 2] Starting the Wallet+ server...
start "Wallet+ Backend" /min cmd /c "python app.py"

timeout /t 2 >nul

echo.
echo [Step 3] Creating public link with ngrok...
echo.
echo If this is the first time, you need a FREE ngrok account:
echo 1. Go to https://dashboard.ngrok.com/signup
echo 2. Copy your authtoken from https://dashboard.ngrok.com/get-started/your-authtoken
echo 3. Paste it below when asked.
echo.
echo Press any key to continue...
pause >nul

ngrok http 5000

echo.
echo Keep this window open to keep the public link alive.
pause
