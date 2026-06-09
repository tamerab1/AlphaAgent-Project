export type AssetType = "crypto" | "stock";
export type AIAction  = "BUY" | "HOLD" | "SELL";
export type MACDSignal = "bullish" | "bearish" | "neutral";

export interface PricePoint { t: number; p: number }

export interface AssetInfo {
  symbol:        string;
  name:          string;
  type:          AssetType;
  price:         number;
  change24h:     number;   // %
  volume24h:     number;   // USD
  high24h:       number;
  low24h:        number;
  rsi:           number;
  macdSignal:    MACDSignal;
  ma50:          number;
  ma200:         number;
  support:       number;
  resistance:    number;
  sentimentScore: number;  // 0–100
  aiAction:      AIAction;
  aiConfidence:  number;   // 0–1
  aiReasoning:   string;
  aiTarget:      number;
  aiStopLoss:    number;
  history:       PricePoint[];
}

// Deterministic price history — starts at yesterday's price, ends at today's.
function genHistory(
  end: number,
  change24h: number,
  volatility: number,
  seed: number,
  n = 200,
): PricePoint[] {
  const start = end / (1 + change24h / 100);
  const pts: PricePoint[] = [];
  for (let i = 0; i < n; i++) {
    const pct   = i / (n - 1);
    const base  = start + (end - start) * pct;
    const s     = (Math.abs(seed) % 9) + 1;
    const noise =
      Math.sin(i * s * 0.14 + 0.3)  * 0.45 +
      Math.sin(i * s * 0.04 + 1.2)  * 0.35 +
      Math.sin(i * 0.65  + s * 0.9) * 0.20;
    pts.push({ t: i, p: Math.max(base + noise * volatility, 0.0001) });
  }
  pts[n - 1].p = end;
  return pts;
}

