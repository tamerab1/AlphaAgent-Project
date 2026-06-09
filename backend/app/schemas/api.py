from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


# --- Portfolio ---------------------------------------------------------------
class PortfolioCreate(BaseModel):
    user: str
    cash_balance: float = 100000.0


class PortfolioOut(BaseModel):
    id: int
    user: str
    cash_balance: float


class PositionOut(BaseModel):
    symbol: str
    qty: float
    avg_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float


class PortfolioStatus(BaseModel):
    id: int
    user: str
    cash_balance: float
    positions_value: float
    total_value: float
    unrealized_pnl: float
    positions: list[PositionOut]


class TradeOut(BaseModel):
    id: int
    symbol: str
    side: str
    qty: float
    price: float
    rationale: Optional[str]
    created_at: datetime


# --- AI ----------------------------------------------------------------------
class AnalyzeRequest(BaseModel):
    symbol: str
    # Optional chart screenshot as a base64 data URL (data:image/png;base64,...).
    chart_image: Optional[str] = None


class ChartReadRequest(BaseModel):
    # Chart screenshot as a base64 data URL.
    chart_image: str
    symbol: Optional[str] = None


class AgentRunOut(BaseModel):
    id: int
    symbol: str
    analyst: Optional[dict]
    risk: Optional[dict]
    executed: bool
    created_at: datetime


# --- Market / asset detail ---------------------------------------------------
class Quote(BaseModel):
    symbol: str
    price: float
    change_24h: float


class PricePoint(BaseModel):
    t: int
    p: float


class AssetDetail(BaseModel):
    symbol: str
    name: str
    type: Literal["crypto", "stock"]
    price: float
    change_24h: float
    volume_24h: float
    high_24h: float
    low_24h: float
    rsi: float
    macd_signal: Literal["bullish", "bearish", "neutral"]
    ma50: float
    ma200: float
    support: float
    resistance: float
    sentiment_score: float
    ai_action: Literal["BUY", "SELL", "HOLD"]
    ai_confidence: float
    ai_reasoning: str
    ai_target: float
    ai_stop_loss: float
    source: str  # "twelvedata" | "stooq" | "seed"
    history: list[PricePoint]


# --- News --------------------------------------------------------------------
class NewsItem(BaseModel):
    id: str
    headline: str
    symbol: str
    sentiment: Literal["bullish", "bearish", "neutral"]
    summary: str
    sentiment_breakdown: str = ""
    source: str
    url: Optional[str] = None
    published_at: datetime


# --- Trading -----------------------------------------------------------------
class ManualTradeRequest(BaseModel):
    symbol: str
    side: Literal["BUY", "SELL"]
    usd_amount: float


class ToggleModeRequest(BaseModel):
    mode: Literal["paper", "live"]


class ToggleModeResponse(BaseModel):
    mode: str
    message: str
