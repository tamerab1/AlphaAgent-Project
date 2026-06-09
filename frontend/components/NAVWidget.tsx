"use client";

import { useState, useEffect } from "react";
import { TrendingUp, TrendingDown, DollarSign, Briefcase } from "lucide-react";
import { AreaChart, Area, Tooltip } from "recharts";
import type { PortfolioStatus } from "@/lib/api";
import { formatCurrency, formatSignedCurrency, formatPercent } from "@/lib/format";
import { MOCK_PNL_HISTORY } from "@/lib/mockData";

interface NAVWidgetProps {
  status: PortfolioStatus;
}

// Recharts must only render on the client (it reads window dimensions).
function Sparkline({ positive }: { positive: boolean }) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted) return <div className="h-16 w-32" />;

  const color = positive ? "#0ECB81" : "#F6465D";
  return (
    <AreaChart width={128} height={64} data={MOCK_PNL_HISTORY} margin={{ top: 4, right: 2, bottom: 4, left: 2 }}>
      <defs>
        <linearGradient id="spark" x1="0" y1="0" x2="0" y2="1">
          <stop offset="5%"  stopColor={color} stopOpacity={0.3} />
          <stop offset="95%" stopColor={color} stopOpacity={0}   />
        </linearGradient>
      </defs>
      <Area type="monotone" dataKey="v" stroke={color} strokeWidth={1.5} fill="url(#spark)" dot={false} />
      <Tooltip
        contentStyle={{ background: "#1E2329", border: "1px solid #2B3139", borderRadius: 6, fontSize: 10, padding: "4px 8px" }}
        formatter={(v) => [v != null ? formatCurrency(Number(v)) : "", "NAV"]}
        labelFormatter={() => ""}
      />
    </AreaChart>
  );
}

export default function NAVWidget({ status }: NAVWidgetProps) {
  const pnlPositive = status.unrealized_pnl >= 0;
  const invested = status.positions_value;
  const cashPct  = status.total_value > 0 ? (status.cash_balance  / status.total_value) * 100 : 0;
  const invPct   = status.total_value > 0 ? (invested / status.total_value) * 100 : 0;
  const pnlPct   = (status.total_value - status.unrealized_pnl) > 0
    ? (status.unrealized_pnl / (status.total_value - status.unrealized_pnl)) * 100
    : 0;

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">

      {/* ── Total NAV (spans 2 cols on all sizes) ── */}
      <div className="col-span-2 flex items-center justify-between overflow-hidden rounded-xl border border-border bg-surface p-4">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-muted">Net Asset Value</p>
          <p className="mt-1 text-[28px] font-bold leading-none tracking-tight text-white">
            {formatCurrency(status.total_value)}
          </p>
          <div className={`mt-2.5 flex items-center gap-1.5 text-sm font-medium ${pnlPositive ? "text-positive" : "text-negative"}`}>
            {pnlPositive ? <TrendingUp className="h-3.5 w-3.5" /> : <TrendingDown className="h-3.5 w-3.5" />}
            <span>{formatSignedCurrency(status.unrealized_pnl)}</span>
            <span className="text-muted/60 text-xs">({formatPercent(pnlPct)})</span>
            <span className="ml-0.5 text-[11px] text-muted">unrealized</span>
          </div>
        </div>
        <div className="opacity-90">
          <Sparkline positive={pnlPositive} />
        </div>
      </div>

      {/* ── Cash Balance ── */}
      <div className="rounded-xl border border-border bg-surface p-4">
        <div className="flex items-center justify-between">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-muted">Cash</p>
          <DollarSign className="h-3.5 w-3.5 text-muted" />
        </div>
        <p className="mt-2 text-xl font-bold text-white">{formatCurrency(status.cash_balance)}</p>
        <p className="mt-0.5 text-[11px] text-muted">{cashPct.toFixed(1)}% of portfolio</p>
        <div className="mt-3 h-1 w-full overflow-hidden rounded-full bg-border">
          <div
            className="h-full rounded-full bg-accent transition-all duration-700"
            style={{ width: `${cashPct}%` }}
          />
        </div>
      </div>

      {/* ── Invested ── */}
      <div className="rounded-xl border border-border bg-surface p-4">
        <div className="flex items-center justify-between">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-muted">Invested</p>
          <Briefcase className="h-3.5 w-3.5 text-muted" />
        </div>
        <p className="mt-2 text-xl font-bold text-white">{formatCurrency(invested)}</p>
        <p className="mt-0.5 text-[11px] text-muted">{status.positions.length} open positions</p>
        <div className="mt-3 h-1 w-full overflow-hidden rounded-full bg-border">
          <div
            className="h-full rounded-full bg-positive transition-all duration-700"
            style={{ width: `${invPct}%` }}
          />
        </div>
      </div>
    </div>
  );
}
