// Supabase Client Initialization
// Supports Vite/ES modules & browser environments

import { createClient } from '@supabase/supabase-js'

const supabaseUrl = (import.meta.env && import.meta.env.VITE_SUPABASE_URL) 
  ? import.meta.env.VITE_SUPABASE_URL 
  : 'https://your-project-id.supabase.co'

const supabaseAnonKey = (import.meta.env && import.meta.env.VITE_SUPABASE_ANON_KEY) 
  ? import.meta.env.VITE_SUPABASE_ANON_KEY 
  : 'your-actual-anon-key-here'

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
