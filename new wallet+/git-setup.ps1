# Wallet+ - Git + GitHub Setup Script (PowerShell)
# Run this AFTER installing Git for Windows.

Write-Host "=== Wallet+ GitHub Setup ===" -ForegroundColor Cyan
Write-Host ""

$repoPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoPath

# Check git
try {
    $gitVersion = git --version
    Write-Host "Git found: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Git is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Please install from: https://git-scm.com/download/win" -ForegroundColor Yellow
    Write-Host "Then restart VS Code / PowerShell and run this script again." -ForegroundColor Yellow
    pause
    exit 1
}

# Initialize if needed
if (-not (Test-Path ".git")) {
    Write-Host "Initializing git repository..." -ForegroundColor Yellow
    git init
    git branch -M main
} else {
    Write-Host "Git repository already exists." -ForegroundColor Green
}

# Add everything
Write-Host "Adding files..." -ForegroundColor Yellow
git add .

# Commit
$commitMsg = "Initial Wallet+ commit - ready for GitHub + Cloudflare static build"
try {
    git commit -m $commitMsg
    Write-Host "Commit created." -ForegroundColor Green
} catch {
    Write-Host "No new changes to commit (or commit already exists)." -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "NEXT STEPS:" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Create a new EMPTY repository on GitHub:" -ForegroundColor White
Write-Host "   https://github.com/new" -ForegroundColor Gray
Write-Host "   - Name it: wallet-plus (or similar)"
Write-Host "   - Do NOT check 'Add a README file'"
Write-Host "   - Do NOT add .gitignore or license"
Write-Host ""
Write-Host "2. Run these commands (replace YOUR_USERNAME):" -ForegroundColor White
Write-Host ""
Write-Host "   git remote add origin https://github.com/YOUR_USERNAME/wallet-plus.git" -ForegroundColor Yellow
Write-Host "   git push -u origin main" -ForegroundColor Yellow
Write-Host ""
Write-Host "3. After push succeeds, connect the repo to:" -ForegroundColor White
Write-Host "   - Render.com (recommended for full working app)" -ForegroundColor Green
Write-Host "   - OR Railway.app" -ForegroundColor Green
Write-Host ""
Write-Host "   For Cloudflare Pages (static only):" -ForegroundColor Yellow
Write-Host "   See CLOUDFLARE_PAGES_SETTINGS.txt" -ForegroundColor Gray
Write-Host ""
Write-Host "Full guide: DEPLOYMENT.md" -ForegroundColor Cyan
Write-Host ""
pause
