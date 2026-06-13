"use client";

import { useState } from "react";
import { useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import { useRouter } from "next/navigation";

import Link from "next/link";
import { lint, type ApiError, type Critique, type Finding } from "@/lib/api";
import { PasteArea } from "@/components/PasteArea";
import { FindingCard } from "@/components/FindingCard";
import { ExampleGallery } from "@/components/ExampleGallery";
import { AuthButton } from "@/components/AuthButton";
import { createClient } from "@/lib/supabase-browser";

const SEVERITY_ORDER: Record<string, number> = { high: 0, medium: 1, low: 2 };

export default function AppPage() {
  const [critique, setCritique] = useState<Critique | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [accepted, setAccepted] = useState<Set<string>>(new Set());
  const router = useRouter();

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: false,
        bulletList: false,
        orderedList: false,
        codeBlock: false,
        blockquote: false,
        horizontalRule: false,
      }),
      Placeholder.configure({
        placeholder:
          "Paste a draft forecasting question here — title and optional resolution criteria.",
      }),
    ],
    content: "",
    immediatelyRender: false,
  });

  async function handleLint(question: string) {
    setLoading(true);
    setError(null);
    setCritique(null);
    setAccepted(new Set());
    try {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const token = session?.access_token ?? null;
      const result = await lint(question, token);
      result.findings.sort(
        (a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity],
      );
      setCritique(result);
    } catch (e) {
      const err = e as ApiError;
      if ((err as { status?: number }).status === 401) {
        router.push("/auth");
        return;
      }
      setError(
        err.detail ??
          "Network error — is the backend running on 127.0.0.1:8000?",
      );
    } finally {
      setLoading(false);
    }
  }

  function findingKey(f: Finding): string {
    return `${f.rubric_item}::${f.quoted_span}`;
  }

  function handleAccept(finding: Finding): boolean {
    if (!editor || !finding.suggested_rewrite) return false;
    const current = editor.getText();
    if (!current.includes(finding.quoted_span)) return false;
    const next = current.replace(finding.quoted_span, finding.suggested_rewrite);
    editor.commands.setContent(next);
    setAccepted((prev) => new Set(prev).add(findingKey(finding)));
    return true;
  }

  return (
    <main className="flex-1 mx-auto w-full max-w-3xl px-6 py-12">
      <header className="mb-8 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
            Sharper
          </h1>
          <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
            A linter for forecasting questions. Catches ambiguity, fuzzy
            resolution criteria, and missing operationalization before a question
            goes live.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/history"
            className="text-sm text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors"
          >
            History
          </Link>
          <AuthButton />
        </div>
      </header>

      <section className="mb-10">
        <PasteArea editor={editor} onSubmit={handleLint} loading={loading} />
      </section>

      {!critique && !loading && (
        <ExampleGallery
          onTry={(text) => {
            editor?.commands.setContent(text);
            editor?.commands.focus("end");
          }}
        />
      )}

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
            {accepted.size > 0 && (
              <span className="text-xs text-emerald-700 dark:text-emerald-400">
                {accepted.size} rewrite{accepted.size === 1 ? "" : "s"} accepted
                — re-lint to verify
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
                accepted={accepted.has(findingKey(f))}
                onAcceptRewrite={handleAccept}
              />
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
