from typing import Literal, Optional, TypedDict

from pydantic import BaseModel, Field


class AnalystDecision(BaseModel):
    """Structured output from the analyst agent."""

    action: Literal["BUY", "SELL", "HOLD"]
    symbol: str
    reasoning: str
    confidence: float = Field(ge=0.0, le=1.0)
    suggested_pct: float = Field(ge=0.0, le=1.0)
    target_price: Optional[float] = Field(default=None, ge=0.0)
    stop_loss: Optional[float] = Field(default=None, ge=0.0)


class RiskDecision(BaseModel):
    """Structured output from the risk agent."""

    approved: bool
    reason: str
    adjusted_pct: float = Field(ge=0.0, le=1.0)


class DebateArgument(BaseModel):
    """One side's case in the analyst debate (bull or bear)."""

    stance: Literal["bull", "bear"]
    thesis: str
    key_points: list[str] = Field(default_factory=list)
    conviction: float = Field(ge=0.0, le=1.0)


class ChartReading(BaseModel):
    """Visual read of an uploaded chart screenshot (multimodal analyst)."""

    summary: str
    support_levels: list[float] = Field(default_factory=list)
    resistance_levels: list[float] = Field(default_factory=list)
    patterns: list[str] = Field(default_factory=list)
    bias: Literal["bullish", "bearish", "neutral"] = "neutral"


class MarketData(BaseModel):
    """Ingested market context for a symbol.

    Base fields (price/rsi/headlines) come from ``get_market_data``; the optional
    technical fields are enriched by the ingest node from ``get_asset_detail`` so
    the agents can reason over the full picture, not just RSI.
    """

    symbol: str
    price: float
    rsi: float
    headlines: list[str] = Field(default_factory=list)
    # Optional technical context (None when unavailable).
    macd_signal: Optional[Literal["bullish", "bearish", "neutral"]] = None
    ma50: Optional[float] = None
    ma200: Optional[float] = None
    support: Optional[float] = None
    resistance: Optional[float] = None
    change_24h: Optional[float] = None


class PortfolioSnapshot(BaseModel):
    """Minimal portfolio view the agents reason over."""

    cash_balance: float
    total_value: float
    symbol_exposure: float = 0.0


class SentimentResult(BaseModel):
    """Sentiment tag produced for a single news headline."""

    sentiment: Literal["bullish", "bearish", "neutral"]
    summary: str
    sentiment_breakdown: str = Field(
        default="",
        description=(
            "2-3 sentences explaining WHY this headline is bullish/bearish/neutral "
            "for the specific asset — include the market mechanism."
        ),
    )


class AgentState(TypedDict, total=False):
    """Mutable state threaded through the LangGraph flow."""

    symbol: str
    chart_image: Optional[str]
    market: MarketData
    portfolio: PortfolioSnapshot
    bull: DebateArgument
    bear: DebateArgument
    analyst: AnalystDecision
    risk: RiskDecision
    executed: bool
    log: list[str]
