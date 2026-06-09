"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Newspaper, Search, RefreshCw, X, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { getNews, type NewsItem } from "@/lib/api";
import { MOCK_NEWS } from "@/lib/mockData";

// ── Helpers ──────────────────────────────────────────────────────────────────

function timeAgo(iso: string): string {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60)   return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

// ── Sentiment config ─────────────────────────────────────────────────────────

const SENTIMENT = {
  bullish: {
    badge:  "border border-positive/50 bg-positive/10 text-positive shadow-[0_0_10px_rgba(14,203,129,0.25)]",
    symbol: "border-positive/30 bg-positive/5 text-positive",
    dot:    "bg-positive",
    icon:   TrendingUp,
    label:  "BULLISH",
  },
  bearish: {
    badge:  "border border-negative/50 bg-negative/10 text-negative shadow-[0_0_10px_rgba(246,70,93,0.25)]",
    symbol: "border-negative/30 bg-negative/5 text-negative",
    dot:    "bg-negative",
    icon:   TrendingDown,
    label:  "BEARISH",
  },
  neutral: {
    badge:  "border border-border bg-surface2 text-muted",
    symbol: "border-border bg-surface2 text-muted",
    dot:    "bg-muted",
    icon:   Minus,
    label:  "NEUTRAL",
  },
} as const;

// ── Sub-components ────────────────────────────────────────────────────────────

