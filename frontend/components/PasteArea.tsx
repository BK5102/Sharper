"use client";

import { useState, type FormEvent } from "react";

export const MAX_CHARS = 4000;

interface Props {
  onSubmit: (question: string) => void;
  loading: boolean;
  initial?: string;
}

export function PasteArea({ onSubmit, loading, initial = "" }: Props) {
  const [text, setText] = useState(initial);
  const tooLong = text.length > MAX_CHARS;
  const tooShort = text.trim().length === 0;
  const disabled = loading || tooLong || tooShort;

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (disabled) return;
    onSubmit(text);
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Paste a draft forecasting question here — title and optional resolution criteria."
        rows={8}
        className="w-full resize-y rounded-md border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-950 px-3 py-2 text-sm text-zinc-900 dark:text-zinc-100 placeholder:text-zinc-400 dark:placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-zinc-900 dark:focus:ring-zinc-100"
      />
      <div className="flex items-center justify-between text-xs">
        <span
          className={
            tooLong
              ? "text-red-600 dark:text-red-400 font-medium"
              : "text-zinc-500"
          }
        >
          {text.length.toLocaleString()} / {MAX_CHARS.toLocaleString()} chars
        </span>
        <button
          type="submit"
          disabled={disabled}
          className="rounded-md bg-zinc-900 dark:bg-zinc-100 px-4 py-2 text-sm font-medium text-white dark:text-zinc-900 hover:bg-zinc-800 dark:hover:bg-zinc-200 disabled:cursor-not-allowed disabled:bg-zinc-300 dark:disabled:bg-zinc-800 disabled:text-zinc-500"
        >
          {loading ? "Linting…" : "Lint this question"}
        </button>
      </div>
    </form>
  );
}
