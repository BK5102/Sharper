"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase-browser";

type Mode = "signin" | "signup";

export default function AuthPage() {
  const [mode, setMode] = useState<Mode>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setMessage(null);

    const supabase = createClient();

    if (mode === "signin") {
      const { error: authError } = await supabase.auth.signInWithPassword({
        email,
        password,
      });
      if (authError) {
        setError(authError.message);
      } else {
        router.push("/app");
        router.refresh();
      }
    } else {
      const { data, error: authError } = await supabase.auth.signUp({
        email,
        password,
      });
      if (authError) {
        setError(authError.message);
      } else if (data.session) {
        router.push("/app");
        router.refresh();
      } else {
        setMessage("Check your email to confirm your account, then sign in.");
        setMode("signin");
      }
    }

    setLoading(false);
  }

  return (
    <main className="flex-1 flex items-start justify-center px-6 py-16">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100 mb-1">
          {mode === "signin" ? "Sign in" : "Create account"}
        </h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-8">
          {mode === "signin"
            ? "Welcome back to Sharper."
            : "Start linting your forecasting questions."}
        </p>

        {message && (
          <div className="mb-6 rounded-md border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950 px-4 py-3 text-sm text-emerald-800 dark:text-emerald-200">
            {message}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label
              htmlFor="email"
              className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1.5"
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-md border border-zinc-300 dark:border-zinc-600 bg-white dark:bg-zinc-900 px-3 py-2 text-sm text-zinc-900 dark:text-zinc-100 placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-zinc-500 focus:border-transparent transition-shadow duration-100"
              placeholder="you@example.com"
              autoComplete="email"
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1.5"
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-md border border-zinc-300 dark:border-zinc-600 bg-white dark:bg-zinc-900 px-3 py-2 text-sm text-zinc-900 dark:text-zinc-100 placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-zinc-500 focus:border-transparent transition-shadow duration-100"
              placeholder={mode === "signup" ? "At least 8 characters" : "••••••••"}
              autoComplete={mode === "signin" ? "current-password" : "new-password"}
            />
          </div>

          {error && (
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="rounded-md px-4 py-2.5 text-sm font-semibold text-white bg-zinc-900 dark:bg-zinc-100 dark:text-zinc-900 hover:bg-zinc-700 dark:hover:bg-zinc-300 disabled:opacity-40 disabled:cursor-not-allowed transition-colors duration-150"
          >
            {loading
              ? mode === "signin" ? "Signing in…" : "Creating account…"
              : mode === "signin" ? "Sign in" : "Create account"}
          </button>
        </form>

        <p className="mt-6 text-sm text-zinc-500 dark:text-zinc-400">
          {mode === "signin" ? (
            <>
              Don&apos;t have an account?{" "}
              <button
                onClick={() => { setMode("signup"); setError(null); setMessage(null); }}
                className="text-zinc-900 dark:text-zinc-100 font-medium hover:underline transition-colors duration-150"
              >
                Sign up
              </button>
            </>
          ) : (
            <>
              Already have an account?{" "}
              <button
                onClick={() => { setMode("signin"); setError(null); setMessage(null); }}
                className="text-zinc-900 dark:text-zinc-100 font-medium hover:underline transition-colors duration-150"
              >
                Sign in
              </button>
            </>
          )}
        </p>
      </div>
    </main>
  );
}
