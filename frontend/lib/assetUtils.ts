import type { AssetDetail } from "@/lib/api";
import type { AssetInfo } from "@/lib/mockAssets";

// Convert the backend AssetDetail response (snake_case) to the frontend AssetInfo shape.
export function toAssetInfo(d: AssetDetail): AssetInfo {
  return {
    symbol: d.symbol,
    name: d.name,
    type: d.type,
    price: d.price,
    change24h: d.change_24h,
    volume24h: d.volume_24h,
    high24h: d.high_24h,
    low24h: d.low_24h,
    rsi: d.rsi,
    macdSignal: d.macd_signal,
    ma50: d.ma50,
    ma200: d.ma200,
    support: d.support,
    resistance: d.resistance,
    sentimentScore: d.sentiment_score,
    aiAction: d.ai_action,
    aiConfidence: d.ai_confidence,
    aiReasoning: d.ai_reasoning,
    aiTarget: d.ai_target,
    aiStopLoss: d.ai_stop_loss,
    history: d.history,
  };
}

// Session-scoped cache for assets fetched dynamically from the backend.
// Keyed by uppercase symbol. Persists until the page is refreshed.
const _dynamicCache = new Map<string, AssetInfo>();

export function cacheDynamicAsset(info: AssetInfo): void {
  _dynamicCache.set(info.symbol.toUpperCase(), info);
}

export function getCachedAsset(symbol: string): AssetInfo | undefined {
  return _dynamicCache.get(symbol.toUpperCase());
}

export function getDynamicAssets(): AssetInfo[] {
  return [..._dynamicCache.values()];
}
