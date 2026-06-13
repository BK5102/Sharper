import { redirect } from "next/navigation";
import Link from "next/link";
import type { Metadata } from "next";

import { createClient } from "@/lib/supabase-server-auth";
import { fetchUserCritiques, type HistoryCritique } from "@/lib/supabase-server";
import { HistoryList } from "@/components/HistoryList";

export const metadata: Metadata = { title: "History — Sharper" };

export default async function HistoryPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/auth");

  const critiques: HistoryCritique[] = await fetchUserCritiques(user.id);

  return (
    <main className="flex-1 mx-auto w-full max-w-3xl px-6 py-12">
      <header className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
            History
          </h1>
          <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
            Your last {critiques.length > 0 ? `${critiques.length} ` : ""}
            critiques
          </p>
        </div>
        <Link
          href="/app"
          className="text-sm text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors"
        >
          ← Back to linter
        </Link>
      </header>

      <HistoryList critiques={critiques} />
    </main>
  );
}
