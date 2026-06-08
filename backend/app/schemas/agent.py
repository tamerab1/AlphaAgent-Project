from typing import Literal, TypedDict

from pydantic import BaseModel, Field


class AnalystDecision(BaseModel):
    """Structured output from the analyst agent."""

    action: Literal["BUY", "SELL", "HOLD"]
    symbol: str
    reasoning: str
    confidence: float = Field(ge=0.0, le=1.0)
    suggested_pct: float = Field(ge=0.0, le=1.0)


class RiskDecision(BaseModel):
    """Structured output from the risk agent."""

    approved: bool
    reason: str
    adjusted_pct: float = Field(ge=0.0, le=1.0)


class MarketData(BaseModel):
    """Ingested market context for a symbol (mocked in Phase 2)."""

    symbol: str
    price: float
    rsi: float
    headlines: list[str] = Field(default_factory=list)


class PortfolioSnapshot(BaseModel):
    """Minimal portfolio view the agents reason over."""

    cash_balance: float
    total_value: float
    symbol_exposure: float = 0.0


class AgentState(TypedDict, total=False):
    """Mutable state threaded through the LangGraph flow."""

    symbol: str
    market: MarketData
    portfolio: PortfolioSnapshot
    analyst: AnalystDecision
    risk: RiskDecision
    executed: bool
    log: list[str]
