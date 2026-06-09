"use client";

import { useState, useEffect } from "react";
import {
  Bot, Target, ShieldAlert, TrendingUp, TrendingDown,
  Minus, Zap, CheckCircle2, XCircle,
} from "lucide-react";
import type { AssetInfo, MACDSignal } from "@/lib/mockAssets";

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtPrice(p: number): string {
  if (p >= 1_000_000) return `$${(p / 1_000_000).toFixed(2)}M`;
  if (p >= 1_000)     return `$${(p / 1_000).toFixed(1)}K`;
  if (p >= 1)         return `$${p.toFixed(2)}`;
  return `$${p.toFixed(4)}`;
}

interface SentimentCfg {
  label: string;
  color: string;
  barCls: string;
  badgeCls: string;
}

function getSentimentCfg(score: number): SentimentCfg {
  if (score >= 71) return { label: "VERY BULLISH", color: "#0ECB81", barCls: "bg-positive", badgeCls: "border-positive/50 bg-positive/10 text-positive shadow-[0_0_10px_rgba(14,203,129,0.25)]" };
  if (score >= 55) return { label: "BULLISH",      color: "#0ECB81", barCls: "bg-positive", badgeCls: "border-positive/50 bg-positive/10 text-positive" };
  if (score >= 45) return { label: "NEUTRAL",      color: "#848E9C", barCls: "bg-muted",    badgeCls: "border-border bg-surface2 text-muted" };
  if (score >= 31) return { label: "BEARISH",      color: "#F6465D", barCls: "bg-negative", badgeCls: "border-negative/50 bg-negative/10 text-negative" };
  return             { label: "VERY BEARISH",      color: "#F6465D", barCls: "bg-negative", badgeCls: "border-negative/50 bg-negative/10 text-negative shadow-[0_0_10px_rgba(246,70,93,0.25)]" };
}

function getRSICfg(rsi: number): { label: string; cls: string } {
  if (rsi < 30) return { label: "Oversold",  cls: "text-positive" };
  if (rsi < 45) return { label: "Weak",      cls: "text-negative" };
  if (rsi < 55) return { label: "Neutral",   cls: "text-muted"    };
  if (rsi < 70) return { label: "Strong",    cls: "text-positive" };
  return              { label: "Overbought", cls: "text-accent"   };
}

function getMACDCfg(sig: MACDSignal): { icon: typeof TrendingUp; label: string; cls: string } {
  if (sig === "bullish") return { icon: TrendingUp,   label: "Bullish",  cls: "text-positive" };
  if (sig === "bearish") return { icon: TrendingDown, label: "Bearish",  cls: "text-negative" };
  return                        { icon: Minus,        label: "Neutral",  cls: "text-muted"    };
}

function getMAStatus(price: number, ma: number): { label: string; cls: string } {
  return price >= ma
    ? { label: "Above ✓", cls: "text-positive" }
    : { label: "Below ✗", cls: "text-negative" };
}

function ActionBadge({ action }: { action: AssetInfo["aiAction"] }) {
  if (action === "BUY")
    return <span className="rounded-lg border border-positive/50 bg-positive/10 px-3 py-1 text-sm font-bold text-positive shadow-[0_0_12px_rgba(14,203,129,0.3)]">BUY</span>;
  if (action === "SELL")
    return <span className="rounded-lg border border-negative/50 bg-negative/10 px-3 py-1 text-sm font-bold text-negative shadow-[0_0_12px_rgba(246,70,93,0.3)]">SELL</span>;
  return <span className="rounded-lg border border-muted/30 bg-surface2 px-3 py-1 text-sm font-bold text-muted">HOLD</span>;
}

// ── Main component ────────────────────────────────────────────────────────────

interface AIAnalysisWidgetProps {
  asset: AssetInfo | undefined;
}

