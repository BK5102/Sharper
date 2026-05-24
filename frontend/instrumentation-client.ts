// Next.js auto-loads this file in the browser bundle. Sentry init for
// client-side errors goes here.

import * as Sentry from "@sentry/nextjs";

import { scrubQuestion } from "./lib/sentry-scrub";

const DSN = process.env.NEXT_PUBLIC_SENTRY_DSN;

function isPlaceholder(dsn: string | undefined): boolean {
  if (!dsn || dsn.trim() === "") return true;
  return dsn.includes("...") || dsn.includes("o000000") || dsn.includes("<");
}

if (!isPlaceholder(DSN)) {
  Sentry.init({
    dsn: DSN,
    environment: process.env.NODE_ENV,
    tracesSampleRate: 0.1,
    sendDefaultPii: false,
    beforeSend: scrubQuestion,
  });
}

// Required export for Next 15+ router transition tracing.
export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;
