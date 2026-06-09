"use client";

import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import Link from "next/link";
import {
  ArrowLeft, TrendingUp, TrendingDown, Sparkles, User as UserIcon,
  RefreshCw, CheckCircle, AlertCircle, Search,
} from "lucide-react";
import { useSession } from "@/components/AuthGate";
import { supabase } from "@/lib/supabase";
import TopNav from "@/components/TopNav";
import {
  setAuthToken, getMyPortfolio, getMyTrades, executeTrade,
  getAssetDetail, toggleMode,
  type TradeOut, type TradingMode, type ManualTradeRequest,
} from "@/lib/api";
import { ASSETS, getAsset } from "@/lib/mockAssets";
import { toAssetInfo, cacheDynamicAsset, getCachedAsset, getDynamicAssets } from "@/lib/assetUtils";
import { MOCK_TRADES } from "@/lib/mockData";
import { formatCurrency, formatQty, formatTime } from "@/lib/format";

// ── Sub-components ────────────────────────────────────────────────────────────

function SideBadge({ side }: { side: string }) {
  return (
    <span className={`rounded px-2 py-0.5 text-[10px] font-bold ${
      side === "BUY"
        ? "bg-positive/15 text-positive"
        : "bg-negative/15 text-negative"
    }`}>
      {side}
    </span>
  );
}

function ByBadge({ rationale }: { rationale: string | null }) {
  const isManual = rationale === "Manual trade";
  return isManual ? (
    <span className="flex w-fit items-center gap-1 rounded border border-accent/30 bg-accent/10 px-1.5 py-0.5 text-[10px] font-bold text-accent">
      <UserIcon className="h-2.5 w-2.5" />
      User
    </span>
  ) : (
    <span className="flex w-fit items-center gap-1 rounded border border-border bg-surface2 px-1.5 py-0.5 text-[10px] font-bold text-muted">
      <Sparkles className="h-2.5 w-2.5" />
      AI
    </span>
  );
}