function SentimentBadge({ sentiment }: { sentiment: NewsItem["sentiment"] }) {
  const s = SENTIMENT[sentiment];
  const Icon = s.icon;
  return (
    <span className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold tracking-wider ${s.badge}`}>
      <Icon className="h-2.5 w-2.5" strokeWidth={2.5} />
      {s.label}
    </span>
  );
}

function SymbolPill({ symbol, sentiment }: { symbol: string; sentiment: NewsItem["sentiment"] }) {
  return (
    <span className={`rounded border px-1.5 py-0.5 text-[10px] font-bold ${SENTIMENT[sentiment].symbol}`}>
      {symbol}
    </span>
  );
}

function NewsCard({ item }: { item: NewsItem }) {
  const s = SENTIMENT[item.sentiment];
  return (
    <div className={`group relative rounded-lg border border-border/50 bg-surface2 p-3.5 transition-all duration-200 hover:border-border hover:bg-white/[0.03]`}>
      {/* Left accent bar */}
      <span className={`absolute left-0 top-3 bottom-3 w-[2px] rounded-full ${s.dot}`} />

      <div className="pl-3">
        {/* Top row: symbol + sentiment + time */}
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div className="flex items-center gap-1.5">
            <SymbolPill symbol={item.symbol} sentiment={item.sentiment} />
            <SentimentBadge sentiment={item.sentiment} />
          </div>
          <span className="text-[11px] tabular-nums text-muted">{timeAgo(item.published_at)}</span>
        </div>

        {/* Headline */}
        <p className="mt-2 text-[13px] font-medium leading-snug text-white">
          {item.headline}
        </p>

        {/* AI Summary */}
        <div className="mt-2 flex items-start gap-1.5">
          <span className="mt-[1px] shrink-0 text-[9px] font-bold uppercase tracking-widest text-accent">AI</span>
          <p className="text-[11px] leading-relaxed text-muted">{item.summary}</p>
        </div>
      </div>
    </div>
  );
}

// ── Main widget ───────────────────────────────────────────────────────────────

const REFRESH_INTERVAL_MS = 60_000;

interface NewsWidgetProps {
  selectedAsset?: string;
}

export default function NewsWidget({ selectedAsset }: NewsWidgetProps) {
  const [items,      setItems]      = useState<NewsItem[]>(MOCK_NEWS);
  const [loading,    setLoading]    = useState(false);
  const [spinning,   setSpinning]   = useState(false);
  const [filterInput, setFilterInput] = useState("");
  const [activeFilter, setActiveFilter] = useState("");
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Fetch (falls back to mock data on error)
  const fetchNews = useCallback(async (symbol?: string) => {
    setLoading(true);
    setSpinning(true);
    try {
      const data = await getNews(symbol || undefined);
      setItems(data);
      setLastUpdated(new Date());
    } catch {
      // Backend offline — filter mock data client-side
      const filtered = symbol
        ? MOCK_NEWS.filter((n) => n.symbol === symbol.toUpperCase())
        : MOCK_NEWS;
      setItems(filtered);
    } finally {
      setLoading(false);
      // Keep spinner for at least 600ms for UX feel
      setTimeout(() => setSpinning(false), 600);
    }
  }, []);

  // Sync filter with the globally selected asset (from AssetSelectorBar)
  useEffect(() => {
    if (selectedAsset) {
      setFilterInput(selectedAsset);
      setActiveFilter(selectedAsset);
      fetchNews(selectedAsset);
    } else {
      setFilterInput("");
      setActiveFilter("");
      fetchNews(undefined);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedAsset]);

  // Debounced filter: fires 600ms after user stops typing
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      const val = filterInput.trim().toUpperCase();
      setActiveFilter(val);
      fetchNews(val || undefined);
    }, 600);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [filterInput, fetchNews]);

  // Auto-refresh every 60s
  useEffect(() => {
    const id = setInterval(() => fetchNews(activeFilter || undefined), REFRESH_INTERVAL_MS);
    return () => clearInterval(id);
  }, [activeFilter, fetchNews]);

  const clearFilter = () => {
    setFilterInput("");
    setActiveFilter("");
    fetchNews(undefined);
  };

  const bullishCount = items.filter((n) => n.sentiment === "bullish").length;
  const bearishCount = items.filter((n) => n.sentiment === "bearish").length;

  return (
    <div className="flex flex-col rounded-xl border border-border bg-surface">

      {/* ── Header ── */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <Newspaper className="h-4 w-4 text-accent" />
          <h2 className="text-sm font-semibold text-white">AI News Feed</h2>
          {activeFilter ? (
            <span className="rounded bg-accent/15 px-1.5 py-0.5 text-[10px] font-bold text-accent">
              {activeFilter}
            </span>
          ) : (
            <span className="rounded bg-surface2 px-1.5 py-0.5 text-[10px] font-medium text-muted">
              GLOBAL
            </span>
          )}

          {/* Sentiment summary pills */}
          <div className="hidden items-center gap-1.5 sm:flex">
            <span className="flex items-center gap-1 text-[11px] text-positive">
              <TrendingUp className="h-3 w-3" />{bullishCount}
            </span>
            <span className="text-border">/</span>
            <span className="flex items-center gap-1 text-[11px] text-negative">
              <TrendingDown className="h-3 w-3" />{bearishCount}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="hidden text-[10px] text-muted sm:block">
            Updated {timeAgo(lastUpdated.toISOString())}
          </span>
          <button
            onClick={() => fetchNews(activeFilter || undefined)}
            className="flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-[11px] text-muted transition-colors hover:border-muted/40 hover:text-white"
          >
            <RefreshCw className={`h-3 w-3 ${spinning ? "animate-spin" : ""}`} />
            <span className="hidden sm:block">Refresh</span>
          </button>
        </div>
      </div>

      {/* ── Search / Filter ── */}
      <div className="border-b border-border px-4 py-3">
        <div className="relative flex items-center">
          <Search className="absolute left-3 h-3.5 w-3.5 text-muted" />
          <input
            value={filterInput}
            onChange={(e) => setFilterInput(e.target.value)}
            placeholder="Filter by asset (e.g. BTC, NVDA)..."
            className="w-full rounded-lg border border-border bg-surface2 py-2 pl-9 pr-9 text-xs outline-none placeholder:text-muted/50 transition-colors focus:border-accent focus:bg-surface"
          />
          {filterInput && (
            <button onClick={clearFilter} className="absolute right-3 text-muted hover:text-white transition-colors">
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
        {activeFilter && (
          <p className="mt-1.5 text-[11px] text-muted">
            Showing news for <span className="font-semibold text-white">{activeFilter}</span>
            {" · "}
            <button onClick={clearFilter} className="text-accent hover:underline">Show all markets</button>
          </p>
        )}
      </div>

      {/* ── News Feed ── */}
      <div className="scrollbar-thin h-[420px] space-y-2 overflow-y-auto p-3">
        {loading && items.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <div className="flex flex-col items-center gap-2">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-border border-t-accent" />
              <p className="text-xs text-muted">Fetching market intelligence…</p>
            </div>
          </div>
        ) : items.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-muted">
            <Newspaper className="h-8 w-8 opacity-30" />
            <p className="text-sm">No news found{activeFilter ? ` for ${activeFilter}` : ""}.</p>
          </div>
        ) : (
          items.map((item) => (
            <div key={item.id} className="animate-slide-up">
              <NewsCard item={item} />
            </div>
          ))
        )}
      </div>

      {/* ── Footer ── */}
      <div className="flex items-center justify-between border-t border-border px-4 py-2">
        <p className="text-[10px] text-muted">
          {items.length} article{items.length !== 1 ? "s" : ""} · AI sentiment analysis
        </p>
        <span className="flex items-center gap-1 text-[10px] text-muted">
          <span className="relative flex h-1.5 w-1.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-positive opacity-60" />
            <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-positive" />
          </span>
          Auto-refresh 60s
        </span>
      </div>
    </div>
  );
}
