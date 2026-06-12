import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import Link from "next/link";
import type { Metadata } from "next";

import {
  createServerSupabaseClient,
  type HistoryCritique,
} from "@/lib/supabase-server";
import { HistoryList } from "@/components/HistoryList";

export const metadata: Metadata = { title: "History — Sharper" };

export default async function HistoryPage() {
  const { userId } = await auth();
  if (!userId) redirect("/");

  const supabase = createServerSupabaseClient();
  let critiques: HistoryCritique[] = [];

  if (supabase) {
    const { data, error } = await supabase
      .from("critiques")
      .select("*, findings(*)")
      .eq("user_id", userId)
      .order("created_at", { ascending: false })
      .limit(50);

    if (error) {
      console.error("Supabase history fetch failed:", error.message);
    } else {
      critiques = (data ?? []) as HistoryCritique[];
    }
  }

  return (
    <main className="flex-1 mx-auto w-full max-w-3xl px-6 py-12">
      <header className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
            History
          </h1>
          <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
            Your last {critiques.length > 0 ? `${critiques.length} ` : ""}critiques
          </p>
        </div>
        <Link
          href="/"
          className="text-sm text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors"
        >
          ← Back to linter
        </Link>
      </header>

      <HistoryList critiques={critiques} />
    </main>
  );
}
