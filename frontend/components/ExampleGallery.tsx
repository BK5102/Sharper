"use client";

import { EXAMPLES, type Example } from "@/lib/examples";
import { RUBRIC_ITEM_LABELS } from "@/lib/api";
import { SeverityBadge } from "./SeverityBadge";

interface Props {
  onTry: (questionText: string) => void;
}

export function ExampleGallery({ onTry }: Props) {
  return (
    <section>
      <header className="mb-3">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-400 dark:text-zinc-500">
          See what Sharper catches
        </h2>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-500">
          Real before / after examples. Click any to load it into the editor.
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
    <article className="flex flex-col gap-2 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-4 hover:border-zinc-300 dark:hover:border-zinc-700 transition-colors duration-150">
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
          {example.label}
        </span>
        <SeverityBadge severity={example.severity} />
      </div>
      <p className="text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed line-clamp-3">
        {example.question}
      </p>
      <div className="rounded border-l-2 border-zinc-300 dark:border-zinc-600 bg-zinc-50 dark:bg-zinc-900 px-2.5 py-1.5 font-mono text-xs text-zinc-600 dark:text-zinc-400 line-clamp-2">
        <span className="block text-[10px] uppercase tracking-widest text-zinc-400 mb-0.5">
          {RUBRIC_ITEM_LABELS[example.rubric_item]}
        </span>
        {example.defect_span}
      </div>
      <div className="rounded border-l-2 border-emerald-400 dark:border-emerald-600 bg-emerald-50 dark:bg-emerald-950 px-2.5 py-1.5 text-xs text-emerald-800 dark:text-emerald-200 leading-relaxed line-clamp-3">
        <span className="block text-[10px] uppercase tracking-widest text-emerald-600 dark:text-emerald-500 mb-0.5">
          Rewrite
        </span>
        {example.rewrite}
      </div>
      <button
        type="button"
        onClick={() => onTry(example.question)}
        className="self-start text-xs font-medium text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors duration-150"
      >
        Try in editor →
      </button>
    </article>
  );
}
