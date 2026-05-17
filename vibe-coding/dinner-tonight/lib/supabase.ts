import { createClient } from '@supabase/supabase-js';

const url = process.env.EXPO_PUBLIC_SUPABASE_URL!;
const key = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY!;

export const supabase = createClient(url, key);

export async function submitFeedback(message: string, rating: number) {
  const { error } = await supabase.from('app_feedback').insert({
    message,
    rating,
    platform: 'expo-go',
  });
  if (error) throw error;
}
