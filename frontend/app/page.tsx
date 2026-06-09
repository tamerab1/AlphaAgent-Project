"use client";

import { useCallback, useEffect, useState } from "react";
import {
  createPortfolio, getAgentLogs, getPortfolioStatus, getTrades, toggleMode,
  getAssetDetail,
  type AgentRunOut, type PortfolioStatus, type TradeOut, type TradingMode,
  type AssetDetail,
} from "@/lib/api";
import { MOCK_STATUS, MOCK_LOGS, MOCK_TRADES } from "@/lib/mockData";
import { getAsset, type AssetType, type AssetInfo } from "@/lib/mockAssets";

// Map the backend's snake_case AssetDetail onto the widgets' AssetInfo shape.
function toAssetInfo(d: AssetDetail): AssetInfo {
  return {
    symbol: d.symbol, name: d.name, type: d.type,
    price: d.price, change24h: d.change_24h, volume24h: d.volume_24h,
    high24h: d.high_24h, low24h: d.low_24h,
    rsi: d.rsi, macdSignal: d.macd_signal,
    ma50: d.ma50, ma200: d.ma200, support: d.support, resistance: d.resistance,
    sentimentScore: d.sentiment_score,
    aiAction: d.ai_action, aiConfidence: d.ai_confidence,
    aiReasoning: d.ai_reasoning, aiTarget: d.ai_target, aiStopLoss: d.ai_stop_loss,
    history: d.history,
  };
}

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
  // Live asset detail (price chart + AI widget); mock as the initial/fallback.
  const [assetData,     setAssetData]     = useState<AssetInfo | undefined>(
    getAsset("BTC"),
  );

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const detail = await getAssetDetail(selectedAsset);
        if (active) setAssetData(toAssetInfo(detail));
      } catch {
        if (active) setAssetData(getAsset(selectedAsset)); // offline fallback
      }
    })();
    return () => { active = false; };
  }, [selectedAsset]);

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
