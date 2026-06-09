"use client";

import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import {
  AreaChart, Area, XAxis, YAxis, Tooltip,
  ReferenceLine, ResponsiveContainer,
} from "recharts";
import { TrendingUp, TrendingDown, BarChart2 } from "lucide-react";
import type { AssetInfo, PricePoint } from "@/lib/mockAssets";
import { getKlines, type Candle } from "@/lib/api";

// ── Formatters ────────────────────────────────────────────────────────────────

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

function fmtDate(ts: number): string {
  return new Date(ts * 1000).toLocaleDateString("en-US", {
    month: "short", day: "numeric",
  });
}

// ── Constants ─────────────────────────────────────────────────────────────────

const RANGES = ["1H", "4H", "1D", "1W", "1M"] as const;
type Range = (typeof RANGES)[number];

const RANGE_SLICE: Record<Range, [number, number]> = {
  "1H": [170, 200],
  "4H": [120, 200],
  "1D": [0, 200],
  "1W": [0, 200],
  "1M": [0, 200],
};

const CANDLE_PARAMS: Record<Range, { interval: string; limit: number }> = {
  "1H": { interval: "1m",  limit: 60 },
  "4H": { interval: "5m",  limit: 48 },
  "1D": { interval: "1h",  limit: 24 },
  "1W": { interval: "4h",  limit: 42 },
  "1M": { interval: "1d",  limit: 30 },
};

function makeLabels(range: Range): string[] {
  switch (range) {
    case "1H": return ["60m", "45m", "30m", "15m", "now"];
    case "4H": return ["4h",  "3h",  "2h",  "1h",  "now"];
    case "1D": return ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00", "now"];
    case "1W": return ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "now"];
    case "1M": return ["W1", "W2", "W3", "W4", "now"];
  }
}

// ── Line chart tooltip ────────────────────────────────────────────────────────

function ChartTooltip({ active, payload }: { active?: boolean; payload?: { value: number }[] }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-border bg-surface2 px-3 py-1.5 shadow-xl">
      <p className="text-xs font-semibold text-white">{fmtPrice(payload[0].value)}</p>
    </div>
  );
}

// ── Candlestick SVG chart ─────────────────────────────────────────────────────

interface CandleTip { x: number; y: number; candle: Candle }

function CandlestickChart({ candles, width, height }: { candles: Candle[]; width: number; height: number }) {
  const [tip, setTip] = useState<CandleTip | null>(null);

  const PAD_R = 58;
  const PAD_T = 8;
  const PAD_B = 24;
  const chartW = Math.max(width - PAD_R, 1);
  const chartH = Math.max(height - PAD_T - PAD_B, 1);

  const rawMin = Math.min(...candles.map((c) => c.l));
  const rawMax = Math.max(...candles.map((c) => c.h));
  const span   = rawMax - rawMin || 1;
  const padP   = span * 0.08;
  const minP   = rawMin - padP;
  const range  = rawMax + padP - minP;

  const scaleY  = (p: number) => PAD_T + chartH - ((p - minP) / range) * chartH;
  const spacing = chartW / Math.max(candles.length, 1);
  const bodyW   = Math.max(2, Math.floor(spacing * 0.65));

  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((f) => ({
    price: minP + range * f,
    y: PAD_T + chartH * (1 - f),
  }));

  const step   = Math.max(1, Math.floor(candles.length / 5));
  const xTicks = candles
    .filter((_, i) => i % step === 0)
    .map((c) => ({ label: fmtDate(c.t), x: (candles.indexOf(c) + 0.5) * spacing }));

  return (
    <svg
      width={width}
      height={height}
      className="cursor-crosshair select-none overflow-visible"
      onMouseLeave={() => setTip(null)}
    >
      {/* Grid */}
      {yTicks.map((tk, i) => (
        <line key={i} x1={0} y1={tk.y} x2={chartW} y2={tk.y}
          stroke="#2B3139" strokeWidth={0.5} strokeDasharray="3,4" />
      ))}

      {/* Candles */}
      {candles.map((c, i) => {
        const cx   = (i + 0.5) * spacing;
        const bull = c.c >= c.o;
        const col  = bull ? "#0ECB81" : "#F6465D";
        const bTop = scaleY(Math.max(c.o, c.c));
        const bBot = scaleY(Math.min(c.o, c.c));
        const bH   = Math.max(bBot - bTop, 1.5);
        return (
          <g key={c.t}
            onMouseEnter={() => setTip({ x: cx, y: bTop, candle: c })}
            onMouseMove={() => setTip({ x: cx, y: bTop, candle: c })}
          >
            {/* Wick */}
            <line x1={cx} y1={scaleY(c.h)} x2={cx} y2={scaleY(c.l)}
              stroke={col} strokeWidth={1} />
            {/* Body */}
            <rect
              x={cx - bodyW / 2} y={bTop}
              width={bodyW} height={bH}
              fill={col} fillOpacity={bull ? 0.85 : 1}
              stroke={col} strokeWidth={0.5}
            />
          </g>
        );
      })}

      {/* Y-axis labels */}
      {yTicks.map((tk, i) => (
        <text key={i} x={chartW + 4} y={tk.y + 4}
          fill="#848E9C" fontSize={9} textAnchor="start">
          {fmtAxis(tk.price)}
        </text>
      ))}

      {/* X-axis labels */}
      {xTicks.map((tk, i) => (
        <text key={i} x={tk.x} y={height - 4}
          fill="#848E9C" fontSize={9} textAnchor="middle">
          {tk.label}
        </text>
      ))}

      {/* Tooltip */}
      {tip && (() => {
        const c    = tip.candle;
        const bull = c.c >= c.o;
        const col  = bull ? "#0ECB81" : "#F6465D";
        const TW   = 120;
        const TH   = 74;
        const tx   = Math.min(Math.max(tip.x - TW / 2, 2), chartW - TW - 2);
        const ty   = Math.max(tip.y - TH - 8, PAD_T);
        return (
          <g>
            <rect x={tx} y={ty} width={TW} height={TH} rx={6}
              fill="#1E2329" stroke="#2B3139" strokeWidth={1} />
            <text x={tx + 8} y={ty + 14} fill="#848E9C" fontSize={9}>{fmtDate(c.t)}</text>
            <text x={tx + 8} y={ty + 27} fill="#EAECEF" fontSize={9}>
              O <tspan fill={col}>{fmtAxis(c.o)}</tspan>{"  "}
              H <tspan fill={col}>{fmtAxis(c.h)}</tspan>
            </text>
            <text x={tx + 8} y={ty + 40} fill="#EAECEF" fontSize={9}>
              L <tspan fill={col}>{fmtAxis(c.l)}</tspan>{"  "}
              C <tspan fill={col}>{fmtAxis(c.c)}</tspan>
            </text>
            <text x={tx + 8} y={ty + 54} fill="#848E9C" fontSize={9}>Vol {fmtVol(c.v)}</text>
            <text x={tx + 8} y={ty + 68} fill={col} fontSize={9} fontWeight="600">
              {bull ? "▲ Bullish" : "▼ Bearish"}
            </text>
          </g>
        );
      })()}
    </svg>
  );
}

