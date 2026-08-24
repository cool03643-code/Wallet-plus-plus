# DO THIS NOW — GitHub + Cloudflare Deployment

## 1. Install Git (one time)

Download and install Git for Windows:
https://git-scm.com/download/win

After installation:
- Restart VS Code (or close and reopen PowerShell)
- Come back to this folder

## 2. Initialize Git and Prepare for Push

Open **PowerShell** in this folder and run:

```powershell
cd "c:\Users\User21\Desktop\new wallet+"

# Option A - Use the helper script (recommended)
.\git-setup.ps1

# Option B - Manual commands
git init
git branch -M main
git add .
git commit -m "Initial Wallet+ commit - ready for GitHub + Cloudflare"
```

## 3. Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `wallet-plus` (or anything you like)
3. **Important**: Leave all checkboxes UNCHECKED:
   - Do NOT add README
   - Do NOT add .gitignore
   - Do NOT add license
4. Click "Create repository"

## 4. Push to GitHub

After creating the repo, run these commands (replace YOUR_USERNAME):

```powershell
git remote add origin https://github.com/YOUR_USERNAME/wallet-plus.git
git push -u origin main
```

## 5. Deploy Options

### A. For a REAL working app (recommended)

- Go to https://render.com → New Web Service → Connect your GitHub repo
- It will auto-detect render.yaml
- Or use Railway: https://railway.app

### B. Cloudflare Pages (static placeholder only)

After the push:

1. Cloudflare Dashboard → Pages → Create a project → Connect to Git
2. Select your `wallet-plus` repo
3. Use these exact settings:
   - Framework preset: None
   - Build command: `npm run build`
   - Build output directory: `public`
   - Root directory: `/` (or leave empty)
4. Save and Deploy

You will get a URL like `https://wallet-plus-xxx.pages.dev`  
It will only show a notice page. The real Flask features will not work.

## Current Status (already done for you)

- All Cloudflare static files prepared (`public/`, `wrangler.toml`, workflow)
- `render.yaml` and Railway files ready
- `.gitignore` protects wallet.db and venv
- Server is running without the old sqlite3.Row crash
- Helper scripts created: `PUSH_TO_GITHUB.bat` and `git-setup.ps1`

## Quick Test Right Now

The app is running locally:
- http://127.0.0.1:5000
- Login: admin@wallet.com / admin123

Run the tunnel for a public link (in a second terminal):
```powershell
ssh -R 80:localhost:5000 nokey@localhost.run
```

After you complete steps 1-4 above, tell me the GitHub repo URL and I can help with the next deployment step.
