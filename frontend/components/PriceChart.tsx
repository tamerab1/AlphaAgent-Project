"use client";

import { useState, useEffect, useMemo } from "react";
import {
  AreaChart, Area, XAxis, YAxis, Tooltip,
  ReferenceLine, ResponsiveContainer,
} from "recharts";
import { TrendingUp, TrendingDown, BarChart2 } from "lucide-react";
import type { AssetInfo, PricePoint } from "@/lib/mockAssets";

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtPrice(p: number): string {
  if (p >= 1_000_000) return `$${(p / 1_000_000).toFixed(2)}M`;
  if (p >= 1_000)     return `$${(p / 1_000).toFixed(2)}K`;
  if (p >= 1)         return `$${p.toFixed(2)}`;
  return `$${p.toFixed(5)}`;
}

function fmtAxis(p: number): string {
  if (p >= 1_000_000) return `${(p / 1_000_000).toFixed(1)}M`;
  if (p >= 1_000)     return `${(p / 1_000).toFixed(1)}K`;
  if (p >= 1)         return p.toFixed(2);
  return p.toFixed(4);
}

function fmtVol(v: number): string {
  if (v >= 1e9) return `$${(v / 1e9).toFixed(1)}B`;
  if (v >= 1e6) return `$${(v / 1e6).toFixed(0)}M`;
  return `$${v.toLocaleString()}`;
}

// ── Constants ─────────────────────────────────────────────────────────────────

const RANGES = ["1H", "4H", "1D", "1W", "1M"] as const;
type Range = (typeof RANGES)[number];

const RANGE_SLICE: Record<Range, [number, number]> = {
  "1H":  [170, 200],
  "4H":  [120, 200],
  "1D":  [0,   200],
  "1W":  [0,   200],
  "1M":  [0,   200],
};

// Time labels generated per range
function makeLabels(range: Range): string[] {
  switch (range) {
    case "1H":  return ["60m","45m","30m","15m","now"];
    case "4H":  return ["4h", "3h", "2h", "1h", "now"];
    case "1D":  return ["00:00","04:00","08:00","12:00","16:00","20:00","now"];
    case "1W":  return ["Mon","Tue","Wed","Thu","Fri","Sat","now"];
    case "1M":  return ["W1","W2","W3","W4","now"];
  }
}

// ── Custom tooltip ────────────────────────────────────────────────────────────

