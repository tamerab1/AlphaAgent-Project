"use client";

import { useCallback, useEffect, useState } from "react";
import {
  getMyPortfolio, getAgentLogs, getPortfolioStatus, getTrades, toggleMode,
  getAssetDetail, setAuthToken,
  type AgentRunOut, type PortfolioStatus, type TradeOut, type TradingMode,
  type AssetDetail,
} from "@/lib/api";
import { MOCK_STATUS, MOCK_LOGS, MOCK_TRADES } from "@/lib/mockData";
import { getAsset, type AssetType, type AssetInfo } from "@/lib/mockAssets";
import { getCachedAsset } from "@/lib/assetUtils";
import { useSession } from "@/components/AuthGate";
import { supabase } from "@/lib/supabase";

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


export default function DashboardPage() {
  // ── Auth session — injected by AuthGate context ────────────────────────────
  const session = useSession();

  // Sync the module-level auth token. This effect is declared first so it runs
  // before the portfolio loading effect, guaranteeing the token is set before
  // any API call fires.
  useEffect(() => {
    setAuthToken(session?.access_token ?? null);
  }, [session?.access_token]);

  // Ensure the viewport starts at the top on every mount. Belt-and-suspenders
  // guard in case any widget scroll propagates to the page level.
  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

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
        // offline fallback: check static list then session-cached dynamic assets
        if (active) setAssetData(getAsset(selectedAsset) ?? getCachedAsset(selectedAsset));
      }
    })();
    return () => { active = false; };
  }, [selectedAsset]);

  // Keep assetType in sync with whatever asset is loaded. This covers dynamic
  // symbols (e.g. DOGE, MATIC) that aren't in the static ASSETS list so
  // handleAssetChange can't set the type immediately.
  useEffect(() => {
    if (assetData?.type) setAssetType(assetData.type);
  }, [assetData]);

  // ── Backend data loading ───────────────────────────────────────────────────
  const load = useCallback(async (id: number) => {
    const [s, l, t] = await Promise.all([
      getPortfolioStatus(id), getAgentLogs(id), getTrades(id),
    ]);
    setStatus(s); setLogs(l); setTrades(t);
    setApiConnected(true);
  }, []);

  // Portfolio loading is keyed on the user's ID so each authenticated user
  // gets their own isolated portfolio. getMyPortfolio() auto-creates a $100k
  // paper portfolio on first login for any new user.
  useEffect(() => {
    if (!session?.user?.id) return;
    let active = true;
    (async () => {
      try {
        const portfolio = await getMyPortfolio();
        if (!active) return;
        setPortfolioId(portfolio.id);
        await load(portfolio.id);
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
  }, [session?.user?.id, load]);

  const handleModeChange = async (newMode: TradingMode) => {
    setMode(newMode);
    if (portfolioId) { try { await toggleMode(portfolioId, newMode); } catch { /* offline */ } }
  };

  const handleAssetChange = (symbol: string) => {
    setSelectedAsset(symbol);
    // For known assets set the type immediately; dynamic assets will be synced
    // by the assetData effect once the fetch resolves.
    const a = getAsset(symbol) ?? getCachedAsset(symbol);
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
        portfolioUser={session?.user?.email ?? display.user}
        onSignOut={() => supabase.auth.signOut()}
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
