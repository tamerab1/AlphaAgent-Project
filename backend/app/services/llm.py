import os
from typing import Optional

from app.schemas.agent import (
    AnalystDecision,
    ChartReading,
    MarketData,
    PortfolioSnapshot,
    SentimentResult,
)

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

CHART_READER_SYSTEM = (
    "You are a technical chart analyst. Read the attached trading chart screenshot "
    "and identify the key support and resistance price levels, any notable "
    "candlestick or chart patterns, and an overall directional bias "
    "(bullish, bearish, or neutral). Be concise and specific."
)

RISK_SYSTEM = (
    "You are a risk manager. In one or two sentences give a brief sanity note on "
    "the proposed trade. Do not approve or reject; just flag anything notable."
)


NEWS_SENTIMENT_SYSTEM = (
    "You are a financial news sentiment analyst. Given a news headline and the "
    "asset it relates to, classify the market sentiment as 'bullish', 'bearish', "
    "or 'neutral'. Write a single sentence summarising the key market implication."
)

_BULLISH_WORDS = {
    "surge",
    "record",
    "beat",
    "rise",
    "gain",
    "bullish",
    "upgrade",
    "breakout",
    "high",
    "growth",
    "rally",
    "strong",
    "buy",
    "partnership",
    "launch",
    "invest",
    "milestone",
    "approval",
    "soar",
    "jump",
    "inflow",
    "adoption",
}
_BEARISH_WORDS = {
    "probe",
    "warning",
    "cut",
    "loss",
    "decline",
    "crash",
    "sell",
    "downgrade",
    "risk",
    "concern",
    "fail",
    "fall",
    "drop",
    "weak",
    "antitrust",
    "ban",
    "fine",
    "lawsuit",
    "outflow",
    "halt",
    "suspend",
    "fraud",
    "breach",
}


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


def analyze_headline_sentiment(headline: str, symbol: str) -> SentimentResult:
    """Classify a news headline as bullish / bearish / neutral (mock when offline)."""
    if _has_api_key():
        return _llm_sentiment(headline, symbol)  # pragma: no cover
    return _mock_sentiment(headline, symbol)


def read_chart(chart_image: str, symbol: Optional[str] = None) -> ChartReading:
    """Visual read of a chart screenshot via gpt-4o-mini vision (mock offline)."""
    if _has_api_key():
        return _llm_read_chart(chart_image, symbol)  # pragma: no cover
    return _mock_read_chart(symbol)


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


def _mock_sentiment(headline: str, symbol: str) -> SentimentResult:
    h = headline.lower()
    score = sum(1 for w in _BULLISH_WORDS if w in h) - sum(
        1 for w in _BEARISH_WORDS if w in h
    )
    if score > 0:
        return SentimentResult(
            sentiment="bullish",
            summary=f"Positive catalyst detected for {symbol}; momentum may accelerate.",
        )
    if score < 0:
        return SentimentResult(
            sentiment="bearish",
            summary=f"Negative pressure on {symbol}; watch for increased volatility.",
        )
    return SentimentResult(
        sentiment="neutral",
        summary=f"Informational update on {symbol}; no immediate directional bias.",
    )


def _llm_sentiment(headline: str, symbol: str) -> SentimentResult:  # pragma: no cover
    from langchain_openai import ChatOpenAI

    structured = ChatOpenAI(model="gpt-4o-mini", temperature=0).with_structured_output(
        SentimentResult
    )
    prompt = f"{NEWS_SENTIMENT_SYSTEM}\n\nSymbol: {symbol}\nHeadline: {headline}"
    return structured.invoke(prompt)


def _mock_read_chart(symbol: Optional[str]) -> ChartReading:
    label = symbol or "the chart"
    return ChartReading(
        summary=(
            f"Offline mode: connect an OPENAI_API_KEY to read {label} visually. "
            "Showing a placeholder; no image was analyzed."
        ),
        support_levels=[],
        resistance_levels=[],
        patterns=[],
        bias="neutral",
    )


def _llm_read_chart(
    chart_image: str, symbol: Optional[str]
) -> ChartReading:  # pragma: no cover
    from langchain_openai import ChatOpenAI

    structured = ChatOpenAI(model="gpt-4o-mini", temperature=0).with_structured_output(
        ChartReading
    )
    text = CHART_READER_SYSTEM + (f"\nSymbol: {symbol}" if symbol else "")
    content = [
        {"type": "text", "text": text},
        {"type": "image_url", "image_url": {"url": chart_image}},
    ]
    return structured.invoke([{"role": "user", "content": content}])