export const ASSETS: AssetInfo[] = [
  // ── Crypto ────────────────────────────────────────────────────────────────
  {
    symbol: "BTC", name: "Bitcoin", type: "crypto",
    price: 67850, change24h: 2.4, volume24h: 28_400_000_000,
    high24h: 68_412, low24h: 66_023,
    rsi: 62.4, macdSignal: "bullish", ma50: 64_200, ma200: 52_800,
    support: 64_500, resistance: 69_200,
    sentimentScore: 78, aiAction: "BUY", aiConfidence: 0.87,
    aiReasoning: "RSI trending upward from oversold territory. Institutional accumulation detected on-chain. Breaking above 50-day MA with volume confirmation. Bullish MACD divergence aligns with strong demand zone.",
    aiTarget: 72_400, aiStopLoss: 63_100,
    history: genHistory(67850, 2.4, 820, 2.1),
  },
  {
    symbol: "ETH", name: "Ethereum", type: "crypto",
    price: 3380, change24h: 1.2, volume24h: 14_200_000_000,
    high24h: 3_428, low24h: 3_298,
    rsi: 55.8, macdSignal: "bullish", ma50: 3_180, ma200: 2_800,
    support: 3_200, resistance: 3_520,
    sentimentScore: 64, aiAction: "BUY", aiConfidence: 0.72,
    aiReasoning: "Pectra upgrade catalyst approaching. DeFi TVL growing steadily. Consolidating above key $3,200 support with positive MACD crossover. Staking yield remains attractive institutional draw.",
    aiTarget: 3_700, aiStopLoss: 3_120,
    history: genHistory(3380, 1.2, 58, 1.7),
  },
  {
    symbol: "SOL", name: "Solana", type: "crypto",
    price: 195, change24h: 3.1, volume24h: 4_800_000_000,
    high24h: 198.4, low24h: 188.2,
    rsi: 71.2, macdSignal: "bullish", ma50: 175, ma200: 140,
    support: 182, resistance: 205,
    sentimentScore: 82, aiAction: "HOLD", aiConfidence: 0.69,
    aiReasoning: "Ecosystem momentum very strong but RSI approaching overbought (71.2). Near-term pullback likely before continuation. Cup-and-handle forming on weekly. Wait for retest of $182 before adding.",
    aiTarget: 225, aiStopLoss: 175,
    history: genHistory(195, 3.1, 4.2, 3.2),
  },
  {
    symbol: "BNB", name: "BNB", type: "crypto",
    price: 580, change24h: -0.8, volume24h: 1_900_000_000,
    high24h: 592, low24h: 574,
    rsi: 48.3, macdSignal: "neutral", ma50: 565, ma200: 480,
    support: 558, resistance: 608,
    sentimentScore: 52, aiAction: "HOLD", aiConfidence: 0.55,
    aiReasoning: "Sideways consolidation in $558–$608 band. RSI neutral at 48. Exchange token utility demand stable. Awaiting volume catalyst to break range.",
    aiTarget: 620, aiStopLoss: 545,
    history: genHistory(580, -0.8, 9, 0.9),
  },
  {
    symbol: "XRP", name: "Ripple", type: "crypto",
    price: 0.61, change24h: 0.5, volume24h: 2_100_000_000,
    high24h: 0.624, low24h: 0.601,
    rsi: 44.7, macdSignal: "neutral", ma50: 0.58, ma200: 0.50,
    support: 0.57, resistance: 0.65,
    sentimentScore: 48, aiAction: "HOLD", aiConfidence: 0.52,
    aiReasoning: "Legal clarity improving post-SEC. Price consolidating near $0.60 with low volume — directional breakout above $0.65 needed for conviction. Watchlist until catalyst.",
    aiTarget: 0.72, aiStopLoss: 0.55,
    history: genHistory(0.61, 0.5, 0.012, 1.3),
  },
  {
    symbol: "ADA", name: "Cardano", type: "crypto",
    price: 0.42, change24h: -1.2, volume24h: 980_000_000,
    high24h: 0.432, low24h: 0.413,
    rsi: 38.2, macdSignal: "bearish", ma50: 0.46, ma200: 0.45,
    support: 0.39, resistance: 0.46,
    sentimentScore: 35, aiAction: "SELL", aiConfidence: 0.61,
    aiReasoning: "RSI declining toward oversold. Below both 50 and 200-day MA — double-MA resistance overhead. Developer activity index declining. MACD negative crossover confirmed.",
    aiTarget: 0.46, aiStopLoss: 0.38,
    history: genHistory(0.42, -1.2, 0.008, 2.8),
  },
  // ── Stocks ────────────────────────────────────────────────────────────────
  {
    symbol: "NVDA", name: "Nvidia", type: "stock",
    price: 1023, change24h: 1.8, volume24h: 28_600_000_000,
    high24h: 1_038, low24h: 998,
    rsi: 68.4, macdSignal: "bullish", ma50: 960, ma200: 810,
    support: 985, resistance: 1_050,
    sentimentScore: 74, aiAction: "BUY", aiConfidence: 0.81,
    aiReasoning: "AI compute demand structurally strong. Blackwell GPU ramp exceeding expectations. Q3 data center guidance raised. RSI 68 tempers near-term upside — scale in on any pullback to $985 support.",
    aiTarget: 1_120, aiStopLoss: 962,
    history: genHistory(1023, 1.8, 18, 1.4),
  },
  {
    symbol: "AAPL", name: "Apple", type: "stock",
    price: 201, change24h: -0.3, volume24h: 8_200_000_000,
    high24h: 203.8, low24h: 199.2,
    rsi: 52.1, macdSignal: "neutral", ma50: 196, ma200: 182,
    support: 195, resistance: 210,
    sentimentScore: 58, aiAction: "HOLD", aiConfidence: 0.64,
    aiReasoning: "Apple Intelligence adoption growing steadily. Services revenue compounding. Price range-bound between $195–$210. Await breakout confirmation above $210 resistance before adding.",
    aiTarget: 220, aiStopLoss: 190,
    history: genHistory(201, -0.3, 3.1, 1.1),
  },
  {
    symbol: "TSLA", name: "Tesla", type: "stock",
    price: 248, change24h: -2.1, volume24h: 12_400_000_000,
    high24h: 256, low24h: 245,
    rsi: 35.6, macdSignal: "bearish", ma50: 268, ma200: 230,
    support: 238, resistance: 268,
    sentimentScore: 31, aiAction: "SELL", aiConfidence: 0.65,
    aiReasoning: "Delivery miss for Q2 consecutive. Margin compression ongoing. Bearish MACD below 50-day MA. FSD adoption slower than projected. Key $238 support level now in focus.",
    aiTarget: 270, aiStopLoss: 235,
    history: genHistory(248, -2.1, 5.8, 3.6),
  },
  {
    symbol: "MSFT", name: "Microsoft", type: "stock",
    price: 425, change24h: 0.9, volume24h: 11_800_000_000,
    high24h: 428, low24h: 419,
    rsi: 58.3, macdSignal: "bullish", ma50: 412, ma200: 390,
    support: 415, resistance: 440,
    sentimentScore: 67, aiAction: "BUY", aiConfidence: 0.74,
    aiReasoning: "Azure AI revenue +38% YoY. Copilot enterprise adoption accelerating. Above both MAs with healthy structure. RSI mid-range with clear room to run toward $440 resistance.",
    aiTarget: 455, aiStopLoss: 408,
    history: genHistory(425, 0.9, 7.2, 0.7),
  },
  {
    symbol: "GOOGL", name: "Alphabet", type: "stock",
    price: 178, change24h: 1.4, volume24h: 9_600_000_000,
    high24h: 179.8, low24h: 175.2,
    rsi: 61.7, macdSignal: "bullish", ma50: 168, ma200: 155,
    support: 170, resistance: 185,
    sentimentScore: 72, aiAction: "BUY", aiConfidence: 0.76,
    aiReasoning: "Search + Cloud + Waymo all accelerating. Gemini AI integration showing early monetisation. Breaking out of 6-month consolidation. MACD bullish crossover confirmed on daily chart.",
    aiTarget: 195, aiStopLoss: 168,
    history: genHistory(178, 1.4, 2.9, 1.8),
  },
  {
    symbol: "META", name: "Meta", type: "stock",
    price: 524, change24h: 2.2, volume24h: 14_300_000_000,
    high24h: 528, low24h: 511,
    rsi: 65.3, macdSignal: "bullish", ma50: 492, ma200: 440,
    support: 505, resistance: 545,
    sentimentScore: 76, aiAction: "BUY", aiConfidence: 0.80,
    aiReasoning: "Ad revenue growth accelerating. AI-driven recommendation improving engagement +22%. Llama 3 enterprise adoption solid. Strong above both MAs. Bullish flag pattern on daily.",
    aiTarget: 568, aiStopLoss: 498,
    history: genHistory(524, 2.2, 9.8, 2.4),
  },
];

export const ASSET_MAP = Object.fromEntries(ASSETS.map((a) => [a.symbol, a]));
export const CRYPTO_ASSETS = ASSETS.filter((a) => a.type === "crypto");
export const STOCK_ASSETS  = ASSETS.filter((a) => a.type === "stock");

export function getAsset(symbol: string): AssetInfo | undefined {
  return ASSET_MAP[symbol.toUpperCase()];
}

// All symbols for search autocomplete
export const ALL_SYMBOLS = ASSETS.map((a) => a.symbol);
