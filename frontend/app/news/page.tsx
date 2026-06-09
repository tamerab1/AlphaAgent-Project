"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import {
  ArrowLeft, Newspaper, TrendingUp, TrendingDown, Minus,
  RefreshCw, Search, X, ChevronDown, ChevronUp, ExternalLink,
} from "lucide-react";
import { useSession } from "@/components/AuthGate";
import { supabase } from "@/lib/supabase";
import TopNav from "@/components/TopNav";
import { setAuthToken, getNews, type NewsItem } from "@/lib/api";
import { MOCK_NEWS } from "@/lib/mockData";

// ── Types & constants ─────────────────────────────────────────────────────────

type Sentiment = "bullish" | "bearish" | "neutral";
type SentimentFilter = "all" | Sentiment;

const REFRESH_MS = 60_000;

const SENTIMENT = {
  bullish: {
    dot:   "bg-positive",
    label: "Bullish",
    badge: "border-positive/40 bg-positive/10 text-positive",
    bar:   "bg-positive",
    pill:  "border-positive/30 bg-positive/5 text-positive",
    icon:  TrendingUp,
    breakdown_label: "Why Bullish",
    breakdown_bar: "border-l-positive/40",
  },
  bearish: {
    dot:   "bg-negative",
    label: "Bearish",
    badge: "border-negative/40 bg-negative/10 text-negative",
    bar:   "bg-negative",
    pill:  "border-negative/30 bg-negative/5 text-negative",
    icon:  TrendingDown,
    breakdown_label: "Why Bearish",
    breakdown_bar: "border-l-negative/40",
  },
  neutral: {
    dot:   "bg-muted",
    label: "Neutral",
    badge: "border-border bg-surface2 text-muted",
    bar:   "bg-muted",
    pill:  "border-border bg-surface2 text-muted",
    icon:  Minus,
    breakdown_label: "Market Impact",
    breakdown_bar: "border-l-border",
  },
} as const;

// ── Helpers ───────────────────────────────────────────────────────────────────

function timeAgo(iso: string): string {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60)    return `${diff}s ago`;
  if (diff < 3600)  return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SkeletonCard() {
  return (
    <div className="relative rounded-xl border border-border/50 bg-surface p-4">
      <span className="absolute left-0 top-4 bottom-4 w-[3px] rounded-full bg-surface2" />
      <div className="space-y-2.5 pl-4">
        <div className="flex items-center gap-2">
          <div className="h-4 w-12 animate-pulse rounded-full bg-surface2" />
          <div className="h-4 w-20 animate-pulse rounded-full bg-surface2" />
          <div className="ml-auto h-3 w-14 animate-pulse rounded bg-surface2" />
        </div>
        <div className="h-4 w-full animate-pulse rounded bg-surface2" />
        <div className="h-4 w-4/5 animate-pulse rounded bg-surface2" />
        <div className="h-3 w-3/5 animate-pulse rounded bg-surface2 opacity-60" />
      </div>
    </div>
  );
}

