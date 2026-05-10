const SUPABASE_URL      = 'https://rlaemixsrmhocxjhkjxl.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJsYWVtaXhzcm1ob2N4amhranhsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzgzOTMzMTQsImV4cCI6MjA5Mzk2OTMxNH0.5S-nlwoAUPZutqtOl1rkVOQC3ITn0DV6JEqJzejquHc';

let _client = null;

if (SUPABASE_URL !== 'YOUR_SUPABASE_URL') {
  const { createClient } = supabase;
  _client = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
}

async function fetchNewsFromSupabase(dateStr) {
  if (!_client) throw new Error('Supabase 미설정 — fallback 사용');
  const { data, error } = await _client
    .from('news_cards')
    .select('*')
    .eq('date', dateStr)
    .order('created_at', { ascending: true });
  if (error) throw error;
  return data;
}

window.supabaseClient = _client;
window.fetchNewsFromSupabase = fetchNewsFromSupabase;
