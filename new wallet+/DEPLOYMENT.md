# Wallet+ Deployment Guide

This is a **Python Flask** application. It cannot be deployed with Cloudflare Pages / Wrangler build because those only support static sites or JavaScript Workers.

Below are the correct ways to deploy after pushing to GitHub.

---

## Step 1: Push to GitHub (Recommended First Step)

1. Create a new repository on GitHub (do **not** initialize with README).
2. On your computer, open **PowerShell or Terminal** in this folder and run:

```bash
cd "c:\Users\User21\Desktop\new wallet+"

# Initialize git (if not already done)
git init
git add .
git commit -m "Initial Wallet+ commit"

# Add your GitHub repo (replace with your actual URL)
git remote add origin https://github.com/YOUR_USERNAME/wallet-plus.git
git branch -M main
git push -u origin main
```

3. Refresh GitHub — your code should now be there.

---

## Step 2: Deploy the Real Working App (Choose One)

### Option A: Render (Easiest & Free - Recommended)

1. Go to: https://render.com
2. Sign up with GitHub.
3. Click **"New +"** → **"Web Service"**.
4. Connect your GitHub repo (`wallet-plus`).
5. Render should auto-detect:
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn --bind 0.0.0.0:$PORT app:app`
6. (Optional) Add these environment variables:
   - `PYTHON_VERSION` = `3.11.0`
   - `FLASK_ENV` = `production`
7. Click **Create Web Service**.

Render will give you a public URL like: `https://wallet-plus-xxxx.onrender.com`

The `render.yaml` file in this repo helps with automatic configuration.

---

### Option B: Railway

1. Go to: https://railway.app
2. Sign in with GitHub.
3. Click **"New Project"** → **"Deploy from GitHub Repo"**.
4. Select your `wallet-plus` repo.
5. Railway will detect the `railway.json` and `Procfile`.
6. It should automatically run `gunicorn --bind 0.0.0.0:$PORT app:app`.

---

### Option C: Keep Using Temporary Public Link (No Hosting Change)

You can keep using the current working method:

1. Terminal 1:
   ```bash
   python app.py
   ```

2. Terminal 2 (new window):
   ```bash
   ssh -R 80:localhost:5000 nokey@localhost.run
   ```

This gives you a link like `https://xxxx.lhr.life` that anyone can access.

---

## Why Cloudflare Pages / Wrangler Build Will NOT Work

- Cloudflare Pages expects static HTML/CSS/JS or a Workers project.
- This app needs:
  - Python runtime
  - Flask server
  - SQLite database writes
  - Server-side sessions
- When you tried `npx wrangler deploy`, it failed with "Could not detect a directory containing static files".

### What you CAN do with Cloudflare:

- Use **Cloudflare Tunnel** (`cloudflared`) to expose your local machine publicly (no code change).
- Or completely rewrite the frontend as a static site + move backend to Cloudflare Workers + D1 (major rewrite).

We have prepared a static fallback in the `public/` folder so a Cloudflare Pages build won't completely explode, but **the real wallet features will not work**.

### If you still want to try Cloudflare Pages (static placeholder only)

After pushing to GitHub:

1. In Cloudflare Dashboard → Pages → Create project → Connect Git
2. Use these exact settings:
   - Framework preset: None
   - Build command: `npm run build`
   - Build output directory: `public`
   - Root directory: `/` (or leave empty)

See the file `CLOUDFLARE_PAGES_SETTINGS.txt` for copy-paste instructions.

The deployed site will only show a notice page. The real app stays on Render/Railway or your localhost tunnel.

---

## Current Working Public Access

As long as your computer is on and the two terminals are running, people can use the app via the localhost.run link.

---

## Files Prepared for Deployment

- `render.yaml` — for Render.com
- `railway.json` + `Procfile` — for Railway
- `.gitignore` — prevents uploading wallet.db and venv
- `requirements.txt` — Python dependencies
- `public/index.html` + `wrangler.toml` — only for Cloudflare static fallback

---

## After Deployment

- Change the secret key in `app.py` before going live:
  ```python
  app.secret_key = 'put-a-long-random-string-here'
  ```

- For production, consider switching from SQLite to Postgres (Render and Railway both offer free Postgres).

Let me know which platform you want to use and I can give more specific steps.