function NewsCard({ item }: { item: NewsItem }) {
  const [expanded, setExpanded] = useState(false);
  const s = SENTIMENT[item.sentiment];
  const Icon = s.icon;

  return (
    <article className="group relative rounded-xl border border-border/50 bg-surface transition-all duration-200 hover:border-border hover:bg-white/[0.025]">
      {/* Left sentiment bar */}
      <span className={`absolute left-0 top-3 bottom-3 w-[3px] rounded-full ${s.bar}`} />

      {/* ── Clickable header (always visible) ── */}
      <button
        className="w-full cursor-pointer px-4 pb-3 pt-4 pl-7 text-left"
        onClick={() => setExpanded((e) => !e)}
        aria-expanded={expanded}
      >
        {/* Meta row */}
        <div className="flex items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className={`rounded border px-2 py-0.5 text-[10px] font-bold ${s.pill}`}>
              {item.symbol}
            </span>
            <span className={`flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-bold tracking-wider ${s.badge}`}>
              <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
              {s.label.toUpperCase()}
            </span>
            <span className="rounded bg-surface2 px-1.5 py-0.5 text-[10px] text-muted">
              {item.source}
            </span>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            <span className="tabular-nums text-[11px] text-muted">
              {timeAgo(item.published_at)}
            </span>
            <span className="text-muted transition-transform duration-200">
              {expanded
                ? <ChevronUp className="h-3.5 w-3.5" />
                : <ChevronDown className="h-3.5 w-3.5 opacity-50 group-hover:opacity-100" />}
            </span>
          </div>
        </div>

        {/* Headline */}
        <p className="mt-2.5 text-sm font-semibold leading-snug text-white">
          {item.headline}
        </p>

        {/* Collapsed preview — truncated summary */}
        {!expanded && (
          <p className="mt-1.5 flex items-center gap-1 truncate text-[11px] text-muted/70">
            <Icon className="h-3 w-3 shrink-0 opacity-70" />
            {item.summary}
          </p>
        )}
      </button>

      {/* ── Expanded panel ── */}
      {expanded && (
        <div className="mx-4 mb-4 ml-7 space-y-3 rounded-xl border border-border bg-surface2 p-4">

          {/* AI Summary */}
          <div className="flex items-start gap-2.5">
            <span className="mt-[3px] shrink-0 rounded bg-accent/15 px-1 py-0.5 text-[9px] font-bold uppercase tracking-widest text-accent">
              AI
            </span>
            <p className="text-xs leading-relaxed text-white/90">{item.summary}</p>
          </div>

          {/* Sentiment Breakdown */}
          {item.sentiment_breakdown && (
            <div className={`border-l-2 pl-3 ${s.breakdown_bar}`}>
              <p className={`mb-1 text-[10px] font-bold uppercase tracking-wider ${
                item.sentiment === "bullish" ? "text-positive"
                : item.sentiment === "bearish" ? "text-negative"
                : "text-muted"
              }`}>
                {s.breakdown_label}
              </p>
              <p className="text-xs leading-relaxed text-muted">
                {item.sentiment_breakdown}
              </p>
            </div>
          )}

          {/* Read Original Source */}
          {item.url && (
            <div className="border-t border-border/60 pt-3">
              <a
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-semibold transition-all duration-200 hover:opacity-80 ${
                  item.sentiment === "bullish"
                    ? "border-positive/30 bg-positive/5 text-positive hover:bg-positive/10"
                    : item.sentiment === "bearish"
                    ? "border-negative/30 bg-negative/5 text-negative hover:bg-negative/10"
                    : "border-border bg-surface text-muted hover:bg-white/5 hover:text-white"
                }`}
              >
                <ExternalLink className="h-3 w-3" />
                Read Original Source
              </a>
            </div>
          )}
        </div>
      )}
    </article>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function NewsPage() {
  const session = useSession();

  useEffect(() => {
    setAuthToken(session?.access_token ?? null);
  }, [session?.access_token]);

  const [items,           setItems]           = useState<NewsItem[]>(MOCK_NEWS);
  const [loading,         setLoading]         = useState(false);
  const [spinning,        setSpinning]        = useState(false);
  const [sentimentFilter, setSentimentFilter] = useState<SentimentFilter>("all");
  const [symbolInput,     setSymbolInput]     = useState("");
  const [activeSymbol,    setActiveSymbol]    = useState("");
  const [lastUpdated,     setLastUpdated]     = useState(new Date());
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchNews = useCallback(async (symbol?: string) => {
    setLoading(true);
    setSpinning(true);
    try {
      const data = await getNews(symbol || undefined);
      setItems(data);
      setLastUpdated(new Date());
    } catch {
      const filtered = symbol
        ? MOCK_NEWS.filter((n) => n.symbol === symbol.toUpperCase())
        : MOCK_NEWS;
      setItems(filtered);
    } finally {
      setLoading(false);
      setTimeout(() => setSpinning(false), 600);
    }
  }, []);

  // Initial load
  useEffect(() => {
    fetchNews(undefined);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Debounce symbol filter (600 ms)
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      const val = symbolInput.trim().toUpperCase();
      setActiveSymbol(val);
      fetchNews(val || undefined);
    }, 600);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [symbolInput, fetchNews]);

  // Auto-refresh every 60 s
  useEffect(() => {
    const id = setInterval(() => fetchNews(activeSymbol || undefined), REFRESH_MS);
    return () => clearInterval(id);
  }, [activeSymbol, fetchNews]);

  const clearFilters = () => {
    setSentimentFilter("all");
    setSymbolInput("");
    setActiveSymbol("");
    fetchNews(undefined);
  };

  const displayItems = items.filter(
    (item) => sentimentFilter === "all" || item.sentiment === sentimentFilter,
  );

  const bullishCount = items.filter((n) => n.sentiment === "bullish").length;
  const bearishCount = items.filter((n) => n.sentiment === "bearish").length;
  const neutralCount = items.filter((n) => n.sentiment === "neutral").length;

  return (
    <div className="min-h-screen bg-bg text-white">
      <TopNav
        mode="paper"
        onModeChange={() => {}}
        apiConnected
        portfolioUser={session?.user?.email ?? "Demo"}
        onSignOut={() => supabase.auth.signOut()}
      />

      <main className="mx-auto max-w-[900px] px-4 py-6 lg:px-6">

        {/* ── Breadcrumb ── */}
        <div className="mb-4 flex items-center gap-2">
          <Link
            href="/"
            className="flex items-center gap-1.5 text-xs text-muted transition-colors hover:text-white"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Dashboard
          </Link>
          <span className="text-border">/</span>
          <span className="text-xs font-medium text-white">Market Intelligence</span>
        </div>

        {/* ── Page header ── */}
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <Newspaper className="h-5 w-5 text-accent" />
              <h1 className="text-lg font-bold text-white">
                Market Intelligence Terminal
              </h1>
              <span className="hidden rounded bg-accent/15 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-widest text-accent sm:block">
                AI-POWERED
              </span>
            </div>
            <p className="mt-1 text-xs text-muted">
              Real-time news analysis · click any card to expand AI summary &amp; sentiment breakdown
            </p>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            <span className="hidden tabular-nums text-[11px] text-muted sm:block">
              {timeAgo(lastUpdated.toISOString())}
            </span>
            <button
              onClick={() => fetchNews(activeSymbol || undefined)}
              className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs text-muted transition-colors hover:border-muted/40 hover:text-white"
            >
              <RefreshCw className={`h-3 w-3 ${spinning ? "animate-spin" : ""}`} />
              Refresh
            </button>
          </div>
        </div>

        {/* ── Stats bar ── */}
        <div className="mb-4 flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl border border-border bg-surface px-4 py-3">
          <div className="flex items-center gap-1.5 text-xs">
            <TrendingUp className="h-3.5 w-3.5 text-positive" />
            <span className="font-bold text-positive">{bullishCount}</span>
            <span className="text-muted">Bullish</span>
          </div>
          <div className="h-3 w-px bg-border" />
          <div className="flex items-center gap-1.5 text-xs">
            <TrendingDown className="h-3.5 w-3.5 text-negative" />
            <span className="font-bold text-negative">{bearishCount}</span>
            <span className="text-muted">Bearish</span>
          </div>
          <div className="h-3 w-px bg-border" />
          <div className="flex items-center gap-1.5 text-xs">
            <Minus className="h-3.5 w-3.5 text-muted" />
            <span className="font-bold text-muted">{neutralCount}</span>
            <span className="text-muted">Neutral</span>
          </div>
          <div className="h-3 w-px bg-border" />
          <span className="text-xs text-muted">{items.length} articles</span>

          <div className="ml-auto flex items-center gap-1 text-[10px] text-muted">
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-positive opacity-60" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-positive" />
            </span>
            Auto-refresh 60s
          </div>
        </div>

        {/* ── Filter bar ── */}
        <div className="mb-4 flex flex-wrap items-center gap-2">
          {/* Sentiment pills */}
          {(["all", "bullish", "bearish", "neutral"] as const).map((s) => {
            const isActive = sentimentFilter === s;
            const cfg = s !== "all" ? SENTIMENT[s] : null;
            return (
              <button
                key={s}
                onClick={() => setSentimentFilter(s)}
                className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                  isActive
                    ? s === "all"
                      ? "border-white/20 bg-white/10 text-white"
                      : cfg!.pill
                    : "border-border bg-surface2 text-muted hover:border-muted/40 hover:text-white"
                }`}
              >
                {cfg && <span className={`h-1.5 w-1.5 rounded-full ${cfg.dot}`} />}
                {s === "all" ? "All Markets" : cfg!.label}
              </button>
            );
          })}

          {/* Symbol search */}
          <div className="relative ml-auto flex items-center">
            <Search className="absolute left-2.5 h-3.5 w-3.5 text-muted" />
            <input
              value={symbolInput}
              onChange={(e) => setSymbolInput(e.target.value)}
              placeholder="Filter by asset…"
              className="w-44 rounded-lg border border-border bg-surface2 py-1.5 pl-8 pr-7 text-xs outline-none placeholder:text-muted/50 focus:border-accent"
            />
            {symbolInput && (
              <button
                onClick={clearFilters}
                className="absolute right-2.5 text-muted hover:text-white"
              >
                <X className="h-3 w-3" />
              </button>
            )}
          </div>
        </div>

        {/* Active symbol label */}
        {activeSymbol && (
          <p className="mb-3 text-[11px] text-muted">
            Showing news for{" "}
            <span className="font-semibold text-white">{activeSymbol}</span>
            {" · "}
            <button onClick={clearFilters} className="text-accent hover:underline">
              Show all markets
            </button>
          </p>
        )}

        {/* ── News feed ── */}
        <div className="space-y-2">
          {loading && items.length === 0 ? (
            Array.from({ length: 5 }).map((_, i) => <SkeletonCard key={i} />)
          ) : displayItems.length === 0 ? (
            <div className="flex h-48 flex-col items-center justify-center gap-2 text-muted">
              <Newspaper className="h-8 w-8 opacity-30" />
              <p className="text-sm">
                No news found
                {sentimentFilter !== "all" ? ` for ${sentimentFilter} sentiment` : ""}
                {activeSymbol ? ` on ${activeSymbol}` : ""}.
              </p>
              <button
                onClick={clearFilters}
                className="mt-1 text-xs text-accent hover:underline"
              >
                Clear all filters
              </button>
            </div>
          ) : (
            displayItems.map((item) => (
              <div key={item.id} className="animate-slide-up">
                <NewsCard item={item} />
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        {displayItems.length > 0 && (
          <p className="mt-6 text-center text-[11px] text-muted">
            {displayItems.length} article{displayItems.length !== 1 ? "s" : ""} ·
            AI sentiment analysis · <span className="text-accent">AlphaAgent Intelligence</span>
          </p>
        )}
      </main>
    </div>
  );
}
