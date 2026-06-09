"use client";

import { useEffect, useRef } from "react";
import { Bot, Terminal, CheckCircle2, XCircle, Minus, AlertTriangle, ChevronRight } from "lucide-react";
import type { AgentRunOut } from "@/lib/api";
import { formatTime } from "@/lib/format";

interface AILogsWidgetProps {
  logs: AgentRunOut[];
}

function ActionBadge({ action }: { action: string }) {
  if (action === "BUY")
    return <span className="rounded bg-positive/15 px-1.5 py-0.5 text-[10px] font-bold text-positive">BUY</span>;
  if (action === "SELL")
    return <span className="rounded bg-negative/15 px-1.5 py-0.5 text-[10px] font-bold text-negative">SELL</span>;
  return <span className="rounded bg-muted/10 px-1.5 py-0.5 text-[10px] font-bold text-muted">HOLD</span>;
}

function StatusIcon({ run }: { run: AgentRunOut }) {
  if (run.executed)
    return <span className="flex items-center gap-1 text-[11px] font-medium text-positive"><CheckCircle2 className="h-3 w-3" />Executed</span>;
  if (run.analyst?.action === "HOLD")
    return <span className="flex items-center gap-1 text-[11px] font-medium text-muted"><Minus className="h-3 w-3" />Hold</span>;
  return <span className="flex items-center gap-1 text-[11px] font-medium text-negative"><XCircle className="h-3 w-3" />Rejected</span>;
}

export default function AILogsWidget({ logs }: AILogsWidgetProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs.length]);

  return (
    <div className="flex flex-col rounded-xl border border-border bg-surface">

      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <Bot className="h-4 w-4 text-accent" />
          <h2 className="text-sm font-semibold text-white">AI Engine</h2>
          <Terminal className="h-3.5 w-3.5 text-muted" />
          {logs.length > 0 && (
            <span className="relative ml-0.5 flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-positive opacity-60" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-positive" />
            </span>
          )}
        </div>
        <span className="text-[11px] text-muted">{logs.length} run{logs.length !== 1 ? "s" : ""}</span>
      </div>

      {/* Terminal body */}
      <div className="scrollbar-thin h-[344px] space-y-2.5 overflow-y-auto p-3 font-mono text-xs">
        {logs.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-muted">
            <Terminal className="h-8 w-8 opacity-30" />
            <p>No runs yet. Use the Analysis panel to start.</p>
          </div>
        ) : (
          [...logs].reverse().map((run) => (
            <div key={run.id} className="animate-slide-up rounded-lg border border-border/50 bg-surface2 p-3 space-y-2">

              {/* Run header */}
              <div className="flex items-center justify-between flex-wrap gap-1">
                <div className="flex items-center gap-1.5">
                  <ChevronRight className="h-3 w-3 text-accent shrink-0" />
                  <span className="font-bold text-accent">{run.symbol}</span>
                  {run.analyst && <ActionBadge action={run.analyst.action} />}
                </div>
                <div className="flex items-center gap-2.5">
                  <StatusIcon run={run} />
                  <span className="text-muted">{formatTime(run.created_at)}</span>
                </div>
              </div>

              {/* Analyst block */}
              {run.analyst && (
                <div className="space-y-1 pl-4 border-l border-border/50">
                  <p className="text-[9px] font-bold uppercase tracking-widest text-accent/60">Analyst</p>
                  <p className="leading-relaxed text-white/80">{run.analyst.reasoning}</p>
                  <div className="flex flex-wrap items-center gap-3 text-[10px] pt-0.5">
                    <span className="text-muted">
                      Confidence: <span className="text-white">{(run.analyst.confidence * 100).toFixed(0)}%</span>
                    </span>
                    {run.analyst.target_price != null && (
                      <span className="text-muted">
                        Target: <span className="text-positive">${run.analyst.target_price.toLocaleString()}</span>
                      </span>
                    )}
                    {run.analyst.stop_loss != null && (
                      <span className="text-muted">
                        Stop: <span className="text-negative">${run.analyst.stop_loss.toLocaleString()}</span>
                      </span>
                    )}
                  </div>
                </div>
              )}

              {/* Risk block */}
              {run.risk && (
                <div className="space-y-1 pl-4 border-l border-border/50 pt-1">
                  <div className="flex items-center gap-1.5">
                    <p className="text-[9px] font-bold uppercase tracking-widest text-accent/60">Risk</p>
                    {!run.risk.approved && <AlertTriangle className="h-2.5 w-2.5 text-negative" />}
                  </div>
                  <p className={`leading-relaxed ${run.risk.approved ? "text-white/80" : "text-negative/80"}`}>
                    {run.risk.reason}
                  </p>
                </div>
              )}
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
