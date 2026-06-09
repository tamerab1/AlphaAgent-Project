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

export type TradingMode = "paper" | "live";

export interface ToggleModeResponse {
  mode: string;
  message: string;
}

// --- Fetch helper ------------------------------------------------------------

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}${detail ? `: ${detail}` : ""}`);
  }
  return res.json() as Promise<T>;
}

// --- Endpoints ---------------------------------------------------------------

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

export function toggleMode(
  portfolioId: number,
  mode: TradingMode
): Promise<ToggleModeResponse> {
  return request<ToggleModeResponse>(`/api/trading/${portfolioId}/toggle-mode`, {
    method: "POST",
    body: JSON.stringify({ mode }),
  });
}
