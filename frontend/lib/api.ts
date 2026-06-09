// Typed client for the AlphaAgent FastAPI backend.
// Endpoints mirror backend/app/api (Phase 4): portfolio, ai, trading.

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// --- Domain types (mirror backend/app/schemas) ------------------------------

export interface PortfolioOut {
  id: number;
  user: string;
  cash_balance: number;
}

export interface PositionOut {
  symbol: string;
  qty: number;
  avg_price: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
}

export interface PortfolioStatus {
  id: number;
  user: string;
  cash_balance: number;
  positions_value: number;
  total_value: number;
  unrealized_pnl: number;
  positions: PositionOut[];
}

export interface AnalystDecision {
  action: "BUY" | "SELL" | "HOLD";
  symbol: string;
  reasoning: string;
  confidence: number;
  suggested_pct: number;
  target_price: number | null;
  stop_loss: number | null;
}

export interface RiskDecision {
  approved: boolean;
  reason: string;
  adjusted_pct: number;
}

export interface AgentRunOut {
  id: number;
  symbol: string;
  analyst: AnalystDecision | null;
  risk: RiskDecision | null;
  executed: boolean;
  created_at: string;
}

export interface TradeOut {
  id: number;
  symbol: string;
  side: string;
  qty: number;
  price: number;
  rationale: string | null;
  created_at: string;
}

export interface ChartReading {
  summary: string;
  support_levels: number[];
  resistance_levels: number[];
  patterns: string[];
  bias: "bullish" | "bearish" | "neutral";
}

export interface NewsItem {
  id: string;
  headline: string;
  symbol: string;
  sentiment: "bullish" | "bearish" | "neutral";
  summary: string;
  source: string;
  published_at: string;
}

export interface AssetDetail {
  symbol: string;
  name: string;
  type: "crypto" | "stock";
  price: number;
  change_24h: number;
  volume_24h: number;
  high_24h: number;
  low_24h: number;
  rsi: number;
  macd_signal: "bullish" | "bearish" | "neutral";
  ma50: number;
  ma200: number;
  support: number;
  resistance: number;
  sentiment_score: number;
  ai_action: "BUY" | "SELL" | "HOLD";
  ai_confidence: number;
  ai_reasoning: string;
  ai_target: number;
  ai_stop_loss: number;
  source: string;
  history: { t: number; p: number }[];
}

export type TradingMode = "paper" | "live";

export interface ToggleModeResponse {
  mode: string;
  message: string;
}

// --- Auth token management ---------------------------------------------------
// The active Supabase JWT is stored here and injected into every request.
// Call setAuthToken(session.access_token) when a session is established and
// setAuthToken(null) on sign-out.

let _authToken: string | null = null;

export function setAuthToken(token: string | null): void {
  _authToken = token;
}

export function getAuthToken(): string | null {
  return _authToken;
}

// --- Fetch helper ------------------------------------------------------------

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const baseHeaders: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (_authToken) {
    baseHeaders["Authorization"] = `Bearer ${_authToken}`;
  }
  const res = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
    ...init,
    // Spread caller headers last so they can override Content-Type if needed,
    // but our Authorization header is always present when a token exists.
    headers: { ...baseHeaders, ...(init?.headers as Record<string, string>) },
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}${detail ? `: ${detail}` : ""}`);
  }
  return res.json() as Promise<T>;
}

// --- Endpoints ---------------------------------------------------------------

/**
 * Fetch (or auto-create) the authenticated user's portfolio.
 * The backend uses the JWT to resolve the user UUID and creates a $100k paper
 * portfolio on first call. Always call after setAuthToken() is set.
 */
export function getMyPortfolio(): Promise<PortfolioOut> {
  return request<PortfolioOut>("/api/v1/users/me/portfolio");
}

export function createPortfolio(
  user: string,
  cashBalance = 100000.0
): Promise<PortfolioOut> {
  return request<PortfolioOut>("/api/portfolios", {
    method: "POST",
    body: JSON.stringify({ user, cash_balance: cashBalance }),
  });
}

export function getPortfolioStatus(
  portfolioId: number
): Promise<PortfolioStatus> {
  return request<PortfolioStatus>(`/api/portfolio/${portfolioId}/status`);
}

export function getAgentLogs(portfolioId: number): Promise<AgentRunOut[]> {
  return request<AgentRunOut[]>(`/api/ai/${portfolioId}/logs`);
}

export function getTrades(portfolioId: number): Promise<TradeOut[]> {
  return request<TradeOut[]>(`/api/portfolio/${portfolioId}/trades`);
}

export function readChart(
  chartImage: string,
  symbol?: string
): Promise<ChartReading> {
  return request<ChartReading>("/api/ai/read-chart", {
    method: "POST",
    body: JSON.stringify({ chart_image: chartImage, symbol: symbol ?? null }),
  });
}

export function getNews(symbol?: string): Promise<NewsItem[]> {
  const params = symbol ? `?symbol=${encodeURIComponent(symbol)}` : "";
  return request<NewsItem[]>(`/api/ai/news${params}`);
}

export function getAssetDetail(symbol: string): Promise<AssetDetail> {
  return request<AssetDetail>(`/api/market/${encodeURIComponent(symbol)}`);
}

export interface Quote {
  symbol: string;
  price: number;
  change_24h: number;
}

export function getQuotes(symbols: string[]): Promise<Quote[]> {
  const q = encodeURIComponent(symbols.join(","));
  return request<Quote[]>(`/api/market/quotes?symbols=${q}`);
}

export function toggleMode(
  portfolioId: number,
  mode: TradingMode
): Promise<ToggleModeResponse> {
  return request<ToggleModeResponse>(`/api/trading/${portfolioId}/toggle-mode`, {
    method: "POST",
    body: JSON.stringify({ mode }),
  });
}
