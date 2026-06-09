"use client";

import { useCallback, useEffect, useState } from "react";
import {
  createPortfolio, getAgentLogs, getPortfolioStatus, getTrades, toggleMode,
  type AgentRunOut, type PortfolioStatus, type TradeOut, type TradingMode,
} from "@/lib/api";
import { MOCK_STATUS, MOCK_LOGS, MOCK_TRADES } from "@/lib/mockData";
import { getAsset, type AssetType } from "@/lib/mockAssets";

import TopNav             from "@/components/TopNav";
import AssetSelectorBar   from "@/components/AssetSelectorBar";
import NAVWidget          from "@/components/NAVWidget";
import PriceChart         from "@/components/PriceChart";
import AIAnalysisWidget   from "@/components/AIAnalysisWidget";
import PortfolioWidget    from "@/components/PortfolioWidget";
import AILogsWidget       from "@/components/AILogsWidget";
import TradeHistoryWidget from "@/components/TradeHistoryWidget";
import AnalysisPanel      from "@/components/AnalysisPanel";
import NewsWidget         from "@/components/NewsWidget";

const STORAGE_KEY = "alphaagent_portfolio_id";

async function resolvePortfolioId(): Promise<number> {
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored) {
    try { await getPortfolioStatus(Number(stored)); return Number(stored); } catch { /* stale */ }
  }
  const created = await createPortfolio("demo");
  window.localStorage.setItem(STORAGE_KEY, String(created.id));
  return created.id;
}

export default function DashboardPage() {
  // ── Portfolio state ────────────────────────────────────────────────────────
  const [portfolioId,  setPortfolioId]  = useState<number | null>(null);
  const [status,       setStatus]       = useState<PortfolioStatus | null>(null);
  const [logs,         setLogs]         = useState<AgentRunOut[]>([]);
  const [trades,       setTrades]       = useState<TradeOut[]>([]);
  const [loading,      setLoading]      = useState(true);
  const [apiConnected, setApiConnected] = useState(false);
  const [mode,         setMode]         = useState<TradingMode>("paper");

  // ── Global asset context ───────────────────────────────────────────────────
  const [selectedAsset, setSelectedAsset] = useState("BTC");
  const [assetType,     setAssetType]     = useState<AssetType>("crypto");

  const assetData = getAsset(selectedAsset);

  // ── Backend data loading ───────────────────────────────────────────────────
  const load = useCallback(async (id: number) => {
    const [s, l, t] = await Promise.all([
      getPortfolioStatus(id), getAgentLogs(id), getTrades(id),
    ]);
    setStatus(s); setLogs(l); setTrades(t);
    setApiConnected(true);
  }, []);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const id = await resolvePortfolioId();
        if (!active) return;
        setPortfolioId(id);
        await load(id);
      } catch {
        if (active) {
          setStatus(MOCK_STATUS); setLogs(MOCK_LOGS); setTrades(MOCK_TRADES);
          setApiConnected(false);
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => { active = false; };
  }, [load]);

  const handleModeChange = async (newMode: TradingMode) => {
    setMode(newMode);
    if (portfolioId) { try { await toggleMode(portfolioId, newMode); } catch { /* offline */ } }
  };

  const handleAssetChange = (symbol: string) => {
    setSelectedAsset(symbol);
    const a = getAsset(symbol);
    if (a) setAssetType(a.type);
  };

  const display = status ?? MOCK_STATUS;

  return (
    <div className="min-h-screen bg-bg text-white">

      {/* ── Sticky top bar ── */}
      <TopNav
        mode={mode}
        onModeChange={handleModeChange}
        apiConnected={apiConnected}
        portfolioUser={display.user}
      />

      {/* ── Sticky asset selector ── */}
      <AssetSelectorBar
        selectedAsset={selectedAsset}
        assetType={assetType}
        onAssetChange={handleAssetChange}
        onTypeChange={setAssetType}
      />

      {/* ── Main content ── */}
      <main className="mx-auto max-w-[1600px] space-y-3.5 px-4 py-4 lg:px-6">
        {loading ? (
          <div className="flex h-[70vh] items-center justify-center">
            <div className="flex flex-col items-center gap-3">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-border border-t-accent" />
              <p className="text-sm text-muted">Loading portfolio…</p>
            </div>
          </div>
        ) : (
          <>
            {/* ── Row 1: NAV quick stats ── */}
            <NAVWidget status={display} />

            {/* ── Row 2: Price Chart + AI Analysis ── */}
            <div className="grid grid-cols-1 gap-3.5 xl:grid-cols-12">
              <div className="xl:col-span-7">
                <PriceChart asset={assetData} />
              </div>
              <div className="xl:col-span-5">
                <AIAnalysisWidget asset={assetData} />
              </div>
            </div>

            {/* ── Row 3: Portfolio positions + News Feed ── */}
            <div className="grid grid-cols-1 gap-3.5 lg:grid-cols-2">
              <PortfolioWidget positions={display.positions} />
              <NewsWidget selectedAsset={selectedAsset} />
            </div>

            {/* ── Row 4: AI Logs + Analysis Panel ── */}
            <div className="grid grid-cols-1 gap-3.5 lg:grid-cols-2">
              <AILogsWidget logs={logs} />
              {portfolioId !== null && (
                <AnalysisPanel
                  portfolioId={portfolioId}
                  defaultSymbol={selectedAsset}
                  onComplete={() => load(portfolioId)}
                />
              )}
            </div>

            {/* ── Row 5: Trade History ── */}
            <TradeHistoryWidget trades={trades} />
          </>
        )}
      </main>
    </div>
  );
}
