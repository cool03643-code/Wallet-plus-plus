@echo off
echo ============================================
echo   Wallet+ Public Server (with ngrok)
echo ============================================
echo.
echo This will start your wallet app and try to create a public link.
echo.
cd /d "%~dp0"

echo [1/3] Making sure pyngrok is installed...
python -m pip install pyngrok flask requests --quiet

echo.
echo [2/3] Starting Wallet+ server in background...
start "Wallet+ Server" cmd /k "python app.py"

timeout /t 3 >nul

echo.
echo [3/3] Creating public tunnel...
echo.
echo IMPORTANT: If this asks for authtoken, get it from:
echo https://dashboard.ngrok.com/get-started/your-authtoken
echo Then run: ngrok config add-authtoken YOUR_TOKEN
echo.
ngrok http 5000

echo.
echo If ngrok is not installed, download it from https://ngrok.com/download
pause
