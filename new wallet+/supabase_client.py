import os
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

def is_supabase_configured():
    """Check if valid Supabase URL and Anon Key are set."""
    return bool(SUPABASE_URL and SUPABASE_ANON_KEY and 
                "your-project-id" not in SUPABASE_URL and 
                "your-supabase-anon-public-key" not in SUPABASE_ANON_KEY)

def get_github_oauth_url(redirect_to=None):
    """Generate GitHub OAuth sign-in URL via Supabase Auth."""
    if not is_supabase_configured():
        return None
    
    endpoint = f"{SUPABASE_URL.rstrip('/')}/auth/v1/authorize"
    params = {
        "provider": "github",
        "redirect_to": redirect_to or "http://localhost:5000/auth/callback"
    }
    req = requests.Request('GET', endpoint, params=params).prepare()
    return req.url

def exchange_code_for_session(auth_code):
    """Exchange authorization code or refresh token with Supabase Auth."""
    if not is_supabase_configured():
        return None, "Supabase credentials are not configured in .env"
    
    url = f"{SUPABASE_URL.rstrip('/')}/auth/v1/token?grant_type=pkce"
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "auth_code": auth_code
    }
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json(), None
        else:
            return None, res.text
    except Exception as e:
        return None, str(e)

def get_user_profile(access_token):
    """Get current logged-in user profile from Supabase Auth."""
    if not is_supabase_configured():
        return None, "Supabase not configured"
        
    url = f"{SUPABASE_URL.rstrip('/')}/auth/v1/user"
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {access_token}"
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json(), None
        else:
            return None, res.text
    except Exception as e:
        return None, str(e)
