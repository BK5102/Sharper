"use client";

import { useState, useEffect, type FormEvent } from "react";
import type { Editor } from "@tiptap/react";
import { EditorContent } from "@tiptap/react";

export const MAX_CHARS = 4000;

interface Props {
  editor: Editor | null;
  onSubmit: (question: string) => void;
  loading: boolean;
  placeholder: string;
}

export function PasteArea({ editor, onSubmit, loading, placeholder }: Props) {
  const [text, setText] = useState("");

  useEffect(() => {
    if (!editor) return;
    const handler = () => setText(editor.getText());
    queueMicrotask(handler);
    editor.on("update", handler);
    return () => { editor.off("update", handler); };
  }, [editor]);

  const length = text.length;
  const tooLong = length > MAX_CHARS;
  const tooShort = text.trim().length === 0;
  const disabled = loading || tooLong || tooShort || !editor;

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (disabled || !editor) return;
    onSubmit(editor.getText());
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <div className="relative min-h-[11rem] w-full rounded-md border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-950 px-4 py-3 text-base text-zinc-900 dark:text-zinc-100 focus-within:ring-2 focus-within:ring-zinc-900 dark:focus-within:ring-zinc-100 focus-within:border-transparent transition-shadow duration-100 [&_.ProseMirror]:min-h-[9rem] [&_.ProseMirror]:outline-none">
        {tooShort && (
          <div className="pointer-events-none absolute left-4 top-3 text-zinc-400 dark:text-zinc-500">
            {placeholder}
          </div>
        )}
        <EditorContent editor={editor} />
      </div>
      <div className="flex items-center justify-between">
        <span className={`text-sm ${tooLong ? "text-red-600 dark:text-red-400 font-medium" : "text-zinc-400 dark:text-zinc-500"}`}>
          {length.toLocaleString()} / {MAX_CHARS.toLocaleString()}
        </span>
        <button
          type="submit"
          disabled={disabled}
          className="rounded-md bg-zinc-900 dark:bg-zinc-100 px-5 py-2 text-sm font-semibold text-white dark:text-zinc-900 hover:bg-zinc-700 dark:hover:bg-zinc-300 disabled:opacity-40 disabled:cursor-not-allowed transition-colors duration-150"
        >
          {loading ? "Linting…" : "Lint this question"}
        </button>
      </div>
    </form>
  );
}
