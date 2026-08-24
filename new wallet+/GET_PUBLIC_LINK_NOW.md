# Get a Public Link RIGHT NOW (Step by Step)

Your server is currently running on this computer.

## What you have right now
- Local access: http://127.0.0.1:5000
- Possible LAN IP: http://195.189.96.116:5000 (only works on same network usually)

To make it accessible from **anywhere in the world**, you need a tunnel.

---

## FASTEST: Use ngrok (Free)

### 1. Get a free ngrok account (30 seconds)
1. Go to: https://dashboard.ngrok.com/signup
2. Sign up with Google, GitHub, or email (free)

### 2. Get your authtoken
1. After logging in, go to: https://dashboard.ngrok.com/get-started/your-authtoken
2. Copy the long token (it starts with `2...`)

### 3. Add the token on your computer
Open a **new** PowerShell window and run:

```powershell
cd "c:\Users\User21\Desktop\new wallet+"
python -m pip install pyngrok --quiet
ngrok config add-authtoken PASTE_YOUR_TOKEN_HERE
```

Example:
```powershell
ngrok config add-authtoken 2abc123xyz...
```

### 4. Start the public server
In the same terminal, run:

```powershell
python start_public.py
```

You should now see something like:
```
✅ PUBLIC LINK READY!
   Share this with anyone in the world:
   https://random-words-1234.ngrok-free.app
```

Copy that `https://...ngrok-free.app` link and send it to anyone.

Keep the window open.

---

## Alternative: Cloudflare Tunnel (No account needed for basic use)

1. Download cloudflared:
   https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe

2. Rename the downloaded file to `cloudflared.exe` and put it in this folder:
   `c:\Users\User21\Desktop\new wallet+`

3. Open a terminal here and run:

```powershell
cd "c:\Users\User21\Desktop\new wallet+"
cloudflared.exe tunnel --url http://localhost:5000
```

It will print a link like:
`https://your-tunnel-name.trycloudflare.com`

Share that link.

---

## Important Notes

- Your computer must stay **ON** and connected to internet.
- The link only works while the script is running.
- To stop: Press `Ctrl + C` in the terminal.
- **Security**: Change the admin password before sharing widely.

To change admin password quickly, edit `app.py` around line 105 and restart.

The server is already running on port 5000. Just add the tunnel on top.

Let me know what link you get or if you hit any error!
