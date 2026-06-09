"use client";

import React, { useState } from "react";
import { ChevronRight, ChevronDown, Sparkles } from "lucide-react";
import type { TradeOut } from "@/lib/api";
import { formatCurrency, formatQty, formatTime } from "@/lib/format";

interface TradeHistoryWidgetProps {
  trades: TradeOut[];
}

export default function TradeHistoryWidget({ trades }: TradeHistoryWidgetProps) {
  const [expanded, setExpanded] = useState<number | null>(null);

  const toggle = (id: number) => setExpanded((prev) => (prev === id ? null : id));

  return (
    <div className="rounded-xl border border-border bg-surface">

      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-white">Trade History</h2>
          <span className="rounded bg-surface2 px-1.5 py-0.5 text-[10px] font-medium text-muted">
            {trades.length} TRADES
          </span>
        </div>
        <span className="text-[11px] text-muted">Click row to view AI reasoning</span>
      </div>

      {trades.length === 0 ? (
        <div className="flex h-32 items-center justify-center">
          <p className="text-sm text-muted">No trades executed yet.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border text-left">
                <th className="w-8 px-3 py-2.5" />
                <th className="px-3 py-2.5 font-medium text-muted">Asset</th>
                <th className="px-3 py-2.5 font-medium text-muted">Type</th>
                <th className="px-3 py-2.5 font-medium text-muted text-right">Exec Price</th>
                <th className="px-3 py-2.5 font-medium text-muted text-right">Qty</th>
                <th className="px-3 py-2.5 font-medium text-muted text-right">Total</th>
                <th className="px-3 py-2.5 font-medium text-muted text-right">Time</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((t) => (
                <React.Fragment key={t.id}>
                  <tr
                    onClick={() => toggle(t.id)}
                    className="cursor-pointer border-b border-border/40 transition-colors hover:bg-white/[0.02]"
                  >
                    <td className="px-3 py-2.5 text-muted">
                      {expanded === t.id
                        ? <ChevronDown className="h-3.5 w-3.5" />
                        : <ChevronRight className="h-3.5 w-3.5" />}
                    </td>
                    <td className="px-3 py-2.5 font-semibold text-white">{t.symbol}</td>
                    <td className="px-3 py-2.5">
                      <span className={`rounded px-2 py-0.5 text-[10px] font-bold ${
                        t.side === "BUY"
                          ? "bg-positive/15 text-positive"
                          : "bg-negative/15 text-negative"
                      }`}>
                        {t.side}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-right text-white">{formatCurrency(t.price)}</td>
                    <td className="px-3 py-2.5 text-right text-muted">{formatQty(t.qty)}</td>
                    <td className="px-3 py-2.5 text-right font-medium text-white">
                      {formatCurrency(t.price * t.qty)}
                    </td>
                    <td className="px-3 py-2.5 text-right text-muted">{formatTime(t.created_at)}</td>
                  </tr>

                  {expanded === t.id && (
                    <tr className="border-b border-border/30 bg-surface2/60">
                      <td colSpan={7} className="px-6 py-3">
                        <div className="flex items-start gap-2">
                          <Sparkles className="h-3.5 w-3.5 shrink-0 text-accent mt-0.5" />
                          <div>
                            <span className="text-[10px] font-bold uppercase tracking-widest text-accent">AI Reasoning</span>
                            <p className="mt-0.5 text-xs leading-relaxed text-muted">
                              {t.rationale ?? "No reasoning recorded."}
                            </p>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
