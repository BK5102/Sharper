"use client";

import { useState } from "react";
import type { HistoryCritique, HistoryFinding } from "@/lib/supabase-server";
import { SeverityBadge } from "./SeverityBadge";
import type { Severity, RubricItem } from "@/lib/api";
import { RUBRIC_ITEM_LABELS } from "@/lib/api";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function truncate(text: string, max = 120): string {
  return text.length <= max ? text : text.slice(0, max).trimEnd() + "…";
}

function FindingRow({ finding }: { finding: HistoryFinding }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <li className="rounded-md border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 p-3">
      <div className="flex items-center justify-between gap-2 mb-1">
        <span className="text-xs font-medium text-zinc-600 dark:text-zinc-400">
          {RUBRIC_ITEM_LABELS[finding.rubric_item as RubricItem] ?? finding.rubric_item}
        </span>
        <SeverityBadge severity={finding.severity as Severity} />
      </div>
      <p className="text-sm text-zinc-900 dark:text-zinc-100 mb-1">{finding.issue}</p>
      <div className="mb-2 rounded border-l-4 border-zinc-400 dark:border-zinc-600 px-2 py-1 font-mono text-xs text-zinc-600 dark:text-zinc-400">
        {finding.quoted_span}
      </div>
      {finding.suggested_rewrite && (
        <div className="mb-2 rounded border-l-4 border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20 px-2 py-1 text-xs text-emerald-900 dark:text-emerald-100">
          {finding.suggested_rewrite}
        </div>
      )}
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="text-xs text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100"
      >
        {expanded ? "Hide explanation" : "Show explanation"}
      </button>
      {expanded && (
        <p className="mt-1 text-xs text-zinc-600 dark:text-zinc-400">
          {finding.explanation}
        </p>
      )}
    </li>
  );
}

function CritiqueCard({ critique }: { critique: HistoryCritique }) {
  const [open, setOpen] = useState(false);
  const highCount = critique.findings.filter((f) => f.severity === "high").length;
  const medCount = critique.findings.filter((f) => f.severity === "medium").length;

  return (
    <article className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 shadow-sm">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full text-left px-5 py-4"
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100 leading-snug">
              {truncate(critique.question)}
            </p>
            <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-500">
              {formatDate(critique.created_at)}
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {critique.findings.length === 0 ? (
              <span className="text-xs text-emerald-700 dark:text-emerald-400 font-medium">
                No issues
              </span>
            ) : (
              <>
                {highCount > 0 && (
                  <SeverityBadge severity="high" />
                )}
                {medCount > 0 && highCount === 0 && (
                  <SeverityBadge severity="medium" />
                )}
                <span className="text-xs text-zinc-500">
                  {critique.findings.length} finding{critique.findings.length !== 1 ? "s" : ""}
                </span>
              </>
            )}
            <span className="text-zinc-400 text-xs">{open ? "▲" : "▼"}</span>
          </div>
        </div>
      </button>

      {open && (
        <div className="border-t border-zinc-100 dark:border-zinc-800 px-5 pb-5 pt-4">
          <p className="mb-4 text-sm text-zinc-600 dark:text-zinc-400 italic">
            {critique.overall_assessment}
          </p>
          {critique.findings.length === 0 ? (
            <p className="text-sm text-zinc-500">No findings for this critique.</p>
          ) : (
            <ul className="flex flex-col gap-2">
              {critique.findings.map((f) => (
                <FindingRow key={f.id} finding={f} />
              ))}
            </ul>
          )}
        </div>
      )}
    </article>
  );
}

export function HistoryList({ critiques }: { critiques: HistoryCritique[] }) {
  if (critiques.length === 0) {
    return (
      <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 px-6 py-12 text-center">
        <p className="text-sm text-zinc-500">No critiques yet — lint a question to get started.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {critiques.map((c) => (
        <CritiqueCard key={c.id} critique={c} />
      ))}
    </div>
  );
}
