import { createClient } from "@supabase/supabase-js";

// NEXT_PUBLIC_* vars are safe to expose — they give read-only anon access.
// Security is enforced via Supabase Row Level Security (RLS) policies.
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";

// @supabase/supabase-js throws "supabaseUrl is required" when the URL is an
// empty string. During Next.js static generation (next build) the env vars are
// absent unless they have been added to the Vercel project settings, which
// causes the build to fail at the page-prerendering step.
//
// Guard: pass placeholder strings so createClient never throws at module-load
// time. All actual Supabase auth calls live inside browser-only useEffects and
// event handlers, so the placeholder client is NEVER invoked at runtime — the
// real client (URL is truthy) is always in place before any auth call fires.
//
// → Add NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY to
//   Vercel → Project → Settings → Environment Variables (all environments).
export const supabase = createClient(
  supabaseUrl || "https://placeholder.supabase.co",
  supabaseAnonKey || "placeholder-anon-key"
);
