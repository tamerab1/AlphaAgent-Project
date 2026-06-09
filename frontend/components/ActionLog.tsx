import type { AgentRunOut } from "@/lib/api";
import { formatCurrency, formatTime } from "@/lib/format";

function StatusBadge({ run }: { run: AgentRunOut }) {
  let label = "HOLD";
  let cls = "bg-border text-muted";
  if (run.executed) {
    label = "EXECUTED";
    cls = "bg-positive/15 text-positive";
  } else if (run.risk && !run.risk.approved) {
    label = "REJECTED";
    cls = "bg-negative/15 text-negative";
  }
  return (
    <span className={`rounded px-2 py-0.5 text-xs font-medium ${cls}`}>
      {label}
    </span>
  );
}

export default function ActionLog({ runs }: { runs: AgentRunOut[] }) {
  return (
    <div className="rounded-lg border border-border bg-surface">
      <div className="border-b border-border px-5 py-3">
        <h2 className="text-lg font-semibold">AI Action Log</h2>
      </div>
      {runs.length === 0 ? (
        <p className="px-5 py-8 text-center text-muted">
          No analysis runs yet. Use “Run Analysis” to start.
        </p>
      ) : (
        <ul className="divide-y divide-border">
          {runs.map((run) => (
            <li key={run.id} className="px-5 py-4">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{run.symbol}</span>
                  {run.analyst && (
                    <span className="text-sm text-accent">
                      {run.analyst.action}
                    </span>
                  )}
                  <StatusBadge run={run} />
                </div>
                <span className="text-xs text-muted">
                  {formatTime(run.created_at)}
                </span>
              </div>
              {run.analyst?.reasoning && (
                <p className="mt-2 text-sm text-muted">
                  <span className="text-white">Analyst:</span>{" "}
                  {run.analyst.reasoning}
                </p>
              )}
              {run.analyst?.target_price != null &&
                run.analyst?.stop_loss != null && (
                  <p className="mt-1 text-sm text-muted">
                    <span className="text-white">Target:</span>{" "}
                    {formatCurrency(run.analyst.target_price)}
                    <span className="ml-3 text-white">Stop:</span>{" "}
                    {formatCurrency(run.analyst.stop_loss)}
                  </p>
                )}
              {run.risk?.reason && (
                <p className="mt-1 text-sm text-muted">
                  <span className="text-white">Risk:</span> {run.risk.reason}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
