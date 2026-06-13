import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Sharper — Forecasting question linter",
  description:
    "Catches ambiguity, fuzzy resolution criteria, and missing operationalization in draft forecasting questions before they go live.",
};

export default function LandingPage() {
  return (
    <main className="flex-1 mx-auto w-full max-w-3xl px-6 py-20">
      <header className="mb-12">
        <h1 className="text-4xl font-bold text-zinc-900 dark:text-zinc-100 mb-4">
          Sharper
        </h1>
        <p className="text-xl text-zinc-600 dark:text-zinc-400 leading-relaxed">
          A linter for forecasting questions. Catches ambiguity, fuzzy resolution
          criteria, and missing operationalization before a question goes live.
        </p>
      </header>

      <section className="mb-12 grid gap-6 sm:grid-cols-2">
        <div className="rounded-lg border border-zinc-200 dark:border-zinc-700 p-6">
          <h2 className="font-semibold text-zinc-900 dark:text-zinc-100 mb-2">
            Ambiguity detection
          </h2>
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            Flags vague terms like &ldquo;significant&rdquo;, &ldquo;large&rdquo;, or &ldquo;soon&rdquo; that make
            questions hard to resolve.
          </p>
        </div>
        <div className="rounded-lg border border-zinc-200 dark:border-zinc-700 p-6">
          <h2 className="font-semibold text-zinc-900 dark:text-zinc-100 mb-2">
            Resolution criteria
          </h2>
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            Checks that your question has clear, measurable conditions for a YES
            or NO resolution.
          </p>
        </div>
        <div className="rounded-lg border border-zinc-200 dark:border-zinc-700 p-6">
          <h2 className="font-semibold text-zinc-900 dark:text-zinc-100 mb-2">
            Operationalization
          </h2>
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            Verifies concepts can be measured with concrete thresholds and
            authoritative sources.
          </p>
        </div>
        <div className="rounded-lg border border-zinc-200 dark:border-zinc-700 p-6">
          <h2 className="font-semibold text-zinc-900 dark:text-zinc-100 mb-2">
            Rewrite suggestions
          </h2>
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            Proposes targeted rewrites for each issue — one click to apply them
            inline.
          </p>
        </div>
      </section>

      <div className="flex flex-col sm:flex-row gap-4">
        <Link
          href="/auth"
          className="inline-flex items-center justify-center rounded-md px-6 py-3 text-sm font-semibold text-white bg-zinc-900 dark:bg-zinc-100 dark:text-zinc-900 hover:bg-zinc-700 dark:hover:bg-zinc-200 transition-colors"
        >
          Get started
        </Link>
        <Link
          href="/auth"
          className="inline-flex items-center justify-center rounded-md px-6 py-3 text-sm font-semibold text-zinc-700 dark:text-zinc-300 border border-zinc-300 dark:border-zinc-600 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
        >
          Sign in
        </Link>
      </div>
    </main>
  );
}
