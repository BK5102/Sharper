// Server-only — never import this from a "use client" component.
// Calls the Supabase PostgREST REST API directly via fetch — no SDK.
// This avoids @supabase/supabase-js pulling in realtime-js, which needs
// WebSocket globals that don't exist at Next.js build time.

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

function getConfig(): { url: string; key: string } | null {
  const url = (
    process.env.SUPABASE_URL ??
    process.env.NEXT_PUBLIC_SUPABASE_URL ??
    ""
  ).replace(/\/$/, "");
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY ?? "";
  return url && key ? { url, key } : null;
}

export async function fetchUserCritiques(
  userId: string,
  limit = 50,
): Promise<HistoryCritique[]> {
  const cfg = getConfig();
  if (!cfg) return [];

  const params = new URLSearchParams({
    "user_id": `eq.${userId}`,
    "select": "*,findings(*)",
    "order": "created_at.desc",
    "limit": String(limit),
  });

  try {
    const resp = await fetch(`${cfg.url}/rest/v1/critiques?${params}`, {
      headers: {
        apikey: cfg.key,
        Authorization: `Bearer ${cfg.key}`,
      },
      cache: "no-store",
    });

    if (!resp.ok) {
      console.error("Supabase history fetch failed:", resp.status);
      return [];
    }

    return (await resp.json()) as HistoryCritique[];
  } catch (e) {
    console.error("Supabase history fetch error:", e);
    return [];
  }
}
