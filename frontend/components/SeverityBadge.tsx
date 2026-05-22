import type { Severity } from "@/lib/api";

const STYLES: Record<Severity, string> = {
  high: "bg-red-100 text-red-900 dark:bg-red-900/40 dark:text-red-100 border-red-300 dark:border-red-700",
  medium:
    "bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-100 border-amber-300 dark:border-amber-700",
  low: "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300 border-zinc-300 dark:border-zinc-700",
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium uppercase tracking-wider ${STYLES[severity]}`}
    >
      {severity}
    </span>
  );
}
