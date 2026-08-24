# How to Make Wallet+ Accessible to Anyone in the World

## ⚠️ IMPORTANT SECURITY WARNINGS
- This exposes your app to the **entire internet**.
- The default admin password is `admin123` — **change it immediately** if you share the link.
- Your computer must stay on and connected to the internet.
- This is for testing/personal use. For real use, deploy to a proper host (Railway, Render, etc.).
- Anyone with the link can register, login, and use the wallet features.

## Easiest Way: Use ngrok (Recommended)

### Step 1: Install ngrok
1. Go to https://ngrok.com
2. Sign up for a free account
3. Download ngrok for Windows
4. Unzip it and put `ngrok.exe` somewhere easy (e.g. C:\ngrok)
5. Add that folder to your PATH, or just run it from that folder.

### Step 2: Get your authtoken (free)
After signing up, copy your authtoken from the ngrok dashboard.

Run this once in terminal (replace YOUR_TOKEN):
```
ngrok config add-authtoken YOUR_TOKEN
```

### Step 3: Start your Wallet+ with a public link

**Option A - Quick (recommended):**
```powershell
cd "c:\Users\User21\Desktop\new wallet+"
python start_public.py
```

This will:
- Start the Flask server
- Automatically create a public HTTPS link like `https://abc123.ngrok-free.app`

**Option B - Manual:**
Open two terminals:

Terminal 1 (start the app):
```powershell
cd "c:\Users\User21\Desktop\new wallet+"
python -m pip install -r requirements.txt
python app.py
```

Terminal 2 (create public tunnel):
```powershell
ngrok http 5000
```

Copy the `https://...ngrok-free.app` link that appears.

## Alternative: Cloudflare Tunnel (also free, no signup for basic use)

1. Download cloudflared: https://github.com/cloudflare/cloudflared/releases
2. Run:
   ```
   cloudflared tunnel --url http://localhost:5000
   ```
3. It will give you a public link.

## For People on the Same WiFi (No Tunnel Needed)

1. Find your computer's IP (it will be shown when you run the app).
2. On the same WiFi, go to: `http://YOUR_IP:5000`
   Example: `http://192.168.1.45:5000`

Note: This does **not** work for people outside your home network.

## After Starting

- Keep the terminal window open.
- The link only works while the script is running.
- To stop: Press Ctrl + C in the terminal.

## Quick Security Hardening (Do This Before Sharing)

Edit `app.py` and change these lines:

```python
app.secret_key = 'CHANGE_THIS_TO_SOMETHING_LONG_AND_RANDOM_1234567890abcdef'

# In init_db(), change the admin password:
admin_hash = hashlib.sha256('YOUR_NEW_STRONG_PASSWORD'.encode()).hexdigest()
```

Then restart the server.

## Demo Accounts (after you change the password)
- Admin: admin@wallet.com / (whatever you set)
- New users can register normally.

## Troubleshooting

- "Address already in use": Close other copies of the app or change port.
- Link doesn't work: Make sure ngrok is running and the Flask app is on port 5000.
- Old Row.get errors: Make sure you restarted the server after the latest changes.

Enjoy! The public link will let anyone access it from anywhere.
