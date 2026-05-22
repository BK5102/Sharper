"use client";

import { EXAMPLES, type Example } from "@/lib/examples";
import { RUBRIC_ITEM_LABELS } from "@/lib/api";
import { SeverityBadge } from "./SeverityBadge";

interface Props {
  onTry: (questionText: string) => void;
}

export function ExampleGallery({ onTry }: Props) {
  return (
    <section className="mb-10">
      <header className="mb-3">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
          See what Sharper catches
        </h2>
        <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-500">
          Real before / after examples from the eval set. Click any to load it
          into the editor.
        </p>
      </header>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {EXAMPLES.map((ex) => (
          <ExampleCard key={ex.label} example={ex} onTry={onTry} />
        ))}
      </div>
    </section>
  );
}

function ExampleCard({
  example,
  onTry,
}: {
  example: Example;
  onTry: (questionText: string) => void;
}) {
  return (
    <article className="flex flex-col gap-2 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-3 text-xs shadow-sm">
      <div className="flex items-center justify-between gap-2">
        <span className="font-medium text-zinc-700 dark:text-zinc-300">
          {example.label}
        </span>
        <SeverityBadge severity={example.severity} />
      </div>
      <p className="text-zinc-900 dark:text-zinc-100 line-clamp-3">
        {example.question}
      </p>
      <div className="mt-1 rounded border-l-2 border-zinc-400 dark:border-zinc-600 bg-zinc-50 dark:bg-zinc-900 px-2 py-1 font-mono text-[11px] text-zinc-700 dark:text-zinc-300 line-clamp-2">
        <span className="block text-[9px] uppercase tracking-wider text-zinc-500 mb-0.5">
          Defect: {RUBRIC_ITEM_LABELS[example.rubric_item]}
        </span>
        {example.defect_span}
      </div>
      <div className="rounded border-l-2 border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20 px-2 py-1 text-[11px] text-emerald-900 dark:text-emerald-100 line-clamp-3">
        <span className="block text-[9px] uppercase tracking-wider text-emerald-700 dark:text-emerald-400 mb-0.5">
          Rewrite
        </span>
        {example.rewrite}
      </div>
      <button
        type="button"
        onClick={() => onTry(example.question)}
        className="mt-1 self-start text-[11px] font-medium text-zinc-700 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
      >
        Try this in the editor →
      </button>
    </article>
  );
}