export default function AIAnalysisWidget({ asset }: AIAnalysisWidgetProps) {
  const [animScore, setAnimScore] = useState(0);

  // Animate score bar whenever asset changes
  useEffect(() => {
    setAnimScore(0);
    if (!asset) return;
    const id = setTimeout(() => setAnimScore(asset.sentimentScore), 80);
    return () => clearTimeout(id);
  }, [asset?.symbol, asset?.sentimentScore]);

  if (!asset) return (
    <div className="flex h-[380px] items-center justify-center rounded-xl border border-border bg-surface">
      <p className="text-sm text-muted">Select an asset for AI analysis.</p>
    </div>
  );

  const sc   = getSentimentCfg(asset.sentimentScore);
  const rsiC = getRSICfg(asset.rsi);
  const maC  = getMACDCfg(asset.macdSignal);
  const ma50S  = getMAStatus(asset.price, asset.ma50);
  const ma200S = getMAStatus(asset.price, asset.ma200);
  const MACDIcon = maC.icon;

  return (
    <div className="flex flex-col rounded-xl border border-border bg-surface overflow-hidden">

      {/* ── Header ── */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <Bot className="h-4 w-4 text-accent" />
          <h2 className="text-sm font-semibold text-white">AI Analysis</h2>
          <span className="rounded bg-surface2 px-1.5 py-0.5 text-[10px] font-medium text-muted">
            {asset.symbol}
          </span>
        </div>
        <span className="text-[11px] text-muted">
          Confidence <span className="font-bold text-white">{(asset.aiConfidence * 100).toFixed(0)}%</span>
        </span>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin">

        {/* ── Sentiment Score ── */}
        <div className="border-b border-border p-4">
          <p className="text-[10px] font-bold uppercase tracking-widest text-muted">Market Sentiment</p>
          <div className="mt-2.5 flex items-center justify-between">
            <div>
              <span className="text-4xl font-bold" style={{ color: sc.color }}>
                {asset.sentimentScore}
              </span>
              <span className="ml-1 text-lg font-bold text-muted">/100</span>
            </div>
            <span className={`rounded-full border px-3 py-1 text-[11px] font-bold tracking-wider ${sc.badgeCls}`}>
              {sc.label}
            </span>
          </div>

          {/* Score bar */}
          <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-border">
            <div
              className={`h-full rounded-full transition-all duration-1000 ease-out ${sc.barCls}`}
              style={{ width: `${animScore}%` }}
            />
          </div>
          <div className="mt-1 flex justify-between text-[9px] font-medium text-muted/60">
            <span>VERY BEARISH</span>
            <span>NEUTRAL</span>
            <span>VERY BULLISH</span>
          </div>
        </div>

        {/* ── Technical Indicators ── */}
        <div className="border-b border-border p-4">
          <p className="mb-3 text-[10px] font-bold uppercase tracking-widest text-muted">
            Technical Indicators
          </p>
          <div className="grid grid-cols-2 gap-2">

            <div className="rounded-lg bg-surface2 p-2.5">
              <p className="text-[10px] text-muted">RSI (14)</p>
              <p className="mt-0.5 text-base font-bold text-white">{asset.rsi.toFixed(1)}</p>
              <p className={`text-[10px] font-semibold ${rsiC.cls}`}>{rsiC.label}</p>
            </div>

            <div className="rounded-lg bg-surface2 p-2.5">
              <p className="text-[10px] text-muted">MACD Signal</p>
              <div className={`mt-0.5 flex items-center gap-1 ${maC.cls}`}>
                <MACDIcon className="h-4 w-4" />
                <span className="text-sm font-bold">{maC.label}</span>
              </div>
            </div>

            <div className="rounded-lg bg-surface2 p-2.5">
              <p className="text-[10px] text-muted">MA 50</p>
              <p className="mt-0.5 text-sm font-bold text-white">{fmtPrice(asset.ma50)}</p>
              <p className={`text-[10px] font-semibold ${ma50S.cls}`}>{ma50S.label}</p>
            </div>

            <div className="rounded-lg bg-surface2 p-2.5">
              <p className="text-[10px] text-muted">MA 200</p>
              <p className="mt-0.5 text-sm font-bold text-white">{fmtPrice(asset.ma200)}</p>
              <p className={`text-[10px] font-semibold ${ma200S.cls}`}>{ma200S.label}</p>
            </div>
          </div>
        </div>

        {/* ── Key Levels ── */}
        <div className="border-b border-border p-4">
          <p className="mb-3 text-[10px] font-bold uppercase tracking-widest text-muted">Key Price Levels</p>
          <div className="grid grid-cols-2 gap-2.5">
            <div className="flex items-center gap-2">
              <ShieldAlert className="h-3.5 w-3.5 shrink-0 text-positive" />
              <div>
                <p className="text-[10px] text-muted">Support</p>
                <p className="text-xs font-bold text-positive">{fmtPrice(asset.support)}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <ShieldAlert className="h-3.5 w-3.5 shrink-0 text-negative" />
              <div>
                <p className="text-[10px] text-muted">Resistance</p>
                <p className="text-xs font-bold text-negative">{fmtPrice(asset.resistance)}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Target className="h-3.5 w-3.5 shrink-0 text-accent" />
              <div>
                <p className="text-[10px] text-muted">AI Target</p>
                <p className="text-xs font-bold text-accent">{fmtPrice(asset.aiTarget)}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <XCircle className="h-3.5 w-3.5 shrink-0 text-negative/70" />
              <div>
                <p className="text-[10px] text-muted">Stop-Loss</p>
                <p className="text-xs font-bold text-negative/80">{fmtPrice(asset.aiStopLoss)}</p>
              </div>
            </div>
          </div>
        </div>

        {/* ── AI Recommendation ── */}
        <div className="p-4">
          <p className="mb-3 text-[10px] font-bold uppercase tracking-widest text-muted">AI Recommendation</p>
          <div className="rounded-xl border border-border bg-surface2 p-3.5">
            <div className="flex items-center justify-between">
              <ActionBadge action={asset.aiAction} />
              <div className="flex items-center gap-1.5 text-[11px] text-muted">
                <Zap className="h-3 w-3 text-accent" />
                {(asset.aiConfidence * 100).toFixed(0)}% confidence
              </div>
            </div>
            <p className="mt-3 text-xs leading-relaxed text-muted">{asset.aiReasoning}</p>
            <div className="mt-3 flex items-center gap-2">
              {asset.aiAction === "BUY" && (
                <span className="flex items-center gap-1 text-[10px] text-positive">
                  <CheckCircle2 className="h-3 w-3" /> Risk/reward ratio favourable
                </span>
              )}
              {asset.aiAction === "SELL" && (
                <span className="flex items-center gap-1 text-[10px] text-negative">
                  <XCircle className="h-3 w-3" /> Downside risk elevated
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
