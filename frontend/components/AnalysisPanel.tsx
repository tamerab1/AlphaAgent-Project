"use client";

import { useRef, useState, useEffect } from "react";
import { Zap, ImagePlus, X, Play, ChevronRight } from "lucide-react";
import { readChart, type ChartReading } from "@/lib/api";
import { streamAnalyze, type AnalyzeEvent } from "@/lib/sse";
import ChartReadingCard from "@/components/ChartReadingCard";

const NODE_LABELS: Record<string, string> = {
  ingest:        "Ingesting market data",
  analyst_agent: "Analyst agent",
  risk_agent:    "Risk manager",
  execute:       "Executing trade",
  log_rejection: "Trade rejected",
  done:          "Pipeline complete",
};

const QUICK_SYMBOLS = ["BTC", "ETH", "SOL", "TSLA", "NVDA", "AAPL"];

export default function AnalysisPanel({
  portfolioId,
  onComplete,
  defaultSymbol,
}: {
  portfolioId: number;
  onComplete: () => void;
  defaultSymbol?: string;
}) {
  const [symbol, setSymbol] = useState(defaultSymbol ?? "BTC");

  // Keep symbol in sync when the globally selected asset changes
  useEffect(() => {
    if (defaultSymbol) setSymbol(defaultSymbol);
  }, [defaultSymbol]);
  const [events, setEvents]               = useState<AnalyzeEvent[]>([]);
  const [running, setRunning]             = useState(false);
  const [error, setError]                 = useState<string | null>(null);
  const [chartImage, setChartImage]       = useState<string | null>(null);
  const [reading, setReading]             = useState<ChartReading | null>(null);
  const [readingLoading, setReadingLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const fileRef  = useRef<HTMLInputElement | null>(null);

  function onPickImage(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) { setError("Please choose a PNG or JPG image."); return; }
    setReading(null);
    const reader = new FileReader();
    reader.onload = () => setChartImage(reader.result as string);
    reader.readAsDataURL(file);
  }

  function clearImage() {
    setChartImage(null);
    setReading(null);
    if (fileRef.current) fileRef.current.value = "";
  }

  async function analyzeChart() {
    if (!chartImage || readingLoading) return;
    setReadingLoading(true);
    setError(null);
    try {
      const sym = symbol.trim().toUpperCase() || undefined;
      setReading(await readChart(chartImage, sym));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chart read failed.");
    } finally {
      setReadingLoading(false);
    }
  }

  async function run() {
    const sym = symbol.trim().toUpperCase();
    if (!sym || running) return;
    setRunning(true);
    setError(null);
    setEvents([]);
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      await streamAnalyze(portfolioId, sym, (event) => setEvents((prev) => [...prev, event]), controller.signal, chartImage);
      onComplete();
    } catch (err) {
      if (!controller.signal.aborted) setError(err instanceof Error ? err.message : "Analysis failed.");
    } finally {
      setRunning(false);
      abortRef.current = null;
    }
  }

  return (
    <div className="rounded-xl border border-border bg-surface">

      {/* Header */}
      <div className="flex items-center gap-2 border-b border-border px-4 py-3">
        <Zap className="h-4 w-4 text-accent" />
        <h2 className="text-sm font-semibold text-white">Run Analysis</h2>
        <span className="rounded bg-surface2 px-1.5 py-0.5 text-[10px] font-medium text-muted">
          AI PIPELINE
        </span>
      </div>

      <div className="p-4 space-y-4">

        {/* Step 1 — Visual chart upload */}
        <div className="rounded-lg border border-border/60 bg-surface2 p-3.5">
          <p className="text-xs font-semibold text-white">1 · Visual chart analysis <span className="font-normal text-muted">(optional)</span></p>
          <p className="mt-0.5 text-[11px] text-muted">Upload a chart screenshot — AI reads support / resistance / patterns.</p>
          <div className="mt-3 flex flex-wrap items-center gap-2.5">
            <label className="flex cursor-pointer items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs text-muted transition-colors hover:border-muted/50 hover:text-white">
              <ImagePlus className="h-3.5 w-3.5" />
              {chartImage ? "Change chart" : "Attach chart"}
              <input ref={fileRef} type="file" accept="image/png,image/jpeg" onChange={onPickImage} className="hidden" />
            </label>

            {chartImage && (
              <>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={chartImage} alt="chart preview" className="h-10 w-16 rounded-lg border border-border object-cover" />
                <button
                  onClick={analyzeChart}
                  disabled={readingLoading}
                  className="rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-bg transition-opacity hover:opacity-90 disabled:opacity-50"
                >
                  {readingLoading ? "Reading…" : "Analyze chart"}
                </button>
                <button onClick={clearImage} disabled={readingLoading} className="flex items-center gap-1 text-[11px] text-muted hover:text-negative transition-colors">
                  <X className="h-3 w-3" /> Remove
                </button>
              </>
            )}
          </div>
          {reading && <ChartReadingCard reading={reading} />}
        </div>

        {/* Step 2 — Agent pipeline */}
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold text-white">2 · Agent trade analysis</p>
            <p className="mt-0.5 text-[11px] text-muted">Stream the analyst → risk → execute reasoning live.</p>
          </div>
          <div className="flex items-center gap-2">
            <input
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              disabled={running}
              placeholder="Symbol"
              className="w-24 rounded-lg border border-border bg-surface2 px-3 py-2 text-xs font-semibold uppercase outline-none transition-colors focus:border-accent disabled:opacity-60"
            />
            <button
              onClick={run}
              disabled={running}
              className="flex items-center gap-1.5 rounded-lg bg-accent px-4 py-2 text-xs font-bold text-bg transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              <Play className="h-3 w-3" />
              {running ? "Analyzing…" : "Run Analysis"}
            </button>
          </div>
        </div>

        {/* Quick pick */}
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] text-muted">Quick pick:</span>
          {QUICK_SYMBOLS.map((s) => (
            <button
              key={s}
              onClick={() => setSymbol(s)}
              disabled={running}
              className={`rounded-full border px-2.5 py-0.5 text-[11px] font-medium transition-colors disabled:opacity-60 ${
                symbol.trim().toUpperCase() === s
                  ? "border-accent bg-accent/10 text-accent"
                  : "border-border text-muted hover:border-muted/50 hover:text-white"
              }`}
            >
              {s}
            </button>
          ))}
        </div>

        {/* Error */}
        {error && (
          <p className="rounded-lg border border-negative/30 bg-negative/10 px-3 py-2 text-xs text-negative">
            {error}
          </p>
        )}

        {/* Live event stream */}
        {events.length > 0 && (
          <ol className="space-y-2 border-t border-border pt-3">
            {events.map((ev, i) => (
              <li key={i} className="animate-slide-up flex gap-2.5">
                <ChevronRight className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent" />
                <div className="min-w-0">
                  <p className="text-xs font-medium text-white">
                    {NODE_LABELS[ev.node] ?? ev.node}
                    {ev.node === "analyst_agent" && ev.analyst && (
                      <span className={`ml-2 font-bold ${ev.analyst.action === "BUY" ? "text-positive" : ev.analyst.action === "SELL" ? "text-negative" : "text-muted"}`}>
                        {ev.analyst.action} ({Math.round(ev.analyst.confidence * 100)}%)
                      </span>
                    )}
                    {ev.node === "risk_agent" && ev.risk && (
                      <span className={`ml-2 ${ev.risk.approved ? "text-positive" : "text-negative"}`}>
                        {ev.risk.approved ? "approved" : "rejected"}
                      </span>
                    )}
                  </p>
                  {ev.message && <p className="text-[11px] text-muted">{ev.message}</p>}
                  {ev.node === "ingest" && ev.market && (
                    <p className="text-[11px] text-muted">
                      Price ${ev.market.price.toFixed(2)} · RSI {ev.market.rsi.toFixed(1)}
                    </p>
                  )}
                  {ev.node === "analyst_agent" && ev.analyst?.target_price != null && ev.analyst?.stop_loss != null && (
                    <p className="text-[11px] text-muted">
                      Target <span className="text-positive">${ev.analyst.target_price.toFixed(2)}</span>
                      {" · "}Stop <span className="text-negative">${ev.analyst.stop_loss.toFixed(2)}</span>
                    </p>
                  )}
                </div>
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}
