import os
from typing import Optional

from app.schemas.agent import AnalystDecision, MarketData, PortfolioSnapshot

ANALYST_SYSTEM = (
    "You are a disciplined trading analyst. Given market data and the current "
    "portfolio, decide whether to BUY, SELL, or HOLD the symbol. Be conservative "
    "and explain your reasoning briefly. When recommending a BUY or SELL, include "
    "a realistic target_price and stop_loss; leave both null for HOLD."
)

ANALYST_VISION_HINT = (
    " A chart screenshot is attached; read its support/resistance levels and "
    "candlestick patterns and factor them into your decision."
)

RISK_SYSTEM = (
    "You are a risk manager. In one or two sentences give a brief sanity note on "
    "the proposed trade. Do not approve or reject; just flag anything notable."
)


def _has_api_key() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def analyze(
    market: MarketData,
    portfolio: PortfolioSnapshot,
    chart_image: Optional[str] = None,
) -> AnalystDecision:
    """Analyst decision, using gpt-4o-mini when a key is set, else a mock.

    When ``chart_image`` (a base64 data URL) is provided and a key is set, the
    image is sent to the multimodal model. Offline, the mock acknowledges the
    chart but still decides from the seed RSI.
    """
    if _has_api_key():
        return _llm_analyze(market, portfolio, chart_image)  # pragma: no cover
    return _mock_analyze(market, chart_image)


def risk_note(market: MarketData, decision: AnalystDecision) -> str:
    """Short LLM sanity note on the proposed trade (mocked when offline)."""
    if _has_api_key():
        return _llm_risk_note(market, decision)  # pragma: no cover
    return _mock_risk_note(market, decision)


def _mock_analyze(
    market: MarketData, chart_image: Optional[str] = None
) -> AnalystDecision:
    if market.rsi < 30:
        action, confidence, pct = "BUY", 0.7, 0.05
    elif market.rsi > 70:
        action, confidence, pct = "SELL", 0.7, 0.05
    else:
        action, confidence, pct = "HOLD", 0.5, 0.0
    target_price, stop_loss = _mock_targets(action, market.price)
    reasoning = f"RSI {market.rsi:.0f} at price {market.price:.2f} -> {action}."
    if chart_image:
        reasoning += " Chart image reviewed (offline: levels approximated from RSI)."
    return AnalystDecision(
        action=action,
        symbol=market.symbol,
        reasoning=reasoning,
        confidence=confidence,
        suggested_pct=pct,
        target_price=target_price,
        stop_loss=stop_loss,
    )


def _mock_targets(action: str, price: float) -> tuple[float | None, float | None]:
    """Deterministic target / stop-loss for the offline analyst (None on HOLD)."""
    if action == "BUY":
        return round(price * 1.10, 2), round(price * 0.95, 2)
    if action == "SELL":
        return round(price * 0.90, 2), round(price * 1.05, 2)
    return None, None


def _mock_risk_note(market: MarketData, decision: AnalystDecision) -> str:
    return (
        f"Mock risk note: {decision.action} {market.symbol} with RSI "
        f"{market.rsi:.0f}; size looks within normal bounds."
    )


def _llm_analyze(
    market: MarketData,
    portfolio: PortfolioSnapshot,
    chart_image: Optional[str] = None,
) -> AnalystDecision:  # pragma: no cover
    from langchain_openai import ChatOpenAI

    structured = ChatOpenAI(model="gpt-4o-mini", temperature=0).with_structured_output(
        AnalystDecision
    )
    system = ANALYST_SYSTEM + (ANALYST_VISION_HINT if chart_image else "")
    text = (
        f"{system}\n\n"
        f"Symbol: {market.symbol}\nPrice: {market.price}\nRSI: {market.rsi}\n"
        f"Headlines: {market.headlines}\n"
        f"Cash: {portfolio.cash_balance}\nPortfolio value: {portfolio.total_value}"
    )
    if chart_image:
        content = [
            {"type": "text", "text": text},
            {"type": "image_url", "image_url": {"url": chart_image}},
        ]
        return structured.invoke([{"role": "user", "content": content}])
    return structured.invoke(text)


def _llm_risk_note(
    market: MarketData, decision: AnalystDecision
) -> str:  # pragma: no cover
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    prompt = (
        f"{RISK_SYSTEM}\n\nProposed: {decision.action} {market.symbol} "
        f"({decision.suggested_pct:.0%}). RSI {market.rsi:.0f}."
    )
    return llm.invoke(prompt).content
