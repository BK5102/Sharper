"use client";

import { useState } from "react";
import { lint, type ApiError, type Critique, type Finding } from "@/lib/api";
import { PasteArea } from "@/components/PasteArea";
import { FindingCard } from "@/components/FindingCard";

const SEVERITY_ORDER: Record<string, number> = { high: 0, medium: 1, low: 2 };

export default function Home() {
  const [critique, setCritique] = useState<Critique | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [accepted, setAccepted] = useState<Finding[]>([]);

  async function handleLint(question: string) {
    setLoading(true);
    setError(null);
    setCritique(null);
    setAccepted([]);
    try {
      const result = await lint(question);
      result.findings.sort(
        (a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity],
      );
      setCritique(result);
    } catch (e) {
      const err = e as ApiError;
      setError(
        err.detail ??
          "Network error — is the backend running on 127.0.0.1:8000?",
      );
    } finally {
      setLoading(false);
    }
  }

  function handleAccept(finding: Finding) {
    setAccepted((prev) =>
      prev.find((f) => f.quoted_span === finding.quoted_span)
        ? prev
        : [...prev, finding],
    );
  }

  return (
    <main className="flex-1 mx-auto w-full max-w-3xl px-6 py-12">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
          Sharper
        </h1>
        <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
          A linter for forecasting questions. Catches ambiguity, fuzzy
          resolution criteria, and missing operationalization before a question
          goes live.
        </p>
      </header>

      <section className="mb-10">
        <PasteArea onSubmit={handleLint} loading={loading} />
      </section>

      {error && (
        <div className="mb-6 rounded-md border border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-900/30 px-4 py-3 text-sm text-red-900 dark:text-red-100">
          {error}
        </div>
      )}

      {critique && (
        <section>
          <header className="mb-4 flex items-baseline justify-between gap-4">
            <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
              {critique.findings.length === 0
                ? "No issues found"
                : `${critique.findings.length} finding${critique.findings.length === 1 ? "" : "s"}`}
            </h2>
            {accepted.length > 0 && (
              <span className="text-xs text-emerald-700 dark:text-emerald-400">
                {accepted.length} rewrite{accepted.length === 1 ? "" : "s"} accepted
              </span>
            )}
          </header>

          {critique.overall_assessment && (
            <p className="mb-6 rounded-md bg-zinc-50 dark:bg-zinc-900 px-4 py-3 text-sm text-zinc-700 dark:text-zinc-300">
              {critique.overall_assessment}
            </p>
          )}

          <div className="flex flex-col gap-3">
            {critique.findings.map((f, i) => (
              <FindingCard
                key={`${f.rubric_item}-${i}`}
                finding={f}
                onAcceptRewrite={handleAccept}
              />
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
