"use client";

import { useState, useEffect } from "react";
import { PieChart, Pie, Cell, Tooltip } from "recharts";
import type { PositionOut } from "@/lib/api";
import { formatCurrency, formatQty, formatSignedCurrency, formatPercent, pnlColor } from "@/lib/format";

const PALETTE = ["#0ECB81", "#4DA7FF", "#FCD535", "#F6465D", "#A855F7", "#FF9D42"];

function DonutChart({ data }: { data: { name: string; value: number; pct: number }[] }) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted) return <div className="h-40 w-40" />;

  const total = data.reduce((s, d) => s + d.value, 0);

  return (
    <div className="relative">
      <PieChart width={160} height={160}>
        <Pie data={data} cx={75} cy={75} innerRadius={50} outerRadius={72} paddingAngle={2} dataKey="value" strokeWidth={0}>
          {data.map((_, i) => (
            <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{ background: "#1E2329", border: "1px solid #2B3139", borderRadius: 6, fontSize: 10, padding: "4px 8px" }}
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          formatter={(v: any, _: any, props: any) => [
            `${formatCurrency(Number(v))} (${props.payload?.pct.toFixed(1)}%)`,
            props.payload?.name ?? "",
          ]}
        />
      </PieChart>
      {/* Center label */}
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-[10px] text-muted">Total</span>
        <span className="text-[13px] font-bold text-white leading-tight">{formatCurrency(total)}</span>
      </div>
    </div>
  );
}

interface PortfolioWidgetProps {
  positions: PositionOut[];
}

export default function PortfolioWidget({ positions }: PortfolioWidgetProps) {
  const totalValue = positions.reduce((s, p) => s + p.market_value, 0);
  const chartData = positions.map((p) => ({
    name: p.symbol,
    value: p.market_value,
    pct: totalValue > 0 ? (p.market_value / totalValue) * 100 : 0,
  }));

  return (
    <div className="flex flex-col rounded-xl border border-border bg-surface">

      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-white">Portfolio Positions</h2>
          <span className="rounded bg-surface2 px-1.5 py-0.5 text-[10px] font-medium text-muted">
            {positions.length} ASSETS
          </span>
        </div>
        <span className="text-[11px] text-muted">{formatCurrency(totalValue)}</span>
      </div>

      {positions.length === 0 ? (
        <div className="flex h-48 items-center justify-center">
          <p className="text-sm text-muted">No open positions</p>
        </div>
      ) : (
        <div className="flex flex-col lg:flex-row">

          {/* Donut + Legend */}
          <div className="flex shrink-0 items-center gap-4 p-4">
            <DonutChart data={chartData} />
            <div className="space-y-2">
              {chartData.map((d, i) => (
                <div key={d.name} className="flex items-center gap-2">
                  <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: PALETTE[i % PALETTE.length] }} />
                  <span className="text-xs text-muted w-10">{d.name}</span>
                  <span className="text-xs font-semibold text-white">{d.pct.toFixed(1)}%</span>
                </div>
              ))}
            </div>
          </div>

          {/* Positions table */}
          <div className="flex-1 overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border text-left">
                  <th className="px-3 py-2.5 font-medium text-muted">Asset</th>
                  <th className="px-3 py-2.5 font-medium text-muted text-right">Qty</th>
                  <th className="px-3 py-2.5 font-medium text-muted text-right">Avg Buy</th>
                  <th className="px-3 py-2.5 font-medium text-muted text-right">Price</th>
                  <th className="px-3 py-2.5 font-medium text-muted text-right">Value</th>
                  <th className="px-3 py-2.5 font-medium text-muted text-right">PnL</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((p, i) => {
                  const pnlPct = p.avg_price > 0
                    ? ((p.current_price - p.avg_price) / p.avg_price) * 100
                    : 0;
                  return (
                    <tr key={p.symbol} className="border-b border-border/40 transition-colors hover:bg-white/[0.02]">
                      <td className="px-3 py-2.5">
                        <div className="flex items-center gap-2">
                          <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: PALETTE[i % PALETTE.length] }} />
                          <span className="font-semibold text-white">{p.symbol}</span>
                        </div>
                      </td>
                      <td className="px-3 py-2.5 text-right text-muted">{formatQty(p.qty)}</td>
                      <td className="px-3 py-2.5 text-right text-muted">{formatCurrency(p.avg_price)}</td>
                      <td className="px-3 py-2.5 text-right text-white">{formatCurrency(p.current_price)}</td>
                      <td className="px-3 py-2.5 text-right font-medium text-white">{formatCurrency(p.market_value)}</td>
                      <td className={`px-3 py-2.5 text-right font-medium ${pnlColor(p.unrealized_pnl)}`}>
                        <div>{formatSignedCurrency(p.unrealized_pnl)}</div>
                        <div className="text-[10px] opacity-70">{formatPercent(pnlPct)}</div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
