"use client";

import { useState } from "react";
import { toggleMode, type TradingMode } from "@/lib/api";

export default function ModeToggle({ portfolioId }: { portfolioId: number }) {
  const [mode, setMode] = useState<TradingMode>("paper");
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function select(next: TradingMode) {
    if (pending) return;
    setPending(true);
    setMessage(null);
    try {
      const res = await toggleMode(portfolioId, next);
      // Backend forces paper-only; trust the returned mode.
      setMode(res.mode as TradingMode);
      if (res.message) setMessage(res.message);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Failed to toggle mode.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="inline-flex rounded-lg border border-border bg-surface p-1">
        {(["paper", "live"] as TradingMode[]).map((m) => (
          <button
            key={m}
            onClick={() => select(m)}
            disabled={pending}
            className={`rounded-md px-3 py-1 text-sm font-medium capitalize transition ${
              mode === m
                ? "bg-accent text-white"
                : "text-muted hover:text-white"
            } ${pending ? "opacity-60" : ""}`}
          >
            {m}
          </button>
        ))}
      </div>
      {message && <p className="text-xs text-muted">{message}</p>}
    </div>
  );
}
