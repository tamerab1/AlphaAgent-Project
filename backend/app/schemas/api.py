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


# --- News --------------------------------------------------------------------
class NewsItem(BaseModel):
    id: str
    headline: str
    symbol: str
    sentiment: Literal["bullish", "bearish", "neutral"]
    summary: str
    source: str
    published_at: datetime


# --- Trading -----------------------------------------------------------------
class ToggleModeRequest(BaseModel):
    mode: Literal["paper", "live"]


class ToggleModeResponse(BaseModel):
    mode: str
    message: str
