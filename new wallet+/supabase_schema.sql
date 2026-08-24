-- ============================================================
-- SUPABASE DATABASE SCHEMA FOR WALLET+ (Auth & Database Setup)
-- Paste and run this SQL in your Supabase Dashboard: SQL Editor -> New Query -> Run
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. PUBLIC USERS TABLE (Linked to Supabase auth.users)
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT,
    email TEXT UNIQUE,
    avatar_url TEXT,
    role TEXT DEFAULT 'user',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security (RLS)
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own profile" ON public.users
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update their own profile" ON public.users
    FOR UPDATE USING (auth.uid() = id);

-- 2. WALLETS TABLE
CREATE TABLE IF NOT EXISTS public.wallets (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    send_enabled BOOLEAN DEFAULT TRUE,
    swap_enabled BOOLEAN DEFAULT TRUE,
    is_frozen BOOLEAN DEFAULT FALSE,
    receive_address TEXT DEFAULT '',
    external_address TEXT DEFAULT '',
    external_provider TEXT DEFAULT '',
    external_balances JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.wallets ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their own wallets" ON public.wallets
    FOR ALL USING (auth.uid() = user_id);

-- 3. HOLDINGS TABLE
CREATE TABLE IF NOT EXISTS public.holdings (
    id BIGSERIAL PRIMARY KEY,
    wallet_id BIGINT REFERENCES public.wallets(id) ON DELETE CASCADE,
    coin_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    amount NUMERIC DEFAULT 0.0
);

ALTER TABLE public.holdings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage holdings through wallet ownership" ON public.holdings
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.wallets 
            WHERE wallets.id = holdings.wallet_id AND wallets.user_id = auth.uid()
        )
    );

-- 4. TRANSACTIONS TABLE
CREATE TABLE IF NOT EXISTS public.transactions (
    id BIGSERIAL PRIMARY KEY,
    wallet_id BIGINT REFERENCES public.wallets(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    coin_id TEXT NOT NULL,
    amount NUMERIC DEFAULT 0.0,
    usd_value NUMERIC DEFAULT 0.0,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view transactions through wallet ownership" ON public.transactions
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.wallets 
            WHERE wallets.id = transactions.wallet_id AND wallets.user_id = auth.uid()
        )
    );

-- 5. USER VERIFICATION TABLE
CREATE TABLE IF NOT EXISTS public.user_verification (
    user_id UUID PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
    is_verified BOOLEAN DEFAULT TRUE,
    steps JSONB DEFAULT '[]'::jsonb,
    submitted_at TIMESTAMPTZ DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.user_verification ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their verification status" ON public.user_verification
    FOR SELECT USING (auth.uid() = user_id);

-- 6. TRIGGER FOR AUTOMATIC USER SYNC ON GITHUB / OAUTH LOGIN
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.users (id, name, email, avatar_url, role, created_at)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.raw_user_meta_data->>'user_name', NEW.email),
        NEW.email,
        NEW.raw_user_meta_data->>'avatar_url',
        'user',
        NOW()
    )
    ON CONFLICT (id) DO UPDATE SET
        name = EXCLUDED.name,
        email = EXCLUDED.email,
        avatar_url = EXCLUDED.avatar_url;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger execution
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
