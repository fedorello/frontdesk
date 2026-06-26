import type { TraceStep } from "./types";

function formatArgs(args?: Record<string, unknown> | null): string {
  if (!args) return "";
  return Object.entries(args)
    .map(([key, value]) => `${key}: ${JSON.stringify(value)}`)
    .join(", ");
}

function truncate(text: string, max = 80): string {
  const oneLine = text.replace(/\s+/g, " ").trim();
  return oneLine.length > max ? `${oneLine.slice(0, max)}…` : oneLine;
}

export function Trace({ steps }: { steps?: TraceStep[] }) {
  if (!steps || steps.length === 0) return null;

  return (
    <details className="mt-2 text-xs text-muted">
      <summary className="cursor-pointer list-none select-none hover:text-zinc-700 dark:hover:text-zinc-300">
        🧠 Agent reasoning · {steps.length} step{steps.length === 1 ? "" : "s"}
      </summary>
      <ol className="mt-2 space-y-1.5 border-l border-line-strong pl-3 ">
        {steps.map((step, index) => (
          <li key={index}>
            {step.kind === "thought" ? (
              <span className="italic">{step.text}</span>
            ) : (
              <span>
                <code className="rounded bg-zinc-200 px-1 font-mono text-zinc-800 dark:text-zinc-200">
                  {step.tool}({formatArgs(step.args)})
                </code>
                {step.result ? (
                  <span className="text-faint"> → {truncate(step.result)}</span>
                ) : null}
              </span>
            )}
          </li>
        ))}
      </ol>
    </details>
  );
}
