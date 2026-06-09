from fastapi import APIRouter

from app.schemas.agent import MarketData, PortfolioSnapshot
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
        MarketData(
            symbol=detail["symbol"],
            price=detail["price"],
            rsi=detail["rsi"],
            macd_signal=detail["macd_signal"],
            ma50=detail["ma50"],
            ma200=detail["ma200"],
            support=detail["support"],
            resistance=detail["resistance"],
            change_24h=detail["change_24h"],
        ),
        _NEUTRAL_PORTFOLIO,
    )
    return AssetDetail(
        **detail,
        sentiment_score=_sentiment_score(detail),
        ai_action=decision.action,
        ai_confidence=decision.confidence,
        ai_reasoning=decision.reasoning,
        ai_target=decision.target_price or detail["resistance"],
        ai_stop_loss=decision.stop_loss or detail["support"],
    )


def _sentiment_score(detail: dict) -> float:
    """Composite 0-100 market-sentiment from the technical posture.

    Reflects the trend (MACD, price vs. the 50/200-day MAs, RSI momentum and the
    24h move) rather than the trade recommendation, so the gauge stays consistent
    with the indicators on screen — a bearish chart reads bearish even when the AI
    flags a speculative oversold bounce.
    """
    score = 50.0
    macd = detail.get("macd_signal")
    if macd == "bullish":
        score += 15.0
    elif macd == "bearish":
        score -= 15.0
    price = detail["price"]
    ma50, ma200 = detail.get("ma50"), detail.get("ma200")
    if ma50:
        score += 8.0 if price >= ma50 else -8.0
    if ma200:
        score += 8.0 if price >= ma200 else -8.0
    score += (detail["rsi"] - 50.0) * 0.3
    score += max(-10.0, min(10.0, detail.get("change_24h", 0.0)))
    return round(max(2.0, min(98.0, score)), 1)
