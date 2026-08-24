"""
Wallet+ Public Server Launcher
This starts your Flask app so it can be accessed from anywhere using ngrok.

How to use:
1. Make sure you have internet.
2. Run: python start_public.py
3. It will start the server + create a public HTTPS link (via ngrok).
4. Share the https://....ngrok-free.app link with anyone.

Requirements:
- pip install pyngrok flask requests   (run once)
- For persistent free tunnels you may need a free ngrok account (https://ngrok.com)

Security warning:
This exposes your app to the internet. The default admin password is weak.
Change it before sharing widely. This is for testing / personal use only.
"""

import os
import sys
import threading
import time
from app import app

def start_flask():
    port = int(os.environ.get("PORT", 5000))
    print(f"\n🚀 Starting Wallet+ on http://0.0.0.0:{port}")
    print("   (Accessible from this computer and via tunnel)\n")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

def try_start_ngrok_tunnel(port=5000):
    try:
        from pyngrok import ngrok, conf
        print("🌍 Setting up public tunnel with ngrok...")

        # Optional: set your ngrok authtoken here if you have one
        # conf.get_default().auth_token = "YOUR_TOKEN_HERE"

        # Kill any old tunnels
        ngrok.kill()

        public_url = ngrok.connect(port, "http").public_url
        print("\n" + "="*60)
        print("✅ PUBLIC LINK READY!")
        print(f"   Share this with anyone in the world:")
        print(f"   {public_url}")
        print("="*60 + "\n")
        print("Keep this window open. The link works while this script is running.")
        print("Press Ctrl+C to stop the server and tunnel.\n")
        return public_url
    except ImportError:
        print("\n⚠️  pyngrok not installed.")
        print("   Run this once:  pip install pyngrok")
        print("   Then re-run: python start_public.py\n")
        print("Alternative (manual):")
        print("   1. Download ngrok from https://ngrok.com/download")
        print("   2. Run: ngrok http 5000")
        print("   3. Copy the https link it gives you.\n")
        return None
    except Exception as e:
        print(f"\n⚠️  Could not create ngrok tunnel: {e}")
        print("   You can still access it locally or set up ngrok manually.\n")
        return None

if __name__ == "__main__":
    print("Wallet+ Public Access Launcher")
    print("-" * 40)

    # Start Flask in background thread
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()

    # Give Flask a moment to start
    time.sleep(1.5)

    # Try to create public tunnel
    public_url = try_start_ngrok_tunnel(5000)

    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        try:
            from pyngrok import ngrok
            ngrok.kill()
        except:
            pass
        print("Server stopped.")
        sys.exit(0)
