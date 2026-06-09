import { createClient } from "@supabase/supabase-js";

// These are safe to expose in the browser — they give read-only, anon access.
// The real security happens in Supabase Row Level Security policies.
export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL ?? "",
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? ""
);