// Measure the container width with ResizeObserver, then render the SVG at that width.
function ResponsiveCandlestick({ candles, height }: { candles: Candle[]; height: number }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const obs = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width;
      if (w) setWidth(Math.floor(w));
    });
    obs.observe(el);
    setWidth(el.offsetWidth);
    return () => obs.disconnect();
  }, []);

  return (
    <div ref={containerRef} style={{ width: "100%", height }}>
      {width > 0 && candles.length > 0 && (
        <CandlestickChart candles={candles} width={width} height={height} />
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

type ChartType = "line" | "candle";

interface PriceChartProps {
  asset: AssetInfo | undefined;
}

export default function PriceChart({ asset }: PriceChartProps) {
  const [range,         setRange]         = useState<Range>("1D");
  const [chartType,     setChartType]     = useState<ChartType>("line");
  const [mounted,       setMounted]       = useState(false);
  const [candles,       setCandles]       = useState<Candle[]>([]);
  const [candleLoading, setCandleLoading] = useState(false);

  useEffect(() => { setMounted(true); }, []);
  useEffect(() => { setRange("1D"); setCandles([]); }, [asset?.symbol]);

  const fetchCandles = useCallback(async () => {
    if (!asset || chartType !== "candle") return;
    const { interval, limit } = CANDLE_PARAMS[range];
    setCandleLoading(true);
    try {
      const data = await getKlines(asset.symbol, interval, limit);
      setCandles(data);
    } catch {
      setCandles([]);
    } finally {
      setCandleLoading(false);
    }
  }, [asset, chartType, range]);

  useEffect(() => { fetchCandles(); }, [fetchCandles]);

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
  const sliceLen  = chartData.length;
  const tickIdxs  = labels.map((_, i) =>
    Math.round((i / (labels.length - 1)) * (sliceLen - 1)),
  );

  return (
    <div className="flex flex-col rounded-xl border border-border bg-surface">

      {/* ── Header ── */}
      <div className="border-b border-border px-3 py-2.5 sm:px-4 sm:py-3">
        <div className="flex flex-wrap items-start justify-between gap-2">
          {/* Left: symbol + price */}
          <div>
            <div className="flex flex-wrap items-center gap-1.5">
              <h2 className="text-base font-bold text-white">{asset.symbol}</h2>
              <span className="hidden text-sm text-muted sm:inline">/ {asset.name}</span>
              <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                asset.type === "crypto" ? "bg-accent/15 text-accent" : "bg-muted/15 text-muted"
              }`}>
                {asset.type === "crypto" ? "CRYPTO" : "STOCK"}
              </span>
              {/* Blinking LIVE indicator */}
              <span className="flex items-center gap-1">
                <span className="relative flex h-1.5 w-1.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-positive opacity-75" />
                  <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-positive" />
                </span>
                <span className="text-[10px] font-bold tracking-widest text-positive">LIVE</span>
              </span>
            </div>
            <div className="mt-1 flex flex-wrap items-baseline gap-2">
              <span className="text-xl font-bold tracking-tight text-white sm:text-2xl">
                {fmtPrice(asset.price)}
              </span>
              <span className={`flex items-center gap-1 text-sm font-semibold ${positive ? "text-positive" : "text-negative"}`}>
                {positive ? <TrendingUp className="h-3.5 w-3.5" /> : <TrendingDown className="h-3.5 w-3.5" />}
                {positive ? "+" : ""}{asset.change24h.toFixed(2)}%
              </span>
            </div>
          </div>

          {/* Right: 24h stats */}
          <div className="flex items-center gap-3 text-[11px] sm:gap-4">
            <div>
              <p className="text-muted">24h High</p>
              <p className="font-semibold text-positive">{fmtPrice(asset.high24h)}</p>
            </div>
            <div>
              <p className="text-muted">24h Low</p>
              <p className="font-semibold text-negative">{fmtPrice(asset.low24h)}</p>
            </div>
            <div className="hidden sm:block">
              <p className="text-muted">Volume</p>
              <p className="font-semibold text-white">{fmtVol(asset.volume24h)}</p>
            </div>
          </div>
        </div>

        {/* ── Controls: chart-type toggle + range tabs ── */}
        <div className="mt-2.5 flex flex-wrap items-center justify-between gap-2">
          {/* Line / Candle toggle */}
          <div className="flex items-center gap-0.5 rounded-md border border-border bg-bg p-0.5">
            {(["line", "candle"] as ChartType[]).map((t) => (
              <button
                key={t}
                onClick={() => setChartType(t)}
                className={`rounded px-2.5 py-0.5 text-[11px] font-semibold capitalize transition-all ${
                  chartType === t
                    ? "bg-accent/20 text-accent"
                    : "text-muted hover:text-white"
                }`}
              >
                {t === "line" ? "Line" : "Candles"}
              </button>
            ))}
          </div>

          {/* Range tabs */}
          <div className="flex items-center gap-0.5">
            {RANGES.map((r) => (
              <button
                key={r}
                onClick={() => setRange(r)}
                className={`rounded-md px-2 py-0.5 text-[11px] font-semibold transition-all ${
                  range === r ? "bg-accent text-bg" : "text-muted hover:text-white"
                }`}
              >
                {r}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Chart area ── */}
      <div className="flex-1 px-1 pb-1 pt-3 sm:p-3 sm:pt-4">
        {!mounted ? (
          <div className="h-[240px] animate-pulse rounded-lg bg-surface2" />
        ) : chartType === "line" ? (
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart
              key={`${asset.symbol}-${range}`}
              data={chartData}
              margin={{ top: 4, right: 4, bottom: 0, left: 0 }}
            >
              <defs>
                <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%"   stopColor={lineColor} stopOpacity={0.22} />
                  <stop offset="100%" stopColor={lineColor} stopOpacity={0}    />
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
          /* ── Candlestick mode ── */
          <div className="relative h-[240px]">
            {candleLoading && (
              <div className="absolute inset-0 z-10 flex items-center justify-center rounded-lg bg-surface/60">
                <div className="h-6 w-6 animate-spin rounded-full border-2 border-border border-t-accent" />
              </div>
            )}
            {candles.length > 0 ? (
              <ResponsiveCandlestick candles={candles} height={240} />
            ) : !candleLoading ? (
              <div className="flex h-full items-center justify-center text-xs text-muted">
                No candle data available
              </div>
            ) : null}
          </div>
        )}
      </div>

      {/* ── Footer: support / resistance ── */}
      <div className="flex items-center justify-between border-t border-border px-3 py-1.5 text-[11px] sm:px-4">
        <span className="text-muted">
          Support <span className="font-semibold text-positive">{fmtPrice(asset.support)}</span>
        </span>
        <span className="flex items-center gap-1 text-muted">
          <BarChart2 className="h-3 w-3" />
          {chartType === "candle" ? "Binance Candles" : "Live Chart"}
        </span>
        <span className="text-muted">
          Resistance <span className="font-semibold text-negative">{fmtPrice(asset.resistance)}</span>
        </span>
      </div>
    </div>
  );
}
