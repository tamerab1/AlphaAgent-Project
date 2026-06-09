"use client";

import { useState, useRef, useEffect, useMemo, useCallback } from "react";
import type { CSSProperties } from "react";
import { Search, X, TrendingUp, TrendingDown } from "lucide-react";
import { getQuotes, getAssetDetail } from "@/lib/api";
import {
  ASSETS,
  CRYPTO_ASSETS,
  STOCK_ASSETS,
  type AssetInfo,
  type AssetType,
} from "@/lib/mockAssets";
import { toAssetInfo, cacheDynamicAsset, getDynamicAssets } from "@/lib/assetUtils";

// ── Helpers ───────────────────────────────────────────────────────────────────

function miniPrice(p: number): string {
  if (p >= 1000) return `$${(p / 1000).toFixed(1)}K`;
  if (p >= 1)    return `$${p.toFixed(2)}`;
  return `$${p.toFixed(4)}`;
}

// ── Ticker chip with price-change glow ───────────────────────────────────────

function AssetChip({
  asset,
  active,
  onClick,
}: {
  asset: AssetInfo;
  active: boolean;
  onClick: () => void;
}) {
  const prevRef = useRef(0);
  const [flash, setFlash] = useState<"up" | "down" | null>(null);

  useEffect(() => {
    const prev = prevRef.current;
    if (prev === 0) { prevRef.current = asset.price; return; }
    if (asset.price === prev) return;
    const dir = asset.price > prev ? "up" : "down";
    prevRef.current = asset.price;
    setFlash(dir);
    const t = setTimeout(() => setFlash(null), 1500);
    return () => clearTimeout(t);
  }, [asset.price]);

  const pos = asset.change24h >= 0;

  const glowStyle: CSSProperties = {
    boxShadow: flash === "up"
      ? "0 0 12px rgba(14, 203, 129, 0.5)"
      : flash === "down"
      ? "0 0 12px rgba(246, 70, 93, 0.5)"
      : undefined,
    transition: "box-shadow 1.5s ease-out",
  };

  const priceClass = flash === "up"
    ? "text-positive"
    : flash === "down"
    ? "text-negative"
    : pos ? "text-positive" : "text-negative";

  return (
    <button
      onClick={onClick}
      style={glowStyle}
      className={`flex shrink-0 items-center gap-2 rounded-lg border px-3 py-1.5 text-xs transition-all duration-200 ${
        active
          ? "border-accent/60 bg-accent/10 text-white"
          : "border-border bg-surface2 text-muted hover:border-border/80 hover:text-white"
      }`}
    >
      <span className="font-bold text-white">{asset.symbol}</span>
      <span className={`font-medium tabular-nums transition-colors duration-300 ${priceClass}`}>
        {miniPrice(asset.price)}
      </span>
      <span className={`flex items-center gap-0.5 text-[10px] font-semibold ${pos ? "text-positive" : "text-negative"}`}>
        {pos ? <TrendingUp className="h-2.5 w-2.5" /> : <TrendingDown className="h-2.5 w-2.5" />}
        {pos ? "+" : ""}{asset.change24h.toFixed(1)}%
      </span>
    </button>
  );
}

// ── Search result row ─────────────────────────────────────────────────────────

