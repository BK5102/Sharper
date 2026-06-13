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
    <main className="flex-1 mx-auto w-full max-w-3xl px-6 py-8">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
            History
          </h1>
          <p className="mt-0.5 text-sm text-zinc-500 dark:text-zinc-400">
            {critiques.length > 0 ? `${critiques.length} past critique${critiques.length === 1 ? "" : "s"}` : "No critiques yet"}
          </p>
        </div>
        <Link
          href="/app"
          className="rounded-md px-3 py-1.5 text-sm font-medium text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors duration-150"
        >
          ← Linter
        </Link>
      </header>

      <HistoryList critiques={critiques} />
    </main>
  );
}
