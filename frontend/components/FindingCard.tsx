"use client";

import { useState } from "react";
import type { Finding } from "@/lib/api";
import { RUBRIC_ITEM_LABELS } from "@/lib/api";
import { SeverityBadge } from "./SeverityBadge";

interface Props {
  finding: Finding;
  accepted: boolean;
  onAcceptRewrite: (finding: Finding) => boolean;
}

export function FindingCard({ finding, accepted, onAcceptRewrite }: Props) {
  const [showExplanation, setShowExplanation] = useState(false);
  const [missed, setMissed] = useState(false);

  function accept() {
    const applied = onAcceptRewrite(finding);
    if (!applied) setMissed(true);
  }

  return (
    <article className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-4">
      <header className="flex items-center justify-between gap-2 mb-3">
        <span className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">
          {RUBRIC_ITEM_LABELS[finding.rubric_item]}
        </span>
        <SeverityBadge severity={finding.severity} />
      </header>

      <p className="mb-3 text-sm text-zinc-900 dark:text-zinc-100 leading-relaxed">
        {finding.issue}
      </p>

      <div className="mb-3 rounded border-l-4 border-zinc-300 dark:border-zinc-600 bg-zinc-50 dark:bg-zinc-900 px-3 py-2 font-mono text-xs text-zinc-700 dark:text-zinc-300">
        <span className="block text-[10px] uppercase tracking-widest text-zinc-400 mb-1">
          Quoted span
        </span>
        {finding.quoted_span}
      </div>

      {finding.suggested_rewrite && (
        <div className="mb-3 rounded border-l-4 border-emerald-400 dark:border-emerald-600 bg-emerald-50 dark:bg-emerald-950 px-3 py-2 text-sm text-emerald-900 dark:text-emerald-100 leading-relaxed">
          <span className="block text-[10px] uppercase tracking-widest text-emerald-600 dark:text-emerald-400 mb-1">
            Suggested rewrite
          </span>
          {finding.suggested_rewrite}
          <div className="mt-2.5 flex items-center gap-3">
            <button
              type="button"
              onClick={accept}
              disabled={accepted}
              className="rounded-md bg-emerald-600 px-3 py-1 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-default transition-colors duration-150"
            >
              {accepted ? "Accepted ✓" : "Accept rewrite"}
            </button>
            {missed && !accepted && (
              <span className="text-xs text-amber-700 dark:text-amber-400">
                Span not found — edited since lint?
              </span>
            )}
          </div>
        </div>
      )}

      <button
        type="button"
        onClick={() => setShowExplanation((v) => !v)}
        className="text-xs text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 transition-colors duration-150"
      >
        {showExplanation ? "Hide explanation" : "Show explanation"}
      </button>
      {showExplanation && (
        <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed">
          {finding.explanation}
        </p>
      )}
    </article>
  );
}
