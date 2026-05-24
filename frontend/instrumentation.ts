// Next.js auto-loads this file once per server runtime (node + edge).
// Sentry init lives here so any server-side error is captured.

import * as Sentry from "@sentry/nextjs";

import { scrubQuestion } from "./lib/sentry-scrub";

const DSN = process.env.NEXT_PUBLIC_SENTRY_DSN;

function isPlaceholder(dsn: string | undefined): boolean {
  if (!dsn || dsn.trim() === "") return true;
  // .env.example default looks like https://...@o000000.ingest.sentry.io/0000000
  return dsn.includes("...") || dsn.includes("o000000") || dsn.includes("<");
}

export async function register() {
  if (isPlaceholder(DSN)) return;
  if (process.env.NEXT_RUNTIME === "nodejs" || process.env.NEXT_RUNTIME === "edge") {
    Sentry.init({
      dsn: DSN,
      environment: process.env.NODE_ENV,
      tracesSampleRate: 0.1,
      sendDefaultPii: false,
      beforeSend: scrubQuestion,
    });
  }
}

// Server-side request error hook (Next 15+ convention).
export const onRequestError = Sentry.captureRequestError;
