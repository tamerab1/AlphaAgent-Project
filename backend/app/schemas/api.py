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


# --- AI ----------------------------------------------------------------------
class AnalyzeRequest(BaseModel):
    symbol: str


class AgentRunOut(BaseModel):
    id: int
    symbol: str
    analyst: Optional[dict]
    risk: Optional[dict]
    executed: bool
    created_at: datetime


# --- Trading -----------------------------------------------------------------
class ToggleModeRequest(BaseModel):
    mode: Literal["paper", "live"]


class ToggleModeResponse(BaseModel):
    mode: str
    message: str