function ChartTooltip({ active, payload }: { active?: boolean; payload?: { value: number }[] }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-border bg-surface2 px-3 py-1.5 shadow-xl">
      <p className="text-xs font-semibold text-white">{fmtPrice(payload[0].value)}</p>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface PriceChartProps {
  asset: AssetInfo | undefined;
}

export default function PriceChart({ asset }: PriceChartProps) {
  const [range,   setRange]   = useState<Range>("1D");
  const [mounted, setMounted] = useState(false);

  useEffect(() => { setMounted(true); }, []);

  // Reset range to 1D whenever the selected asset changes
  useEffect(() => { setRange("1D"); }, [asset?.symbol]);

  const { chartData, minP, maxP } = useMemo(() => {
    if (!asset) return { chartData: [], minP: 0, maxP: 0 };
    const [s, e] = RANGE_SLICE[range];
    const slice: PricePoint[] = asset.history.slice(s, e);
    const prices = slice.map((d) => d.p);
    const lo = Math.min(...prices);
    const hi = Math.max(...prices);
    const pad = (hi - lo) * 0.12;
    return { chartData: slice, minP: lo - pad, maxP: hi + pad };
  }, [asset, range]);

  if (!asset) return (
    <div className="flex h-[380px] items-center justify-center rounded-xl border border-border bg-surface">
      <p className="text-sm text-muted">Select an asset to view its chart.</p>
    </div>
  );

  const positive  = asset.change24h >= 0;
  const lineColor = positive ? "#0ECB81" : "#F6465D";
  const gradId    = `grad-${asset.symbol}`;
  const labels    = makeLabels(range);

  // Map tick indices across the slice
  const sliceLen  = chartData.length;
  const tickCount = labels.length;
  const tickIdxs  = labels.map((_, i) =>
    Math.round((i / (tickCount - 1)) * (sliceLen - 1)),
  );

  return (
    <div className="flex flex-col rounded-xl border border-border bg-surface">

      {/* ── Header ── */}
      <div className="border-b border-border px-4 py-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-white">{asset.symbol}</h2>
              <span className="text-sm text-muted">/</span>
              <span className="text-sm text-muted">{asset.name}</span>
              <span className={`rounded text-[10px] px-1.5 py-0.5 font-bold ${
                asset.type === "crypto" ? "bg-accent/15 text-accent" : "bg-muted/15 text-muted"
              }`}>
                {asset.type === "crypto" ? "CRYPTO" : "STOCK"}
              </span>
            </div>
            <div className="mt-1 flex items-baseline gap-2.5 flex-wrap">
              <span className="text-2xl font-bold tracking-tight text-white">
                {fmtPrice(asset.price)}
              </span>
              <span className={`flex items-center gap-1 text-sm font-semibold ${positive ? "text-positive" : "text-negative"}`}>
                {positive ? <TrendingUp className="h-3.5 w-3.5" /> : <TrendingDown className="h-3.5 w-3.5" />}
                {positive ? "+" : ""}{asset.change24h.toFixed(2)}%
              </span>
            </div>
          </div>

          {/* Meta stats */}
          <div className="flex items-center gap-4 text-[11px]">
            <div>
              <p className="text-muted">24h High</p>
              <p className="font-semibold text-positive">{fmtPrice(asset.high24h)}</p>
            </div>
            <div>
              <p className="text-muted">24h Low</p>
              <p className="font-semibold text-negative">{fmtPrice(asset.low24h)}</p>
            </div>
            <div>
              <p className="text-muted">Volume</p>
              <p className="font-semibold text-white">{fmtVol(asset.volume24h)}</p>
            </div>
          </div>
        </div>

        {/* ── Range tabs ── */}
        <div className="mt-3 flex items-center gap-1">
          {RANGES.map((r) => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className={`rounded-md px-2.5 py-1 text-[11px] font-semibold transition-all ${
                range === r
                  ? "bg-accent text-bg"
                  : "text-muted hover:text-white"
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {/* ── Chart ── */}
      <div className="flex-1 p-3 pt-4">
        {mounted ? (
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart
              key={`${asset.symbol}-${range}`}
              data={chartData}
              margin={{ top: 4, right: 4, bottom: 0, left: 0 }}
            >
              <defs>
                <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%"  stopColor={lineColor} stopOpacity={0.22} />
                  <stop offset="100%" stopColor={lineColor} stopOpacity={0}   />
                </linearGradient>
              </defs>

              <XAxis
                dataKey="t"
                tickLine={false}
                axisLine={false}
                tick={{ fill: "#848E9C", fontSize: 10 }}
                ticks={tickIdxs}
                tickFormatter={(idx: number) => {
                  const pos = tickIdxs.indexOf(idx);
                  return pos >= 0 ? (labels[pos] ?? "") : "";
                }}
              />
              <YAxis
                domain={[minP, maxP]}
                tickLine={false}
                axisLine={false}
                tick={{ fill: "#848E9C", fontSize: 10 }}
                tickFormatter={fmtAxis}
                width={60}
                tickCount={5}
                orientation="right"
              />
              <Tooltip content={<ChartTooltip />} cursor={{ stroke: "#2B3139", strokeWidth: 1 }} />

              {/* Current price reference line */}
              <ReferenceLine
                y={asset.price}
                stroke={lineColor}
                strokeDasharray="3 3"
                strokeWidth={0.8}
                strokeOpacity={0.6}
              />

              <Area
                type="monotone"
                dataKey="p"
                stroke={lineColor}
                strokeWidth={1.5}
                fill={`url(#${gradId})`}
                dot={false}
                activeDot={{ r: 3, fill: lineColor, strokeWidth: 0 }}
                isAnimationActive
                animationDuration={500}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-[240px] animate-pulse rounded-lg bg-surface2" />
        )}
      </div>

      {/* ── Footer: key levels ── */}
      <div className="flex items-center justify-between border-t border-border px-4 py-2 text-[11px]">
        <span className="text-muted">
          Support <span className="font-semibold text-positive">{fmtPrice(asset.support)}</span>
        </span>
        <span className="flex items-center gap-1 text-muted">
          <BarChart2 className="h-3 w-3" /> Live Chart
        </span>
        <span className="text-muted">
          Resistance <span className="font-semibold text-negative">{fmtPrice(asset.resistance)}</span>
        </span>
      </div>
    </div>
  );
}