function SearchResult({
  asset,
  onSelect,
}: {
  asset: AssetInfo;
  onSelect: (a: AssetInfo) => void;
}) {
  const pos = asset.change24h >= 0;
  return (
    <button
      onMouseDown={(e) => { e.preventDefault(); onSelect(asset); }}
      className="flex w-full items-center justify-between px-3.5 py-2.5 text-xs transition-colors hover:bg-white/5"
    >
      <div className="flex items-center gap-2">
        <span className={`rounded px-1.5 py-0.5 text-[9px] font-bold ${
          asset.type === "crypto" ? "bg-accent/15 text-accent" : "bg-muted/15 text-muted"
        }`}>
          {asset.type === "crypto" ? "CRYPTO" : "STOCK"}
        </span>
        <span className="font-semibold text-white">{asset.symbol}</span>
        <span className="text-muted">{asset.name}</span>
      </div>
      <div className="flex items-center gap-2 tabular-nums">
        <span className="text-white">{miniPrice(asset.price)}</span>
        <span className={`font-medium ${pos ? "text-positive" : "text-negative"}`}>
          {pos ? "+" : ""}{asset.change24h.toFixed(2)}%
        </span>
      </div>
    </button>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface AssetSelectorBarProps {
  selectedAsset: string;
  assetType:     AssetType;
  onAssetChange: (symbol: string) => void;
  onTypeChange:  (type: AssetType) => void;
}

export default function AssetSelectorBar({
  selectedAsset,
  assetType,
  onAssetChange,
  onTypeChange,
}: AssetSelectorBarProps) {
  const [query,         setQuery]         = useState("");
  const [open,          setOpen]          = useState(false);
  const [liveSearching, setLiveSearching] = useState(false);
  const [liveError,     setLiveError]     = useState("");
  const [liveQuotes, setLiveQuotes] = useState<
    Record<string, { price: number; change24h: number }>
  >({});
  const searchRef = useRef<HTMLDivElement>(null);

  const visibleAssets = assetType === "crypto" ? CRYPTO_ASSETS : STOCK_ASSETS;

  // Fetch live prices for the visible tickers. Re-runs every 30s.
  const fetchQuotes = useCallback(async () => {
    const symbols = (assetType === "crypto" ? CRYPTO_ASSETS : STOCK_ASSETS)
      .map((a) => a.symbol);
    try {
      const quotes = await getQuotes(symbols);
      const map: Record<string, { price: number; change24h: number }> = {};
      for (const q of quotes) {
        map[q.symbol] = { price: q.price, change24h: q.change_24h };
      }
      setLiveQuotes(map);
    } catch {
      /* keep mock prices */
    }
  }, [assetType]);

  useEffect(() => {
    fetchQuotes();
    const id = setInterval(fetchQuotes, 30_000);
    return () => clearInterval(id);
  }, [fetchQuotes]);

  // Filter static + session-cached dynamic assets by the search query.
  const results = useMemo(() => {
    if (!query.trim()) return [];
    const q = query.trim().toUpperCase();
    return [...ASSETS, ...getDynamicAssets()]
      .filter((a) => a.symbol.includes(q) || a.name.toUpperCase().includes(q))
      .slice(0, 7);
  }, [query]);

  // Show live-market search when the typed symbol has no exact local match.
  const showLiveSearch = useMemo(() => {
    const q = query.trim().toUpperCase();
    if (!q) return false;
    return ![...ASSETS, ...getDynamicAssets()].some((a) => a.symbol === q);
  }, [query]);

  // Close on outside click.
  useEffect(() => {
    function onDown(e: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, []);

  function selectAsset(a: AssetInfo) {
    onAssetChange(a.symbol);
    onTypeChange(a.type);
    setQuery("");
    setOpen(false);
    setLiveError("");
  }

  async function handleLiveSearch() {
    const sym = query.trim().toUpperCase();
    if (!sym) return;
    setLiveSearching(true);
    setLiveError("");
    try {
      const detail = await getAssetDetail(sym);
      const info   = toAssetInfo(detail);
      cacheDynamicAsset(info);
      selectAsset(info);
    } catch {
      setLiveError(`"${sym}" not found — check the symbol and try again`);
    } finally {
      setLiveSearching(false);
    }
  }

  return (
    <div className="sticky top-14 z-40 border-b border-border bg-surface">
      <div className="mx-auto flex max-w-[1600px] items-center gap-3 px-4 py-2 lg:px-6">

        {/* ── Asset type tabs ── */}
        <div className="flex shrink-0 items-center gap-0.5 rounded-lg border border-border bg-bg p-0.5">
          {(["crypto", "stock"] as AssetType[]).map((t) => (
            <button
              key={t}
              onClick={() => {
                onTypeChange(t);
                const staticForType = t === "crypto" ? CRYPTO_ASSETS : STOCK_ASSETS;
                // Only auto-switch if the current asset isn't in the static list
                // or in the session-cached dynamic assets for this type.
                const dynForType = getDynamicAssets().filter((a) => a.type === t);
                const allForType = [...staticForType, ...dynForType];
                if (!allForType.some((a) => a.symbol === selectedAsset)) {
                  onAssetChange(staticForType[0].symbol);
                }
              }}
              className={`rounded-md px-3 py-1 text-xs font-semibold capitalize transition-all duration-200 ${
                assetType === t
                  ? "bg-accent text-bg shadow"
                  : "text-muted hover:text-white"
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        {/* ── Horizontal ticker scroll ── */}
        <div className="scrollbar-thin flex flex-1 items-center gap-1.5 overflow-x-auto py-0.5">
          {visibleAssets.map((a) => {
            const live = liveQuotes[a.symbol];
            const chip = live
              ? { ...a, price: live.price, change24h: live.change24h }
              : a;
            return (
              <AssetChip
                key={a.symbol}
                asset={chip}
                active={a.symbol === selectedAsset}
                onClick={() => onAssetChange(a.symbol)}
              />
            );
          })}
        </div>

        {/* ── Global search ── */}
        <div className="relative shrink-0 w-52" ref={searchRef}>
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted" />
          <input
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setOpen(true);
              setLiveError("");
            }}
            onFocus={() => setOpen(true)}
            placeholder="Search any ticker…"
            className="w-full rounded-lg border border-border bg-surface2 py-1.5 pl-8 pr-8 text-xs outline-none placeholder:text-muted/50 transition-colors focus:border-accent focus:bg-bg"
          />
          {query && (
            <button
              onClick={() => { setQuery(""); setOpen(false); setLiveError(""); }}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted hover:text-white"
            >
              <X className="h-3 w-3" />
            </button>
          )}

          {/* Dropdown */}
          {open && query.trim() && (
            <div className="animate-fade-in absolute right-0 top-full mt-1 w-80 rounded-xl border border-border bg-surface2 py-1.5 shadow-2xl">
              {results.length > 0 && (
                <>
                  <p className="px-3.5 pb-1.5 text-[10px] font-semibold uppercase tracking-widest text-muted">
                    Results
                  </p>
                  {results.map((a) => (
                    <SearchResult key={a.symbol} asset={a} onSelect={selectAsset} />
                  ))}
                </>
              )}

              {showLiveSearch && (
                <>
                  {results.length > 0 && (
                    <div className="mx-3.5 my-1 border-t border-border/50" />
                  )}
                  <button
                    onMouseDown={(e) => { e.preventDefault(); handleLiveSearch(); }}
                    disabled={liveSearching}
                    className="flex w-full items-center gap-2.5 px-3.5 py-2.5 text-[11px] text-muted transition-colors hover:bg-white/5 hover:text-white disabled:opacity-50"
                  >
                    {liveSearching ? (
                      <span className="h-3 w-3 animate-spin rounded-full border border-current border-t-transparent" />
                    ) : (
                      <Search className="h-3 w-3" />
                    )}
                    {liveSearching
                      ? "Searching market…"
                      : `Search live market for "${query.trim().toUpperCase()}"`
                    }
                  </button>
                  {liveError && (
                    <p className="px-3.5 pb-2 pt-1 text-[11px] text-negative">
                      {liveError}
                    </p>
                  )}
                </>
              )}

              {results.length === 0 && !showLiveSearch && (
                <p className="px-3.5 py-3 text-xs text-muted">
                  No results for &quot;{query}&quot;
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
