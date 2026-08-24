@echo off
echo ============================================
echo   Wallet+ - Push to GitHub
echo ============================================
echo.

cd /d "%~dp0"

set "PATH=%PATH%;C:\Users\User21\AppData\Local\Programs\Git\cmd;C:\Program Files\Git\cmd"

echo Checking for Git...
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Git is not found.
    echo Please restart your terminal or VS Code.
    pause
    exit /b 1
)

echo Git found!
echo.

if not exist ".git" (
    echo Initializing Git repository...
    git init
    git branch -M main
)

echo Adding files and committing...
git add .
git commit -m "Initial commit with Supabase & GitHub Auth" 2>nul

echo.
echo Setting remote repository...
git remote remove origin 2>nul
git remote add origin https://github.com/cool03643-code/wallet-plus.git

echo.
echo Pushing code to GitHub...
git push -u origin main

echo.
echo ============================================
echo DONE! Check https://github.com/cool03643-code/wallet-plus
echo ============================================
pause
