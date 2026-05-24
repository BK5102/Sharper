// Defense-in-depth scrubber: strip the user's `question` field from any
// Sentry event payload before it leaves the process. sendDefaultPii=false
// already prevents request bodies + headers from being captured by the SDK's
// default integrations, but this hook catches the field if it leaks via any
// other path (breadcrumbs from fetch, custom contexts, etc).

import type { ErrorEvent, EventHint } from "@sentry/nextjs";

const SCRUBBED = "[SCRUBBED]";

function scrubObject(obj: unknown): boolean {
  if (!obj || typeof obj !== "object") return false;
  const record = obj as Record<string, unknown>;
  if ("question" in record) {
    record.question = SCRUBBED;
    return true;
  }
  return false;
}

function scrubJsonStringField(value: unknown): unknown {
  if (typeof value !== "string") return value;
  try {
    const parsed = JSON.parse(value);
    if (scrubObject(parsed)) return JSON.stringify(parsed);
  } catch {
    // not JSON; leave as-is
  }
  return value;
}

export function scrubQuestion(event: ErrorEvent, _hint?: EventHint): ErrorEvent | null {
  // request.data may be a dict or a JSON-encoded string
  if (event.request) {
    if (event.request.data) {
      if (typeof event.request.data === "string") {
        event.request.data = scrubJsonStringField(event.request.data) as string;
      } else {
        scrubObject(event.request.data);
      }
    }
  }

  // fetch breadcrumbs may include the request body under `data.body`
  if (event.breadcrumbs) {
    for (const bc of event.breadcrumbs) {
      if (!bc.data) continue;
      const bcData = bc.data as Record<string, unknown>;
      if ("body" in bcData) {
        bcData.body = scrubJsonStringField(bcData.body);
      }
    }
  }

  return event;
}
