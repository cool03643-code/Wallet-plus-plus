from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import sqlite3
import requests
import json
from datetime import datetime
import hashlib
import os
import random
import re
import traceback
from functools import wraps

import supabase_client

try:
    from web3 import Web3
except ImportError:
    Web3 = None

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'walletplus_super_secret_key_2026')

# Optional real RPC for live external balances (Sepolia recommended)
ETH_RPC_URL = os.getenv('ETH_RPC_URL', '').strip()
ETH_CHAIN_ID = int(os.getenv('ETH_CHAIN_ID', '11155111'))  # Sepolia default
w3 = None
if ETH_RPC_URL and Web3:
    try:
        w3 = Web3(Web3.HTTPProvider(ETH_RPC_URL))
        if not w3.is_connected():
            print("[WARN] ETH RPC not connected")
            w3 = None
    except Exception as e:
        print("[WARN] Failed to init web3:", e)
        w3 = None


# ====================== DATABASE SETUP ======================
def init_db():
    conn = sqlite3.connect('wallet.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        name TEXT,
        email TEXT UNIQUE,
        password_hash TEXT,
        role TEXT DEFAULT 'user',
        created_at TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS wallets (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        name TEXT,
        address TEXT,
        send_enabled INTEGER DEFAULT 1,
        swap_enabled INTEGER DEFAULT 1,
        is_frozen INTEGER DEFAULT 0,
        receive_address TEXT DEFAULT '',
        created_at TEXT
    )''')
    
    # Add receive_address column if it doesn't exist (for existing DBs)
    try:
        c.execute("ALTER TABLE wallets ADD COLUMN receive_address TEXT DEFAULT ''")
    except:
        pass

    # External wallet connection columns (for "Connect to Wallet" feature)
    try:
        c.execute("ALTER TABLE wallets ADD COLUMN external_address TEXT DEFAULT ''")
    except:
        pass
    try:
        c.execute("ALTER TABLE wallets ADD COLUMN external_provider TEXT DEFAULT ''")
    except:
        pass
    try:
        c.execute("ALTER TABLE wallets ADD COLUMN external_balances TEXT DEFAULT '{}'")
    except:
        pass
    
    c.execute('''CREATE TABLE IF NOT EXISTS holdings (
        id INTEGER PRIMARY KEY,
        wallet_id INTEGER,
        coin_id TEXT,
        symbol TEXT,
        amount REAL DEFAULT 0.0
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY,
        wallet_id INTEGER,
        type TEXT,
        coin_id TEXT,
        amount REAL,
        usd_value REAL,
        timestamp TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS admin_logs (
        id INTEGER PRIMARY KEY,
        admin_id INTEGER,
        action TEXT,
        target_user_id INTEGER,
        details TEXT,
        timestamp TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS user_verification (
        user_id INTEGER PRIMARY KEY,
        is_verified INTEGER DEFAULT 1,
        steps TEXT DEFAULT '[]',
        submitted_at TEXT,
        reviewed_at TEXT
    )''')
    
    # Create default admin account (email: admin@wallet.com, password: admin123)
    admin_hash = hashlib.sha256('admin123'.encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users (name, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
              ("Admin Owner", "admin@wallet.com", admin_hash, "admin", datetime.now().isoformat()))
    
    # Ensure admin has at least one wallet with 0-balance coins
    admin_user = c.execute("SELECT id FROM users WHERE email = 'admin@wallet.com'").fetchone()
    if admin_user:
        admin_id = admin_user[0]
        existing_wallets = c.execute("SELECT id FROM wallets WHERE user_id = ?", (admin_id,)).fetchall()
        if not existing_wallets:
            address = f"0x{random.randint(100000, 999999):06x}...{random.randint(1000,9999)}"
            c.execute("INSERT INTO wallets (user_id, name, address, created_at) VALUES (?, ?, ?, ?)",
                      (admin_id, "Admin Main Wallet", address, datetime.now().isoformat()))
            wallet_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
            popular_coins = [('bitcoin', 'BTC'), ('ethereum', 'ETH'), ('solana', 'SOL'), ('cardano', 'ADA'), ('ripple', 'XRP'), ('dogecoin', 'DOGE')]
            for coin_id, symbol in popular_coins:
                c.execute("INSERT INTO holdings (wallet_id, coin_id, symbol, amount) VALUES (?, ?, ?, 0.0)",
                          (wallet_id, coin_id, symbol))
    
    conn.commit()
    conn.close()

init_db()

# ====================== HELPER FUNCTIONS ======================
def dict_factory(cursor, row):
    """Convert sqlite3.Row to plain dict so .get() and template access always work."""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def get_db():
    # timeout helps avoid 'database is locked' under concurrent writes (Flask dev server, quick admin+user actions)
    conn = sqlite3.connect('wallet.db', timeout=10)
    conn.row_factory = dict_factory
    return conn

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ====================== COINGECKO LIVE DATA ======================
def get_live_prices(coin_ids=None):
    """Return live prices with strong fallback so it always looks good."""
    fallback_prices = {
        'bitcoin':  {'usd': 67250, 'usd_24h_change': 1.8,  'symbol': 'BTC', 'name': 'Bitcoin'},
        'ethereum': {'usd': 2650,  'usd_24h_change': 2.4,  'symbol': 'ETH', 'name': 'Ethereum'},
        'solana':   {'usd': 158,   'usd_24h_change': -0.9, 'symbol': 'SOL', 'name': 'Solana'},
        'cardano':  {'usd': 0.36,  'usd_24h_change': 3.1,  'symbol': 'ADA', 'name': 'Cardano'},
        'ripple':   {'usd': 0.52,  'usd_24h_change': 0.7,  'symbol': 'XRP', 'name': 'Ripple'},
        'dogecoin': {'usd': 0.12,  'usd_24h_change': -1.2, 'symbol': 'DOGE','name': 'Dogecoin'},
    }

    try:
        if not coin_ids:
            url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=50&page=1&sparkline=false"
            response = requests.get(url, timeout=8)
            if response.status_code == 200:
                data = response.json()
                result = {}
                for coin in data:
                    result[coin['id']] = {
                        'usd': coin.get('current_price', 0),
                        'usd_24h_change': coin.get('price_change_percentage_24h', 0),
                        'symbol': coin.get('symbol', '').upper(),
                        'name': coin.get('name', coin['id'])
                    }
                # Merge fallback for coins we care about
                for k, v in fallback_prices.items():
                    if k not in result:
                        result[k] = v
                return result
        else:
            ids = ','.join(coin_ids)
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true"
            response = requests.get(url, timeout=6)
            if response.status_code == 200:
                raw = response.json()
                result = {}
                for cid in coin_ids:
                    info = raw.get(cid, {})
                    result[cid] = {
                        'usd': info.get('usd', fallback_prices.get(cid, {}).get('usd', 0)),
                        'usd_24h_change': info.get('usd_24h_change', fallback_prices.get(cid, {}).get('usd_24h_change', 0)),
                        'symbol': fallback_prices.get(cid, {}).get('symbol', cid[:4].upper()),
                        'name': fallback_prices.get(cid, {}).get('name', cid.capitalize())
                    }
                return result
    except Exception as e:
        print("Price API error (using fallback):", e)

    # Return fallback for requested coins or all popular
    if coin_ids:
        return {cid: fallback_prices.get(cid, {'usd': 0, 'usd_24h_change': 0, 'symbol': cid[:4].upper(), 'name': cid.capitalize()}) for cid in coin_ids}
    return fallback_prices


def get_external_wallet_balances(address):
    """Return balances for a connected external wallet.
    If ETH_RPC_URL is configured, we query the real on-chain ETH balance for EVM addresses.
    Other chains still return 0 until additional RPCs are added.
    """
    if not address:
        return {}
    balances = {
        'bitcoin':  0.0,
        'ethereum': 0.0,
        'solana':   0.0,
        'cardano':  0.0,
        'ripple':   0.0,
        'dogecoin': 0.0,
    }
    # Real ETH balance via configured RPC (Sepolia or mainnet)
    if w3 and address.lower().startswith('0x'):
        try:
            checksum = w3.to_checksum_address(address)
            wei = w3.eth.get_balance(checksum)
            eth = float(w3.from_wei(wei, 'ether'))
            balances['ethereum'] = round(eth, 8)
        except Exception as e:
            print("RPC balance query failed for", address[:10], ":", e)
    return balances


def get_all_coins():
    try:
        response = requests.get("https://api.coingecko.com/api/v3/coins/list", timeout=10)
        if response.status_code == 200:
            return response.json()[:200]  # Limit for performance
        return []
    except:
        return []

# ====================== VERIFICATION FUNCTIONS ======================
def get_verification(user_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM user_verification WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    if row:
        try:
            steps = json.loads(row['steps']) if row['steps'] else []
        except:
            steps = []
        return {
            'is_verified': bool(row['is_verified']),
            'steps': steps,
            'submitted_at': row['submitted_at'],
            'reviewed_at': row['reviewed_at']
        }
    return {'is_verified': True, 'steps': [], 'submitted_at': None, 'reviewed_at': None}

def set_verification(user_id, is_verified, steps=None):
    conn = get_db()
    steps_json = json.dumps(steps or []) if steps is not None else None
    existing = conn.execute("SELECT 1 FROM user_verification WHERE user_id = ?", (user_id,)).fetchone()
    if existing:
        if steps_json is not None:
            conn.execute("UPDATE user_verification SET is_verified = ?, steps = ?, reviewed_at = ? WHERE user_id = ?",
                         (1 if is_verified else 0, steps_json, datetime.now().isoformat(), user_id))
        else:
            conn.execute("UPDATE user_verification SET is_verified = ?, reviewed_at = ? WHERE user_id = ?",
                         (1 if is_verified else 0, datetime.now().isoformat(), user_id))
    else:
        conn.execute("INSERT INTO user_verification (user_id, is_verified, steps, reviewed_at) VALUES (?, ?, ?, ?)",
                     (user_id, 1 if is_verified else 0, steps_json or '[]', datetime.now().isoformat()))
    conn.commit()
    conn.close()

def ensure_verification_record(user_id):
    conn = get_db()
    existing = conn.execute("SELECT 1 FROM user_verification WHERE user_id = ?", (user_id,)).fetchone()
    if not existing:
        conn.execute("INSERT INTO user_verification (user_id, is_verified, steps) VALUES (?, 1, '[]')", (user_id,))
        conn.commit()
    conn.close()

# ====================== ROUTES ======================
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        password_hash = hash_password(password)
        
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ? AND password_hash = ?", 
                           (email, password_hash)).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['name'] = user['name']
            session['role'] = user['role']
            flash(f"Welcome back, {user['name']}!")
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials')
    
    supabase_configured = supabase_client.is_supabase_configured()
    return render_template('login.html', supabase_configured=supabase_configured)

@app.route('/auth/login/github')
def login_github():
    """Initiate GitHub OAuth login via Supabase."""
    if not supabase_client.is_supabase_configured():
        flash('Supabase is not configured yet. Please set SUPABASE_URL and SUPABASE_ANON_KEY in your .env file.')
        return redirect(url_for('login'))
    
    app_url = os.getenv('APP_BASE_URL', 'http://localhost:5000').rstrip('/')
    callback_url = f"{app_url}/auth/callback"
    oauth_url = supabase_client.get_github_oauth_url(redirect_to=callback_url)
    return redirect(oauth_url)

@app.route('/auth/callback')
def auth_callback():
    """Handle OAuth redirect callback from Supabase."""
    code = request.args.get('code')
    token = request.args.get('access_token')
    
    # If PKCE code provided
    if code:
        data, err = supabase_client.exchange_code_for_session(code)
        if err:
            flash(f'GitHub login failed: {err}')
            return redirect(url_for('login'))
        token = data.get('access_token')

    if not token:
        # Client-side hash fragment verification template (for standard OAuth flows)
        return render_template('auth_callback.html')

    user_info, err = supabase_client.get_user_profile(token)
    if err or not user_info:
        flash('Failed to retrieve GitHub user profile from Supabase.')
        return redirect(url_for('login'))

    email = user_info.get('email')
    name = user_info.get('user_metadata', {}).get('full_name') or user_info.get('user_metadata', {}).get('user_name') or email or 'GitHub User'
    
    conn = get_db()
    existing_user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    
    if existing_user:
        user_id = existing_user['id']
        role = existing_user['role']
    else:
        created_at = datetime.now().isoformat()
        dummy_hash = hash_password(f"github_oauth_{user_info.get('id')}")
        conn.execute("INSERT INTO users (name, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
                     (name, email, dummy_hash, 'user', created_at))
        user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        role = 'user'
        
        # Create default main wallet
        address = f"0x{random.randint(100000, 999999):06x}...{random.randint(1000,9999)}"
        conn.execute("INSERT INTO wallets (user_id, name, address, created_at) VALUES (?, ?, ?, ?)",
                     (user_id, "Main Wallet", address, created_at))
        wallet_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        
        popular_coins = [('bitcoin', 'BTC'), ('ethereum', 'ETH'), ('solana', 'SOL'), ('cardano', 'ADA'), ('ripple', 'XRP'), ('dogecoin', 'DOGE')]
        for coin_id, symbol in popular_coins:
            conn.execute("INSERT INTO holdings (wallet_id, coin_id, symbol, amount) VALUES (?, ?, ?, 0.0)",
                         (wallet_id, coin_id, symbol))
        conn.commit()

    conn.close()

    session['user_id'] = user_id
    session['name'] = name
    session['role'] = role
    session['supabase_token'] = token
    flash(f'Successfully logged in with GitHub as {name}!')
    return redirect(url_for('dashboard'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        password_hash = hash_password(password)
        created_at = datetime.now().isoformat()
        
        try:
            conn = get_db()
            conn.execute("INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                        (name, email, password_hash, created_at))
            user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            
            # Create default wallet
            address = f"0x{random.randint(100000, 999999):06x}...{random.randint(1000,9999)}"
            conn.execute("INSERT INTO wallets (user_id, name, address, created_at) VALUES (?, ?, ?, ?)",
                        (user_id, "Main Wallet", address, created_at))
            wallet_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            
            # Create holdings with 0 balance for popular coins
            popular_coins = [
                ('bitcoin', 'BTC'),
                ('ethereum', 'ETH'),
                ('solana', 'SOL'),
                ('cardano', 'ADA'),
                ('ripple', 'XRP'),
                ('dogecoin', 'DOGE')
            ]
            for coin_id, symbol in popular_coins:
                conn.execute("INSERT INTO holdings (wallet_id, coin_id, symbol, amount) VALUES (?, ?, ?, 0.0)",
                            (wallet_id, coin_id, symbol))
            
            conn.commit()
            conn.close()
            
            ensure_verification_record(user_id)
            
            flash('Account created successfully! Please login.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already exists')
    
    return render_template('register.html')

def ensure_user_has_wallet_and_holdings(user_id):
    """Make sure every user has at least one wallet with 0-balance popular coins.
    Always returns plain dicts (never sqlite3.Row) so .get() is safe everywhere.
    """
    conn = get_db()
    rows = conn.execute("SELECT * FROM wallets WHERE user_id = ?", (user_id,)).fetchall()
    wallets = [dict(r) if not isinstance(r, dict) else r for r in rows]

    if not wallets:
        address = f"0x{random.randint(100000, 999999):06x}...{random.randint(1000,9999)}"
        conn.execute("INSERT INTO wallets (user_id, name, address, created_at) VALUES (?, ?, ?, ?)",
                    (user_id, "Main Wallet", address, datetime.now().isoformat()))
        wallet_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        rows = conn.execute("SELECT * FROM wallets WHERE id = ?", (wallet_id,)).fetchall()
        wallets = [dict(r) if not isinstance(r, dict) else r for r in rows]
    
    # Ensure holdings exist for popular coins with 0 balance
    popular_coins = [
        ('bitcoin', 'BTC'), ('ethereum', 'ETH'), ('solana', 'SOL'),
        ('cardano', 'ADA'), ('ripple', 'XRP'), ('dogecoin', 'DOGE')
    ]
    for w in wallets:
        for coin_id, symbol in popular_coins:
            exists = conn.execute("SELECT 1 FROM holdings WHERE wallet_id = ? AND coin_id = ?", 
                                 (w['id'], coin_id)).fetchone()
            if not exists:
                conn.execute("INSERT INTO holdings (wallet_id, coin_id, symbol, amount) VALUES (?, ?, ?, 0.0)",
                            (w['id'], coin_id, symbol))
    conn.commit()
    conn.close()
    return wallets

@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    wallets = ensure_user_has_wallet_and_holdings(user_id)
    
    # Normalize to plain dicts (sqlite.Row does not support .get() or some template patterns)
    wallets = [dict(w) for w in wallets] if wallets else []
    
    conn = get_db()
    # Get all holdings for this user (convert to dicts for safe .get() usage)
    holdings = []
    for w in wallets:
        h = conn.execute("""
            SELECT h.*, w.name as wallet_name 
            FROM holdings h 
            JOIN wallets w ON h.wallet_id = w.id 
            WHERE h.wallet_id = ?
        """, (w['id'],)).fetchall()
        holdings.extend([dict(row) for row in h])
    conn.close()
    
    # Popular coins we always want to show
    popular = ['bitcoin', 'ethereum', 'solana', 'cardano', 'ripple', 'dogecoin']
    coin_ids = list(set([h['coin_id'] for h in holdings] + popular))
    prices = get_live_prices(coin_ids)
    
    # Calculate total portfolio value
    total_usd = 0.0
    for h in holdings:
        price = prices.get(h['coin_id'], {}).get('usd', 0) or 0
        total_usd += (h['amount'] or 0) * price
    
    # Build display list - always show popular coins with live prices
    display_coins = []
    seen = set()
    for cid in popular + [h['coin_id'] for h in holdings]:
        if cid in seen: continue
        seen.add(cid)
        price_info = prices.get(cid, {})
        user_amount = 0.0
        for h in holdings:
            if h['coin_id'] == cid:
                user_amount = h['amount'] or 0
                break
        display_coins.append({
            'coin_id': cid,
            'symbol': price_info.get('symbol', cid[:4].upper()),
            'name': price_info.get('name', cid.capitalize()),
            'price': price_info.get('usd', 0) or 0,
            'change': price_info.get('usd_24h_change', 0) or 0,
            'amount': user_amount,
            'value': user_amount * (price_info.get('usd', 0) or 0)
        })
    
    verification = get_verification(session['user_id'])
    
    # Final safety: guarantee plain dicts (prevents 'sqlite3.Row has no attribute get')
    wallets = [dict(w) if w and not isinstance(w, dict) else w for w in (wallets or [])]
    primary = wallets[0] if wallets else None
    if primary and not isinstance(primary, dict):
        primary = dict(primary)

    # Use .get() safely - wallets are now normalized to dicts
    send_enabled = bool(primary.get('send_enabled', 1)) if primary else True
    swap_enabled = bool(primary.get('swap_enabled', 1)) if primary else True
    receive_address = (primary.get('receive_address') or '') if primary else ''
    external_address = (primary.get('external_address') or '') if primary else ''
    external_provider = (primary.get('external_provider') or '') if primary else ''

    external_balances = {}
    if external_address:
        try:
            external_balances = json.loads(primary.get('external_balances') or '{}')
        except:
            external_balances = get_external_wallet_balances(external_address)

    # Merge external wallet balances into display so they appear "in this wallet"
    if external_balances:
        for coin in display_coins:
            ext_amt = external_balances.get(coin['coin_id'], 0) or 0
            if ext_amt:
                coin['amount'] = (coin['amount'] or 0) + ext_amt
                coin['value'] = coin['amount'] * (coin['price'] or 0)
                coin['from_external'] = True  # flag for UI badge

        # Also add any extra coins that only exist in the external wallet
        for cid, amt in external_balances.items():
            if amt and not any(c['coin_id'] == cid for c in display_coins):
                pinfo = prices.get(cid, {})
                display_coins.append({
                    'coin_id': cid,
                    'symbol': pinfo.get('symbol', cid[:4].upper()),
                    'name': pinfo.get('name', cid.capitalize()),
                    'price': pinfo.get('usd', 0) or 0,
                    'change': pinfo.get('usd_24h_change', 0) or 0,
                    'amount': amt,
                    'value': amt * (pinfo.get('usd', 0) or 0),
                    'from_external': True
                })

    # Recalculate total after merge
    total_usd = sum((c.get('value') or 0) for c in display_coins)
    
    return render_template('dashboard.html', 
                         name=session.get('name', 'User'),
                         wallets=wallets,
                         holdings=holdings,
                         prices=prices,
                         display_coins=display_coins,
                         total_usd=round(total_usd, 2),
                         verification=verification,
                         send_enabled=send_enabled,
                         swap_enabled=swap_enabled,
                         receive_address=receive_address,
                         external_address=external_address,
                         external_provider=external_provider,
                         external_balances=external_balances,
                         has_external_wallet=bool(external_address))

@app.route('/admin')
@admin_required
def admin_dashboard():
    ensure_user_has_wallet_and_holdings(session['user_id'])
    
    conn = get_db()
    users_raw = conn.execute("SELECT * FROM users").fetchall()
    logs = conn.execute("SELECT * FROM admin_logs ORDER BY timestamp DESC LIMIT 50").fetchall()
    conn.close()
    
    users = []
    for u in users_raw:
        ensure_verification_record(u['id'])
        ver = get_verification(u['id'])
        users.append({
            'id': u['id'],
            'name': u['name'],
            'email': u['email'],
            'role': u['role'],
            'created_at': u['created_at'],
            'verification': ver
        })
    
    prices = get_live_prices()
    return render_template('admin.html', users=users, logs=logs, prices=prices)

# ====================== ADMIN POWERFUL ACTIONS ======================
@app.route('/api/price/<coin_id>')
def get_price(coin_id):
    data = get_live_prices([coin_id])
    return jsonify(data)

@app.route('/api/admin/adjust_balance', methods=['POST'])
@admin_required
def adjust_balance():
    data = request.json
    user_id = data.get('user_id')
    coin_id = data.get('coin_id')
    new_amount = float(data.get('amount', 0))
    
    conn = get_db()
    # Find any wallet of this user and update/create holding
    wallet = conn.execute("SELECT id FROM wallets WHERE user_id = ? LIMIT 1", (user_id,)).fetchone()
    if wallet:
        wallet_id = wallet['id']
        existing = conn.execute("SELECT id FROM holdings WHERE wallet_id = ? AND coin_id = ?", (wallet_id, coin_id)).fetchone()
        if existing:
            conn.execute("UPDATE holdings SET amount = ? WHERE wallet_id = ? AND coin_id = ?", (new_amount, wallet_id, coin_id))
        else:
            conn.execute("INSERT INTO holdings (wallet_id, coin_id, symbol, amount) VALUES (?, ?, ?, ?)",
                        (wallet_id, coin_id, coin_id[:3].upper(), new_amount))
    
    conn.execute("INSERT INTO admin_logs (admin_id, action, target_user_id, details, timestamp) VALUES (?, ?, ?, ?, ?)",
                (session['user_id'], 'adjust_balance', user_id, json.dumps(data), datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': 'Balance updated'})

@app.route('/api/admin/toggle', methods=['POST'])
@admin_required
def toggle_feature():
    data = request.json
    wallet_id = data.get('wallet_id')
    feature = data.get('feature')  # 'send' or 'swap'
    
    conn = get_db()
    if feature == 'send':
        conn.execute("UPDATE wallets SET send_enabled = 1 - send_enabled WHERE id = ?", (wallet_id,))
    elif feature == 'swap':
        conn.execute("UPDATE wallets SET swap_enabled = 1 - swap_enabled WHERE id = ?", (wallet_id,))
    
    conn.execute("INSERT INTO admin_logs (admin_id, action, target_user_id, details, timestamp) VALUES (?, ?, ?, ?, ?)",
                (session['user_id'], f'toggle_{feature}', None, json.dumps(data), datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/api/admin/create_wallet', methods=['POST'])
@login_required
def create_wallet():
    data = request.json or {}
    name = data.get('name', 'New Wallet')
    user_id = session['user_id']
    
    conn = get_db()
    address = f"0x{random.randint(100000, 999999):06x}...{random.randint(1000,9999)}"
    conn.execute("INSERT INTO wallets (user_id, name, address, created_at) VALUES (?, ?, ?, ?)",
                (user_id, name, address, datetime.now().isoformat()))
    wallet_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    
    # Give 0 balance coins
    for coin_id, symbol in [('bitcoin','BTC'),('ethereum','ETH'),('solana','SOL')]:
        conn.execute("INSERT INTO holdings (wallet_id, coin_id, symbol, amount) VALUES (?, ?, ?, 0)", (wallet_id, coin_id, symbol))
    
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'wallet_id': wallet_id})

POPULAR_COINS = [
    ('bitcoin', 'BTC'), ('ethereum', 'ETH'), ('solana', 'SOL'),
    ('cardano', 'ADA'), ('ripple', 'XRP'), ('dogecoin', 'DOGE')
]

@app.route('/api/admin/get_user_data/<int:user_id>')
@admin_required
def get_user_data(user_id):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    wallets = conn.execute("SELECT * FROM wallets WHERE user_id = ?", (user_id,)).fetchall()

    # If no wallets, create one
    if not wallets:
        address = f"0x{random.randint(100000, 999999):06x}...{random.randint(1000,9999)}"
        conn.execute("INSERT INTO wallets (user_id, name, address, created_at) VALUES (?, ?, ?, ?)",
                    (user_id, "Main Wallet", address, datetime.now().isoformat()))
        conn.commit()
        wallets = conn.execute("SELECT * FROM wallets WHERE user_id = ?", (user_id,)).fetchall()

    # Force the 6 popular coins on every wallet (create with 0 if missing)
    for w in wallets:
        for coin_id, symbol in POPULAR_COINS:
            exists = conn.execute("SELECT 1 FROM holdings WHERE wallet_id=? AND coin_id=?", (w['id'], coin_id)).fetchone()
            if not exists:
                conn.execute("INSERT INTO holdings (wallet_id, coin_id, symbol, amount) VALUES (?, ?, ?, 0.0)",
                            (w['id'], coin_id, symbol))
    conn.commit()

    verification = get_verification(user_id)
    result = {
        'user': dict(user) if user else None,
        'wallets': []
    }
    for w in wallets:
        holdings_raw = conn.execute("SELECT * FROM holdings WHERE wallet_id = ?", (w['id'],)).fetchall()
        holdings = [dict(h) for h in holdings_raw]

        # Always return exactly the 6 popular coins
        final_holdings = []
        existing_map = {h['coin_id']: h for h in holdings}
        for coin_id, symbol in POPULAR_COINS:
            if coin_id in existing_map:
                final_holdings.append(existing_map[coin_id])
            else:
                final_holdings.append({
                    'id': None,
                    'wallet_id': w['id'],
                    'coin_id': coin_id,
                    'symbol': symbol,
                    'amount': 0.0
                })
        wdict = dict(w)
        wdict['receive_address'] = wdict.get('receive_address') or ''
        result['wallets'].append({
            'wallet': wdict,
            'holdings': final_holdings
        })
    result['verification'] = verification
    conn.close()
    return jsonify(result)


# ====================== SEND / SWAP / RECEIVE ACTIONS ======================
def log_transaction(wallet_id, tx_type, coin_id, amount, usd_value=0, conn=None):
    """Log a transaction. If conn is provided, use it (caller must commit/close). Otherwise open/close our own."""
    own = conn is None
    if own:
        conn = get_db()
    conn.execute("""INSERT INTO transactions (wallet_id, type, coin_id, amount, usd_value, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                 (wallet_id, tx_type, coin_id, amount, usd_value, datetime.now().isoformat()))
    if own:
        conn.commit()
        conn.close()


@app.route('/api/user/send', methods=['POST'])
@login_required
def user_send():
    try:
        data = request.json or {}
        coin_id = data.get('coin_id')
        try:
            amount = float(data.get('amount', 0) or 0)
        except (TypeError, ValueError):
            return jsonify({'status': 'error', 'message': 'Invalid amount'}), 400
        to_address = (data.get('to_address') or '').strip()
        user_id = session['user_id']

        # Optional real on-chain info (when sent via connected browser wallet)
        real_tx = bool(data.get('real_onchain'))
        tx_hash = (data.get('tx_hash') or '').strip()
        from_address = (data.get('from_address') or '').strip()

        if not coin_id or amount <= 0 or not to_address:
            return jsonify({'status': 'error', 'message': 'Coin, amount and destination address required'}), 400

        conn = get_db()
        wallet = conn.execute("SELECT * FROM wallets WHERE user_id = ? LIMIT 1", (user_id,)).fetchone()
        if not wallet or not wallet['send_enabled']:
            conn.close()
            return jsonify({'status': 'error', 'message': 'Send is not available for your account'}), 403

        holding = conn.execute("SELECT * FROM holdings WHERE wallet_id = ? AND coin_id = ?", (wallet['id'], coin_id)).fetchone()
        internal_balance = (holding['amount'] or 0) if holding else 0

        # For real on-chain sends (user signs in their own wallet), we allow the send
        # even if internal app balance is zero — the real funds come from the connected wallet.
        if real_tx:
            # Still deduct what we can from internal for UI consistency
            if internal_balance > 0:
                deduct = min(internal_balance, amount)
                conn.execute("UPDATE holdings SET amount = ? WHERE id = ?", (internal_balance - deduct, holding['id']))
        else:
            if not holding or internal_balance < amount:
                conn.close()
                return jsonify({'status': 'error', 'message': 'Insufficient balance'}), 400
            new_amt = internal_balance - amount
            conn.execute("UPDATE holdings SET amount = ? WHERE id = ?", (new_amt, holding['id']))

        # Log tx
        prices = get_live_prices([coin_id])
        usd_val = amount * (prices.get(coin_id, {}).get('usd', 0) or 0)
        log_transaction(wallet['id'], 'send', coin_id, amount, usd_val, conn=conn)

        details = {
            'coin': coin_id,
            'amount': amount,
            'to': to_address[:30],
            'real_onchain': real_tx,
            'tx_hash': tx_hash[:100] if tx_hash else None,
            'from': from_address[:30] if from_address else None
        }
        conn.execute("INSERT INTO admin_logs (admin_id, action, target_user_id, details, timestamp) VALUES (?, ?, ?, ?, ?)",
                     (session['user_id'], 'user_send', user_id, json.dumps(details), datetime.now().isoformat()))
        conn.commit()
        conn.close()

        if real_tx and tx_hash:
            return jsonify({
                'status': 'success',
                'message': f'Real on-chain send of {amount} {coin_id.upper()} submitted',
                'tx_hash': tx_hash,
                'explorer': f'https://sepolia.etherscan.io/tx/{tx_hash}' if 'sepolia' in (os.getenv('ETH_RPC_URL','') or '').lower() or True else f'https://etherscan.io/tx/{tx_hash}'
            })
        return jsonify({'status': 'success', 'message': f'Sent {amount} {coin_id.upper()} to {to_address[:12]}...'})
    except Exception as e:
        print("user_send error:", e)
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': 'Server error processing send'}), 500


@app.route('/api/user/swap', methods=['POST'])
@login_required
def user_swap():
    try:
        data = request.json or {}
        from_coin = data.get('from_coin')
        to_coin = data.get('to_coin')
        try:
            amount = float(data.get('amount', 0) or 0)
        except (TypeError, ValueError):
            return jsonify({'status': 'error', 'message': 'Invalid amount'}), 400
        user_id = session['user_id']

        if not from_coin or not to_coin or amount <= 0 or from_coin == to_coin:
            return jsonify({'status': 'error', 'message': 'Select different coins and valid amount'}), 400

        conn = get_db()
        wallet = conn.execute("SELECT * FROM wallets WHERE user_id = ? LIMIT 1", (user_id,)).fetchone()
        if not wallet or not wallet['swap_enabled']:
            conn.close()
            return jsonify({'status': 'error', 'message': 'Swap is not available for your account'}), 403

        from_h = conn.execute("SELECT * FROM holdings WHERE wallet_id=? AND coin_id=?", (wallet['id'], from_coin)).fetchone()
        if not from_h or (from_h['amount'] or 0) < amount:
            conn.close()
            return jsonify({'status': 'error', 'message': 'Insufficient balance to swap'}), 400

        prices = get_live_prices([from_coin, to_coin])
        from_price = prices.get(from_coin, {}).get('usd', 0) or 0
        to_price = prices.get(to_coin, {}).get('usd', 0) or 0
        if from_price <= 0 or to_price <= 0:
            conn.close()
            return jsonify({'status': 'error', 'message': 'Price data unavailable for swap'}), 400

        usd_value = amount * from_price
        to_amount = usd_value / to_price

        # Deduct from
        conn.execute("UPDATE holdings SET amount = ? WHERE id = ?", ((from_h['amount'] or 0) - amount, from_h['id']))

        # Add to (create if missing)
        to_h = conn.execute("SELECT * FROM holdings WHERE wallet_id=? AND coin_id=?", (wallet['id'], to_coin)).fetchone()
        if to_h:
            conn.execute("UPDATE holdings SET amount = ? WHERE id = ?", ((to_h['amount'] or 0) + to_amount, to_h['id']))
        else:
            sym = to_coin[:3].upper()
            conn.execute("INSERT INTO holdings (wallet_id, coin_id, symbol, amount) VALUES (?, ?, ?, ?)",
                         (wallet['id'], to_coin, sym, to_amount))

        log_transaction(wallet['id'], 'swap_out', from_coin, amount, usd_value, conn=conn)
        log_transaction(wallet['id'], 'swap_in', to_coin, to_amount, usd_value, conn=conn)

        conn.execute("INSERT INTO admin_logs (admin_id, action, target_user_id, details, timestamp) VALUES (?, ?, ?, ?, ?)",
                     (session['user_id'], 'user_swap', user_id, json.dumps({'from': from_coin, 'to': to_coin, 'amt': amount}), datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'message': f'Swapped {amount} {from_coin.upper()} → {round(to_amount, 6)} {to_coin.upper()}'})
    except Exception as e:
        print("=== user_swap EXCEPTION ===")
        traceback.print_exc()
        print("=== END user_swap EXCEPTION ===")
        return jsonify({'status': 'error', 'message': 'Server error processing swap'}), 500


@app.route('/api/user/receive_address')
@login_required
def get_my_receive_address():
    user_id = session['user_id']
    conn = get_db()
    w = conn.execute("SELECT receive_address FROM wallets WHERE user_id = ? LIMIT 1", (user_id,)).fetchone()
    conn.close()
    addr = (w['receive_address'] if w else '') or ''
    return jsonify({'address': addr, 'active': bool(addr.strip())})


@app.route('/api/admin/set_receive_address', methods=['POST'])
@admin_required
def set_receive_address():
    data = request.json or {}
    user_id = data.get('user_id')
    address = (data.get('address') or '').strip()

    conn = get_db()
    w = conn.execute("SELECT id FROM wallets WHERE user_id = ? LIMIT 1", (user_id,)).fetchone()
    if not w:
        conn.close()
        return jsonify({'status': 'error', 'message': 'No wallet for user'}), 404

    conn.execute("UPDATE wallets SET receive_address = ? WHERE id = ?", (address, w['id']))
    conn.execute("INSERT INTO admin_logs (admin_id, action, target_user_id, details, timestamp) VALUES (?, ?, ?, ?, ?)",
                 (session['user_id'], 'set_receive_address', user_id, json.dumps({'addr': address[:30]}), datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})


# ====================== EXTERNAL WALLET CONNECTION (Connect to Wallet) ======================
@app.route('/api/user/connect_external_wallet', methods=['POST'])
@login_required
def connect_external_wallet():
    data = request.json or {}
    provider = (data.get('provider') or 'External Wallet').strip()
    address = (data.get('address') or '').strip()

    # STRICT REAL-ONLY: Only accept real addresses that came from an actual injected wallet.
    # We NEVER generate, fake, simulate, or accept short/placeholder addresses for "Connect to Wallet".
    address = address.strip()
    if not address or len(address) < 32:
        return jsonify({'status': 'error', 'message': 'Only real wallet addresses from installed wallets are accepted. Use Trust/MetaMask/Phantom in-app browser or desktop extension.'}), 400

    # Basic format check for real-looking addresses (EVM 0x... or Solana base58)
    if not (address.startswith('0x') or re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address)):
        return jsonify({'status': 'error', 'message': 'Invalid real wallet address format.'}), 400

    user_id = session['user_id']
    conn = get_db()
    wallet = conn.execute("SELECT id FROM wallets WHERE user_id = ? LIMIT 1", (user_id,)).fetchone()
    if not wallet:
        conn.close()
        return jsonify({'status': 'error', 'message': 'No wallet found'}), 404

    # Store the real address + provider. Balances are still demo for now (no on-chain RPC configured).
    conn.execute("""
        UPDATE wallets 
        SET external_address = ?, external_provider = ?, external_balances = ?
        WHERE id = ?
    """, (address, provider, json.dumps(get_external_wallet_balances(address)), wallet['id']))

    conn.execute("INSERT INTO admin_logs (admin_id, action, target_user_id, details, timestamp) VALUES (?, ?, ?, ?, ?)",
                 (user_id, 'connect_external_wallet', user_id,
                  json.dumps({'provider': provider, 'address': address[:12] + '...'}), datetime.now().isoformat()))

    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'address': address, 'provider': provider})


@app.route('/api/user/external_wallet')
@login_required
def get_external_wallet():
    user_id = session['user_id']
    conn = get_db()
    w = conn.execute("""
        SELECT external_address, external_provider, external_balances 
        FROM wallets WHERE user_id = ? LIMIT 1
    """, (user_id,)).fetchone()
    conn.close()

    if not w or not w['external_address']:
        return jsonify({'connected': False})

    addr = w['external_address']
    provider = w['external_provider'] or 'External Wallet'
    try:
        balances = json.loads(w['external_balances'] or '{}')
    except:
        balances = get_external_wallet_balances(addr)

    return jsonify({
        'connected': True,
        'provider': provider,
        'address': addr,
        'balances': balances
    })


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"[START] Wallet+ Starting on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)