function TableSkeleton() {
  return (
    <>
      {Array.from({ length: 5 }).map((_, i) => (
        <tr key={i} className="border-b border-border/40">
          {[24, 48, 44, 72, 72, 52, 80].map((w, j) => (
            <td key={j} className="px-3 py-2.5">
              <div
                className="h-3 animate-pulse rounded bg-surface2"
                style={{ width: `${w}%` }}
              />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

// ── Symbol combobox — accepts any ticker, falls back to live market search ────

function SymbolCombobox({
  value,
  onChange,
}: {
  value: string;
  onChange: (sym: string) => void;
}) {
  const [query,         setQuery]         = useState(value);
  const [open,          setOpen]          = useState(false);
  const [liveSearching, setLiveSearching] = useState(false);
  const [liveError,     setLiveError]     = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

  // Keep local query in sync when the parent resets the symbol (e.g. after a trade).
  useEffect(() => { setQuery(value); }, [value]);

  // All assets known this session (static list + anything fetched dynamically).
  const allAssets = useMemo(() => [...ASSETS, ...getDynamicAssets()], [open]);

  const q = query.trim().toUpperCase();

  const filtered = useMemo(() => {
    if (!q) return allAssets.slice(0, 12);
    return allAssets
      .filter((a) => a.symbol.startsWith(q) || a.name.toUpperCase().includes(q))
      .slice(0, 8);
  }, [q, allAssets]);

  const hasExactMatch = allAssets.some((a) => a.symbol === q);
  const showLiveSearch = q.length >= 1 && !hasExactMatch;

  // Close on outside click.
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
        // If the typed text isn't a known symbol, restore the last valid value.
        if (!allAssets.some((a) => a.symbol === q)) setQuery(value);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [q, value, allAssets]);

  function pick(sym: string) {
    onChange(sym);
    setQuery(sym);
    setOpen(false);
    setLiveError("");
  }

  async function doLiveSearch() {
    if (!q) return;
    setLiveSearching(true);
    setLiveError("");
    try {
      const detail = await getAssetDetail(q);
      const info   = toAssetInfo(detail);
      cacheDynamicAsset(info);
      pick(info.symbol);
    } catch {
      setLiveError(`"${q}" not found — check the symbol`);
    } finally {
      setLiveSearching(false);
    }
  }

  return (
    <div ref={containerRef} className="relative">
      <input
        type="text"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value.toUpperCase());
          setOpen(true);
          setLiveError("");
        }}
        onFocus={() => setOpen(true)}
        placeholder="BTC, ETH, DOGE, NVDA…"
        className="w-full rounded-lg border border-border bg-surface2 px-3 py-2.5 text-sm font-bold text-white outline-none placeholder:font-normal placeholder:text-muted/50 focus:border-accent"
      />

      {open && (
        <div className="absolute left-0 right-0 top-full z-50 mt-1 max-h-60 overflow-y-auto rounded-xl border border-border bg-surface2 py-1 shadow-2xl">
          {filtered.map((a) => (
            <button
              key={a.symbol}
              onMouseDown={(e) => { e.preventDefault(); pick(a.symbol); }}
              className="flex w-full items-center justify-between px-3.5 py-2 text-xs transition-colors hover:bg-white/5"
            >
              <span className="flex items-center gap-2">
                <span className={`rounded px-1.5 py-0.5 text-[9px] font-bold ${
                  a.type === "crypto" ? "bg-accent/15 text-accent" : "bg-muted/15 text-muted"
                }`}>
                  {a.type === "crypto" ? "CRYPTO" : "STOCK"}
                </span>
                <span className="font-bold text-white">{a.symbol}</span>
                <span className="text-muted">{a.name}</span>
              </span>
              <span className="tabular-nums text-muted">
                {a.price >= 1000
                  ? `$${(a.price / 1000).toFixed(1)}K`
                  : a.price >= 1
                  ? `$${a.price.toFixed(2)}`
                  : `$${a.price.toFixed(4)}`}
              </span>
            </button>
          ))}

          {showLiveSearch && (
            <>
              {filtered.length > 0 && (
                <div className="mx-3.5 my-1 border-t border-border/50" />
              )}
              <button
                onMouseDown={(e) => { e.preventDefault(); doLiveSearch(); }}
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
                  : `Search live market for "${q}"`}
              </button>
              {liveError && (
                <p className="px-3.5 pb-2 pt-0.5 text-[11px] text-negative">
                  {liveError}
                </p>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function TradesPage() {
  const session = useSession();

  // Sync auth token before any API call
  useEffect(() => {
    setAuthToken(session?.access_token ?? null);
  }, [session?.access_token]);

  // ── Portfolio ──
  const [portfolioId, setPortfolioId] = useState<number | null>(null);
  const [cashBalance, setCashBalance] = useState(0);
  const [mode,        setMode]        = useState<TradingMode>("paper");
  const [apiConnected, setApiConnected] = useState(false);

  // ── Trades ──
  const [trades,        setTrades]        = useState<TradeOut[]>([]);
  const [loadingTrades, setLoadingTrades] = useState(true);
  const [refreshing,    setRefreshing]    = useState(false);

  // ── Form ──
  const [side,         setSide]         = useState<"BUY" | "SELL">("BUY");
  const [symbol,       setSymbol]       = useState("BTC");
  const [usdAmount,    setUsdAmount]    = useState("");
  const [currentPrice, setCurrentPrice] = useState(0);
  const [loadingPrice, setLoadingPrice] = useState(false);
  const [executing,    setExecuting]    = useState(false);
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);

  const fallbackAsset = getAsset(symbol) ?? getCachedAsset(symbol);

  // Load portfolio + trades on session ready
  useEffect(() => {
    if (!session?.user?.id) return;
    let active = true;
    (async () => {
      try {
        const portfolio = await getMyPortfolio();
        if (!active) return;
        setPortfolioId(portfolio.id);
        setCashBalance(portfolio.cash_balance);
        setApiConnected(true);
        const t = await getMyTrades();
        if (active) setTrades(t);
      } catch {
        if (active) {
          setTrades(MOCK_TRADES);
          setApiConnected(false);
        }
      } finally {
        if (active) setLoadingTrades(false);
      }
    })();
    return () => { active = false; };
  }, [session?.user?.id]);

  // Fetch live price when asset changes
  useEffect(() => {
    let active = true;
    setLoadingPrice(true);
    (async () => {
      try {
        const detail = await getAssetDetail(symbol);
        if (active) setCurrentPrice(detail.price);
      } catch {
        if (active) setCurrentPrice(fallbackAsset?.price ?? 0);
      } finally {
        if (active) setLoadingPrice(false);
      }
    })();
    return () => { active = false; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol]);

  const usdNum = parseFloat(usdAmount) || 0;
  const qty    = currentPrice > 0 ? usdNum / currentPrice : 0;

  const refreshTrades = useCallback(async () => {
    setRefreshing(true);
    try {
      const t = await getMyTrades();
      setTrades(t);
    } catch { /* offline */ }
    finally { setRefreshing(false); }
  }, []);

  const handleModeChange = async (newMode: TradingMode) => {
    setMode(newMode);
    if (portfolioId) {
      try { await toggleMode(portfolioId, newMode); } catch { /* offline */ }
    }
  };

  const handleExecute = async () => {
    if (!usdNum || usdNum <= 0) {
      setResult({ ok: false, message: "Enter a valid USD amount." });
      return;
    }
    setExecuting(true);
    setResult(null);
    try {
      const req: ManualTradeRequest = { symbol, side, usd_amount: usdNum };
      await executeTrade(req);
      setResult({
        ok: true,
        message: `${side} order filled: ${formatQty(qty)} ${symbol} @ ${formatCurrency(currentPrice)}`,
      });
      setUsdAmount("");
      // Refresh cash balance
      try {
        const p = await getMyPortfolio();
        setCashBalance(p.cash_balance);
      } catch { /* ignore */ }
      await refreshTrades();
    } catch (err: unknown) {
      const raw = err instanceof Error ? err.message : "Trade failed.";
      // Strip HTTP prefix from backend error detail
      const match = raw.match(/\d{3} [^:]+: (.+)$/);
      setResult({ ok: false, message: match ? match[1] : raw });
    } finally {
      setExecuting(false);
    }
  };

  return (
    <div className="min-h-screen bg-bg text-white">
      <TopNav
        mode={mode}
        onModeChange={handleModeChange}
        apiConnected={apiConnected}
        portfolioUser={session?.user?.email ?? "Demo"}
        onSignOut={() => supabase.auth.signOut()}
      />

      <main className="mx-auto max-w-[1600px] px-4 py-6 lg:px-6">

        {/* ── Breadcrumb ── */}
        <div className="mb-6 flex items-center gap-2">
          <Link
            href="/"
            className="flex items-center gap-1.5 text-xs text-muted transition-colors hover:text-white"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Dashboard
          </Link>
          <span className="text-border">/</span>
          <span className="text-xs font-medium text-white">Trading Center</span>
        </div>

        <div className="grid gap-4 lg:grid-cols-[420px_1fr]">

          {/* ── Left: Trade Form ── */}
          <div className="h-fit rounded-xl border border-border bg-surface">
            <div className="border-b border-border px-5 py-4">
              <h2 className="text-sm font-semibold text-white">Manual Paper Trade</h2>
              <p className="mt-0.5 text-[11px] text-muted">
                Execute at live market price · paper mode
              </p>
            </div>

            <div className="space-y-4 p-5">
              {/* BUY / SELL tabs */}
              <div className="flex rounded-lg border border-border bg-bg p-0.5">
                <button
                  onClick={() => { setSide("BUY"); setResult(null); }}
                  className={`flex-1 rounded-md py-2.5 text-sm font-bold transition-all duration-200 ${
                    side === "BUY"
                      ? "bg-positive text-bg shadow-[0_0_16px_rgba(14,203,129,0.3)]"
                      : "text-muted hover:text-white"
                  }`}
                >
                  BUY
                </button>
                <button
                  onClick={() => { setSide("SELL"); setResult(null); }}
                  className={`flex-1 rounded-md py-2.5 text-sm font-bold transition-all duration-200 ${
                    side === "SELL"
                      ? "bg-negative text-white shadow-[0_0_16px_rgba(246,70,93,0.3)]"
                      : "text-muted hover:text-white"
                  }`}
                >
                  SELL
                </button>
              </div>

              {/* Asset selector — accepts any symbol */}
              <div>
                <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-widest text-muted">
                  Asset
                </label>
                <SymbolCombobox
                  value={symbol}
                  onChange={(sym) => { setSymbol(sym); setResult(null); }}
                />

                <div className="mt-2 flex items-center justify-between">
                  <span className="text-[11px] text-muted">Live price</span>
                  {loadingPrice ? (
                    <div className="h-3 w-24 animate-pulse rounded bg-surface2" />
                  ) : (
                    <span className="font-bold tabular-nums text-white">
                      {currentPrice > 0 ? formatCurrency(currentPrice) : "—"}
                    </span>
                  )}
                </div>
              </div>

              {/* USD amount input */}
              <div>
                <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-widest text-muted">
                  Amount (USD)
                </label>
                <div className="relative flex items-center">
                  <span className="absolute left-3 text-sm font-medium text-muted">$</span>
                  <input
                    type="number"
                    min="0"
                    step="100"
                    value={usdAmount}
                    onChange={(e) => { setUsdAmount(e.target.value); setResult(null); }}
                    placeholder="0.00"
                    className="w-full rounded-lg border border-border bg-surface2 py-2.5 pl-7 pr-3 text-sm text-white outline-none placeholder:text-muted/50 focus:border-accent"
                  />
                </div>
                <div className="mt-1.5 flex items-center justify-between">
                  <span className="text-[11px] text-muted">Available cash</span>
                  <span className="text-[11px] tabular-nums text-white">
                    {formatCurrency(cashBalance)}
                  </span>
                </div>
              </div>

              {/* Quantity preview */}
              {usdNum > 0 && currentPrice > 0 && (
                <div className={`rounded-lg border p-3 ${
                  side === "BUY"
                    ? "border-positive/20 bg-positive/5"
                    : "border-negative/20 bg-negative/5"
                }`}>
                  <p className="text-[11px] text-muted">
                    You will {side === "BUY" ? "receive" : "sell"}
                  </p>
                  <p className="mt-0.5 tabular-nums">
                    <span className="text-lg font-bold text-white">{formatQty(qty)}</span>
                    {" "}
                    <span className="text-sm font-medium text-muted">{symbol}</span>
                  </p>
                  <p className="text-[11px] text-muted">
                    ≈ {formatCurrency(usdNum)} at market price
                  </p>
                </div>
              )}

              {/* Execute button */}
              <button
                onClick={handleExecute}
                disabled={executing || loadingPrice || !usdNum}
                className={`w-full rounded-lg py-3 text-sm font-bold transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-40 ${
                  side === "BUY"
                    ? "bg-positive text-bg hover:bg-positive/90 shadow-[0_0_20px_rgba(14,203,129,0.2)]"
                    : "bg-negative text-white hover:bg-negative/90 shadow-[0_0_20px_rgba(246,70,93,0.2)]"
                }`}
              >
                {executing ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
                    Executing…
                  </span>
                ) : (
                  `${side} ${symbol}`
                )}
              </button>

              {/* Inline result message */}
              {result && (
                <div className={`flex items-start gap-2 rounded-lg border p-3 text-xs ${
                  result.ok
                    ? "border-positive/20 bg-positive/5 text-positive"
                    : "border-negative/20 bg-negative/5 text-negative"
                }`}>
                  {result.ok
                    ? <CheckCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                    : <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />}
                  <span className="leading-relaxed">{result.message}</span>
                </div>
              )}
            </div>
          </div>

          {/* ── Right: Trade History ── */}
          <div className="rounded-xl border border-border bg-surface">
            <div className="flex items-center justify-between border-b border-border px-4 py-3">
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-semibold text-white">Trade History</h2>
                <span className="rounded bg-surface2 px-1.5 py-0.5 text-[10px] font-medium text-muted">
                  {trades.length} TRADES
                </span>
              </div>
              <button
                onClick={refreshTrades}
                className="flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-[11px] text-muted transition-colors hover:border-muted/40 hover:text-white"
              >
                <RefreshCw className={`h-3 w-3 ${refreshing ? "animate-spin" : ""}`} />
                Refresh
              </button>
            </div>

            {loadingTrades ? (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-border text-left">
                      {["#", "Asset", "Side", "Price", "Amount", "By", "Time"].map((h) => (
                        <th key={h} className={`px-3 py-2.5 font-medium text-muted ${["Price", "Amount", "Time"].includes(h) ? "text-right" : ""}`}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    <TableSkeleton />
                  </tbody>
                </table>
              </div>
            ) : trades.length === 0 ? (
              <div className="flex h-64 flex-col items-center justify-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-full border border-border">
                  <TrendingUp className="h-5 w-5 text-muted opacity-40" />
                </div>
                <div className="text-center">
                  <p className="text-sm font-medium text-white">No trades yet</p>
                  <p className="mt-0.5 text-xs text-muted">
                    Execute your first paper trade using the form.
                  </p>
                </div>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-border text-left">
                      <th className="px-3 py-2.5 font-medium text-muted">#</th>
                      <th className="px-3 py-2.5 font-medium text-muted">Asset</th>
                      <th className="px-3 py-2.5 font-medium text-muted">Side</th>
                      <th className="px-3 py-2.5 font-medium text-muted text-right">Price</th>
                      <th className="px-3 py-2.5 font-medium text-muted text-right">Amount</th>
                      <th className="px-3 py-2.5 font-medium text-muted">By</th>
                      <th className="px-3 py-2.5 font-medium text-muted text-right">Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trades.map((t) => (
                      <tr
                        key={t.id}
                        className="border-b border-border/40 transition-colors hover:bg-white/[0.02]"
                      >
                        <td className="px-3 py-2.5 font-mono text-[11px] text-muted">
                          #{t.id}
                        </td>
                        <td className="px-3 py-2.5 font-bold text-white">
                          {t.symbol}
                        </td>
                        <td className="px-3 py-2.5">
                          <SideBadge side={t.side} />
                        </td>
                        <td className="px-3 py-2.5 text-right tabular-nums text-white">
                          {formatCurrency(t.price)}
                        </td>
                        <td className="px-3 py-2.5 text-right tabular-nums font-medium text-white">
                          {formatCurrency(t.price * t.qty)}
                        </td>
                        <td className="px-3 py-2.5">
                          <ByBadge rationale={t.rationale} />
                        </td>
                        <td className="px-3 py-2.5 text-right tabular-nums text-muted">
                          {formatTime(t.created_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Footer legend */}
            {!loadingTrades && trades.length > 0 && (
              <div className="flex items-center gap-4 border-t border-border px-4 py-2.5">
                <span className="flex items-center gap-1.5 text-[11px] text-muted">
                  <span className="flex items-center gap-1 rounded border border-border bg-surface2 px-1.5 py-0.5 text-[10px] font-bold text-muted">
                    <Sparkles className="h-2.5 w-2.5" /> AI
                  </span>
                  Executed by AI agent
                </span>
                <span className="flex items-center gap-1.5 text-[11px] text-muted">
                  <span className="flex items-center gap-1 rounded border border-accent/30 bg-accent/10 px-1.5 py-0.5 text-[10px] font-bold text-accent">
                    <UserIcon className="h-2.5 w-2.5" /> User
                  </span>
                  Manual paper trade
                </span>
                <span className="ml-auto text-[10px] text-muted">
                  {trades.filter((t) => t.side === "BUY").length} buys ·{" "}
                  {trades.filter((t) => t.side === "SELL").length} sells
                </span>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
