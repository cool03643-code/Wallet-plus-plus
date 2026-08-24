# Cloudflare Pages - Static Only Fallback

This project is a full Python Flask application.

Cloudflare Pages / Wrangler can ONLY serve static files or run JavaScript (Workers / Pages Functions).

## What happens if you deploy to Cloudflare Pages

- The build will succeed using the files in the `public/` folder.
- Visitors will see a simple page explaining that this is only the static part.
- None of the real features will work:
  - No login
  - No dashboard
  - No Send / Swap / Receive
  - No admin panel
  - No database

## When Cloudflare is actually useful here

1. **Cloudflare Tunnel** (recommended if you want Cloudflare domain)
   Run on your computer while the app is running:

   ```bash
   cloudflared tunnel --url http://localhost:5000
   ```

   This gives you a `https://something.trycloudflare.com` link that points to your local Flask server.

2. **Full rewrite** (advanced)
   Move the frontend to static + use Cloudflare Workers + D1 database + KV.
   This would be a completely different architecture.

## Current recommended hosting for this app

- Render (free)
- Railway (free tier)
- Fly.io
- Any Python-capable host

See DEPLOYMENT.md for exact steps after pushing to GitHub.
