"use client";

import { useRef, useState } from "react";
import { streamAnalyze, type AnalyzeEvent } from "@/lib/sse";

const NODE_LABELS: Record<string, string> = {
  ingest: "Ingest market data",
  analyst_agent: "Analyst agent",
  risk_agent: "Risk manager",
  execute: "Execute trade",
  log_rejection: "Trade rejected",
  done: "Done",
};

// Quick-pick symbols for the demo (seed RSI makes these decisions predictable).
const QUICK_SYMBOLS = ["TSLA", "NVDA", "AAPL", "MSFT", "GOOGL"];

export default function AnalysisPanel({
  portfolioId,
  onComplete,
}: {
  portfolioId: number;
  onComplete: () => void;
}) {
  const [symbol, setSymbol] = useState("AAPL");
  const [events, setEvents] = useState<AnalyzeEvent[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chartImage, setChartImage] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);

  function onPickImage(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setError("Please choose a PNG or JPG image.");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => setChartImage(reader.result as string);
    reader.readAsDataURL(file); // -> "data:image/png;base64,..."
  }

  function clearImage() {
    setChartImage(null);
    if (fileRef.current) fileRef.current.value = "";
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
      await streamAnalyze(
        portfolioId,
        sym,
        (event) => setEvents((prev) => [...prev, event]),
        controller.signal,
        chartImage
      );
      onComplete();
    } catch (err) {
      if (!controller.signal.aborted) {
        setError(err instanceof Error ? err.message : "Analysis failed.");
      }
    } finally {
      setRunning(false);
      abortRef.current = null;
    }
  }

  return (
    <div className="rounded-lg border border-border bg-surface p-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">Run Analysis</h2>
          <p className="text-sm text-muted">
            Stream the analyst → risk → execute reasoning live.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <input
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            disabled={running}
            placeholder="Symbol"
            className="w-28 rounded-md border border-border bg-bg px-3 py-2 text-sm uppercase outline-none focus:border-accent"
          />
          <button
            onClick={run}
            disabled={running}
            className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-60"
          >
            {running ? "Analyzing…" : "Run Analysis"}
          </button>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <span className="text-xs text-muted">Quick pick:</span>
        {QUICK_SYMBOLS.map((s) => (
          <button
            key={s}
            onClick={() => setSymbol(s)}
            disabled={running}
            className={`rounded-full border px-2.5 py-0.5 text-xs transition disabled:opacity-60 ${
              symbol.trim().toUpperCase() === s
                ? "border-accent text-accent"
                : "border-border text-muted hover:text-white"
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <label className="cursor-pointer rounded-md border border-border px-3 py-1.5 text-sm text-muted transition hover:text-white">
          {chartImage ? "Change chart" : "Attach chart (optional)"}
          <input
            ref={fileRef}
            type="file"
            accept="image/png,image/jpeg"
            onChange={onPickImage}
            disabled={running}
            className="hidden"
          />
        </label>
        {chartImage && (
          <div className="flex items-center gap-2">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={chartImage}
              alt="chart preview"
              className="h-10 w-16 rounded border border-border object-cover"
            />
            <button
              onClick={clearImage}
              disabled={running}
              className="text-xs text-muted underline hover:text-white"
            >
              Remove
            </button>
          </div>
        )}
      </div>

      {error && (
        <p className="mt-4 rounded-md border border-negative/40 bg-negative/10 px-3 py-2 text-sm text-negative">
          {error}
        </p>
      )}

      {events.length > 0 && (
        <ol className="mt-5 space-y-3">
          {events.map((ev, i) => (
            <li key={i} className="flex gap-3">
              <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-accent" />
              <div className="min-w-0">
                <p className="text-sm font-medium">
                  {NODE_LABELS[ev.node] ?? ev.node}
                  {ev.node === "analyst_agent" && ev.analyst && (
                    <span className="ml-2 text-accent">
                      {ev.analyst.action} ({Math.round(ev.analyst.confidence * 100)}%)
                    </span>
                  )}
                  {ev.node === "risk_agent" && ev.risk && (
                    <span
                      className={`ml-2 ${
                        ev.risk.approved ? "text-positive" : "text-negative"
                      }`}
                    >
                      {ev.risk.approved ? "approved" : "rejected"}
                    </span>
                  )}
                </p>
                {ev.message && (
                  <p className="text-sm text-muted">{ev.message}</p>
                )}
                {ev.node === "ingest" && ev.market && (
                  <p className="text-sm text-muted">
                    Price ${ev.market.price.toFixed(2)} · RSI{" "}
                    {ev.market.rsi.toFixed(1)}
                  </p>
                )}
                {ev.node === "analyst_agent" &&
                  ev.analyst?.target_price != null &&
                  ev.analyst?.stop_loss != null && (
                    <p className="text-sm text-muted">
                      Target ${ev.analyst.target_price.toFixed(2)} · Stop $
                      {ev.analyst.stop_loss.toFixed(2)}
                    </p>
                  )}
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
