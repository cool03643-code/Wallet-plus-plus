# Wallet+ - Trust Wallet Inspired Crypto Wallet

A fully functional crypto wallet with beautiful Trust Wallet-like interface, live CoinGecko prices, admin control panel, loading screens, smooth transitions, and responsive design for both mobile and desktop.

## Features Implemented
- Beautiful dark Trust-style UI with smooth animations
- Loading screen on app start
- "Welcome, [Name]" message with owner name at the top
- User registration (email, name, password)
- Multiple wallet accounts support
- Live real-time prices for all major coins (CoinGecko)
- Full Admin panel with:
  - Balance adjustment
  - Enable/disable Send & Swap
  - View user credentials
  - Activity logging
- Responsive (bottom nav on mobile, clean layout on PC)
- Instant data persistence (SQLite)

## How to Run

1. Make sure Python 3.12+ is installed
2. Open terminal in this folder and run:

```bash
pip install flask requests
python app.py
```

3. Open your browser and go to: http://localhost:5000

**Demo Accounts:**
- **Admin**: `admin@wallet.com` / `admin123`
- Register new users normally

## Deployment (GitHub + Hosting)

This is a **Python Flask** app. It cannot run on Cloudflare Pages / Wrangler (those only support static sites or JavaScript).

### Recommended Path: GitHub → Render (or Railway)

1. Push this folder to a new GitHub repository.
2. Deploy on **Render.com** (free tier works well):
   - Connect your GitHub repo
   - It will auto-detect the included `render.yaml`
   - Or manually set:
     - Build: `pip install -r requirements.txt`
     - Start: `gunicorn --bind 0.0.0.0:$PORT app:app`
3. Alternative: Railway.app also works with the included `railway.json` + `Procfile`.

See [DEPLOYMENT.md](DEPLOYMENT.md) for full step-by-step instructions.

### Current Public Access (No Hosting Change)
Run these two commands in separate terminals:

```bash
python app.py
ssh -R 80:localhost:5000 nokey@localhost.run
```

This gives a public link (e.g. https://xxxx.lhr.life) that works immediately.

### Cloudflare Limitation
Cloudflare build will only serve the static fallback in the `public/` folder.  
The real wallet (login, dashboard, admin, database, Send/Swap/Receive) requires a Python backend.

## Next Steps (You can request changes)
- Add real transaction simulation
- Add more coins and charts
- Convert to Next.js when Node.js is available
- Add password encryption improvements

Enjoy your new Wallet+!

Built with all your specifications as of 2026-08-11.
You can now test it and tell me what to change or improve.