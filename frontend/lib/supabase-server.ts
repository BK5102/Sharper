// Server-only Supabase client — never import this from a "use client" component.
// Uses the service-role key so it bypasses RLS; safe only in server-side code
// (Next.js server components, route handlers). Env vars have no NEXT_PUBLIC_
// prefix so they are never bundled into the browser.

import { createClient } from "@supabase/supabase-js";

export interface HistoryFinding {
  id: string;
  rubric_item: string;
  severity: string;
  quoted_span: string;
  issue: string;
  explanation: string;
  suggested_rewrite: string | null;
}

export interface HistoryCritique {
  id: string;
  user_id: string;
  question: string;
  overall_assessment: string;
  created_at: string;
  findings: HistoryFinding[];
}

export function createServerSupabaseClient() {
  // Accept both SUPABASE_URL (server-only) and the public variant set during
  // account setup; the URL is not a secret so either works.
  const url =
    process.env.SUPABASE_URL ?? process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY ?? "";

  if (!url || !key) return null;

  return createClient(url, key, {
    auth: { persistSession: false },
  });
}
