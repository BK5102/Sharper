import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Sharper — Structured question linter",
  description:
    "Catches ambiguity, fuzzy resolution criteria, and missing operationalization in forecasting questions and outcome statements — for prediction markets, civic planning, and program evaluation.",
};

export default function LandingPage() {
  return (
    <main className="flex-1 mx-auto w-full max-w-3xl px-6 py-12">
      <header className="mb-10">
        <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100 mb-3">
          Sharper
        </h1>
        <p className="text-lg text-zinc-600 dark:text-zinc-400 leading-relaxed max-w-xl">
          A linter for structured forecasting questions and outcome statements. Catches
          ambiguity, fuzzy resolution criteria, and missing operationalization before
          a disputed outcome — on prediction markets, in civic planning, or in program evaluation.
        </p>
      </header>

      <section className="mb-6 grid gap-4 sm:grid-cols-2">
        <div className="rounded-lg border border-zinc-200 dark:border-zinc-700 p-5">
          <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 mb-1">
            Ambiguity detection
          </h2>
          <p className="text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed">
            Flags vague terms like &ldquo;significant&rdquo;, &ldquo;stable&rdquo;, or &ldquo;meaningful&rdquo; that
            make questions impossible to resolve consistently.
          </p>
        </div>
        <div className="rounded-lg border border-zinc-200 dark:border-zinc-700 p-5">
          <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 mb-1">
            Resolution criteria
          </h2>
          <p className="text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed">
            Checks for clear, measurable conditions — whether that&rsquo;s a Metaculus
            YES/NO or a program outcome threshold.
          </p>
        </div>
        <div className="rounded-lg border border-zinc-200 dark:border-zinc-700 p-5">
          <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 mb-1">
            Operationalization
          </h2>
          <p className="text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed">
            Verifies concepts have concrete thresholds, named data sources, and hard deadlines.
          </p>
        </div>
        <div className="rounded-lg border border-zinc-200 dark:border-zinc-700 p-5">
          <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 mb-1">
            Rewrite suggestions
          </h2>
          <p className="text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed">
            Proposes targeted rewrites for each issue — one click to apply them inline.
          </p>
        </div>
      </section>

      <section className="mb-10">
        <p className="text-xs font-semibold uppercase tracking-widest text-zinc-400 dark:text-zinc-500 mb-3">
          Built for
        </p>
        <div className="flex flex-wrap gap-2">
          {["Metaculus question authors", "City planning teams", "Public health programs", "Nonprofit evaluators", "Policy forecasters"].map((label) => (
            <span
              key={label}
              className="rounded-full border border-zinc-200 dark:border-zinc-700 px-3 py-1 text-xs text-zinc-600 dark:text-zinc-400"
            >
              {label}
            </span>
          ))}
        </div>
      </section>

      <div className="flex flex-wrap gap-3">
        <Link
          href="/auth"
          className="inline-flex items-center justify-center rounded-md px-5 py-2.5 text-sm font-semibold text-white bg-zinc-900 dark:bg-zinc-100 dark:text-zinc-900 hover:bg-zinc-700 dark:hover:bg-zinc-300 transition-colors duration-150"
        >
          Get started
        </Link>
        <Link
          href="/auth"
          className="inline-flex items-center justify-center rounded-md px-5 py-2.5 text-sm font-semibold text-zinc-700 dark:text-zinc-300 border border-zinc-300 dark:border-zinc-600 hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors duration-150"
        >
          Sign in
        </Link>
      </div>
    </main>
  );
}
