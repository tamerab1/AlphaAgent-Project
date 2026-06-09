from fastapi import APIRouter

from app.schemas.agent import AnalystDecision, MarketData, PortfolioSnapshot
from app.schemas.api import AssetDetail, Quote
from app.services import llm, market_data

router = APIRouter(prefix="/api", tags=["market"])

# Neutral portfolio context for the asset-detail analyst call (not a real trade).
_NEUTRAL_PORTFOLIO = PortfolioSnapshot(cash_balance=100000.0, total_value=100000.0)


# Declared before "/market/{symbol}" so "quotes" isn't captured as a symbol.
@router.get("/market/quotes", response_model=list[Quote])
def market_quotes(symbols: str = ""):
    """Live price + 24h change for several tickers (the ticker bar), one call."""
    wanted = [s for s in symbols.split(",") if s.strip()]
    return market_data.get_quotes(wanted)


@router.get("/market/{symbol}", response_model=AssetDetail)
def market_detail(symbol: str):
    """Live price + indicators + AI read for one asset (powers the chart/AI widgets)."""
    detail = market_data.get_asset_detail(symbol)
    decision = llm.analyze(
        MarketData(symbol=detail["symbol"], price=detail["price"], rsi=detail["rsi"]),
        _NEUTRAL_PORTFOLIO,
    )
    return AssetDetail(
        **detail,
        sentiment_score=_sentiment_score(decision),
        ai_action=decision.action,
        ai_confidence=decision.confidence,
        ai_reasoning=decision.reasoning,
        ai_target=decision.target_price or detail["resistance"],
        ai_stop_loss=decision.stop_loss or detail["support"],
    )


def _sentiment_score(decision: AnalystDecision) -> float:
    """Map the analyst decision to a 0-100 market-sentiment score."""
    if decision.action == "BUY":
        return round(min(95.0, 55.0 + decision.confidence * 40.0), 1)
    if decision.action == "SELL":
        return round(max(5.0, 45.0 - decision.confidence * 40.0), 1)
    return 50.0
