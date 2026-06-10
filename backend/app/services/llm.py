from typing import Optional

from app.core.config import settings
from app.schemas.agent import (
    AnalystDecision,
    ChartReading,
    DebateArgument,
    MarketData,
    PortfolioSnapshot,
    RiskDecision,
    SentimentResult,
)

ANALYST_SYSTEM = (
    "You are a disciplined trading analyst. Given market data — price, RSI, MACD "
    "signal, 50/200-day moving averages, support/resistance, recent price change "
    "and news headlines — plus the current portfolio, decide whether to BUY, "
    "SELL, or HOLD the symbol. Weigh the technical signals together (RSI extremes, "
    "price vs. moving averages, MACD direction, proximity to support/resistance) "
    "rather than relying on any single indicator. Be conservative and explain your "
    "reasoning briefly, citing the specific signals that drove the call. When "
    "recommending a BUY or SELL, anchor a realistic target_price and stop_loss to "
    "the support/resistance levels; leave both null for HOLD."
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

RISK_MANAGER_SYSTEM = (
    "You are the risk manager on a trading desk. Decide whether to APPROVE the "
    "proposed trade and at what size (adjusted_pct, a fraction of the total book). "
    "Weigh the analyst's conviction against the technicals and the current exposure. "
    "Approve only when the risk/reward justifies it; otherwise reject. You may size "
    "the position DOWN from the stated cap but must NEVER exceed it. Give a concise "
    "one-sentence reason."
)

BULL_SYSTEM = (
    "You are the BULL — a trading analyst arguing the strongest evidence-based case "
    "to BUY this symbol. Cite the specific technicals (RSI, MACD, moving averages, "
    "support/resistance) and any positive headlines. Give a concise thesis, 2-4 key "
    "points, and your conviction from 0 to 1. Be persuasive but honest; never invent "
    "data."
)

BEAR_SYSTEM = (
    "You are the BEAR — a trading analyst arguing the strongest evidence-based case "
    "to SELL or avoid this symbol. Cite the specific technicals (RSI, MACD, moving "
    "averages, support/resistance) and any negative headlines. Give a concise thesis, "
    "2-4 key points, and your conviction from 0 to 1. Be persuasive but honest; never "
    "invent data."
)

JUDGE_SYSTEM = (
    "You are the JUDGE — the head of the trading desk. You are given a BULL case and a "
    "BEAR case for the symbol, plus the market data and current portfolio. Weigh both "
    "sides objectively against the technicals and decide BUY, SELL, or HOLD. In your "
    "reasoning, state which arguments were decisive and why. Be conservative. When "
    "recommending BUY or SELL, anchor a realistic target_price and stop_loss to the "
    "support/resistance levels; leave both null for HOLD."
)


NEWS_SENTIMENT_SYSTEM = (
    "You are a financial news sentiment analyst. Given a news headline and the "
    "asset it relates to:\n"
    "1. Classify sentiment as 'bullish', 'bearish', or 'neutral'.\n"
    "2. 'summary': one concise sentence stating the key market implication.\n"
    "3. 'sentiment_breakdown': 2-3 sentences explaining specifically WHY this "
    "headline is bullish/bearish/neutral for this particular asset — name the "
    "market mechanism (e.g. demand/supply shift, regulatory impact, adoption "
    "catalyst, macro headwind)."
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
    # Source the key from pydantic settings (loaded from .env) rather than
    # os.environ, which BaseSettings does not populate. This is what makes the
    # LLM path fire regardless of how the process was launched.
    return bool(settings.openai_api_key)


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


def debate_bull(market: MarketData, portfolio: PortfolioSnapshot) -> DebateArgument:
    """Bullish case for the symbol (gpt-4o-mini when keyed, else a mock)."""
    if _has_api_key():
        return _llm_debate(market, portfolio, "bull")  # pragma: no cover
    return _mock_debate(market, "bull")


def debate_bear(market: MarketData, portfolio: PortfolioSnapshot) -> DebateArgument:
    """Bearish case for the symbol (gpt-4o-mini when keyed, else a mock)."""
    if _has_api_key():
        return _llm_debate(market, portfolio, "bear")  # pragma: no cover
    return _mock_debate(market, "bear")


def judge(
    market: MarketData,
    portfolio: PortfolioSnapshot,
    bull: DebateArgument,
    bear: DebateArgument,
    chart_image: Optional[str] = None,
) -> AnalystDecision:
    """Final BUY/SELL/HOLD weighing the bull vs bear cases (mock when offline)."""
    if _has_api_key():
        return _llm_judge(
            market, portfolio, bull, bear, chart_image
        )  # pragma: no cover
    return _mock_judge(market, bull, bear, chart_image)


def assess_risk_llm(
    market: MarketData,
    analyst: AnalystDecision,
    portfolio: PortfolioSnapshot,
    max_pct: float,
) -> RiskDecision:
    """Risk manager's structured judgment within an allowed size envelope.

    Offline, echoes the deterministic envelope (approve at the cap). With a key,
    the LLM may veto or size the position down — never above ``max_pct``.
    """
    if _has_api_key():
        return _llm_assess_risk(market, analyst, portfolio, max_pct)  # pragma: no cover
    return RiskDecision(
        approved=True,
        reason=f"Within risk limits (size {max_pct:.0%} of book).",
        adjusted_pct=max_pct,
    )


def _mock_analyze(
    market: MarketData, chart_image: Optional[str] = None
) -> AnalystDecision:
    if market.rsi < 30:
        action, confidence, pct = "BUY", 0.7, 0.05
    elif market.rsi > 70:
        action, confidence, pct = "SELL", 0.7, 0.05
    else:
        action, confidence, pct = "HOLD", 0.5, 0.0
    # Don't fight the trend: if MACD contradicts the RSI mean-reversion call,
    # downgrade to HOLD so the read stays coherent with the indicators shown.
    if action == "BUY" and market.macd_signal == "bearish":
        action, confidence, pct = "HOLD", 0.5, 0.0
    elif action == "SELL" and market.macd_signal == "bullish":
        action, confidence, pct = "HOLD", 0.5, 0.0
    target_price, stop_loss = _mock_targets(action, market.price)
    bits = [f"RSI {market.rsi:.0f}"]
    if market.macd_signal:
        bits.append(f"MACD {market.macd_signal}")
    reasoning = f"{', '.join(bits)} at price {market.price:.2f} -> {action}."
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


def _format_technicals(market: MarketData) -> str:
    """Render the optional technical fields as prompt lines (skip missing ones)."""
    lines: list[str] = []
    if market.macd_signal is not None:
        lines.append(f"MACD signal: {market.macd_signal}")
    if market.ma50 is not None and market.ma200 is not None:
        trend = "above" if market.price >= market.ma50 else "below"
        lines.append(f"MA50: {market.ma50}  MA200: {market.ma200} (price {trend} MA50)")
    if market.support is not None and market.resistance is not None:
        lines.append(f"Support: {market.support}  Resistance: {market.resistance}")
    if market.change_24h is not None:
        lines.append(f"24h change: {market.change_24h}%")
    return "\n".join(lines)


def _llm_analyze(
    market: MarketData,
    portfolio: PortfolioSnapshot,
    chart_image: Optional[str] = None,
) -> AnalystDecision:  # pragma: no cover
    from langchain_openai import ChatOpenAI

    structured = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=settings.openai_api_key,
        timeout=8.0,
    ).with_structured_output(AnalystDecision)
    system = ANALYST_SYSTEM + (ANALYST_VISION_HINT if chart_image else "")
    technicals = _format_technicals(market)
    text = (
        f"{system}\n\n"
        f"Symbol: {market.symbol}\nPrice: {market.price}\nRSI: {market.rsi}\n"
        f"{technicals}\n"
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

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=settings.openai_api_key,
        timeout=8.0,
    )
    prompt = (
        f"{RISK_SYSTEM}\n\nProposed: {decision.action} {market.symbol} "
        f"({decision.suggested_pct:.0%}). RSI {market.rsi:.0f}."
    )
    return llm.invoke(prompt).content


def _mock_debate(market: MarketData, stance: str) -> DebateArgument:
    if stance == "bull":
        return DebateArgument(
            stance="bull",
            thesis=(
                f"{market.symbol} is attractively priced at {market.price:.2f}; "
                f"RSI {market.rsi:.0f} leaves room to the upside."
            ),
            key_points=[
                f"RSI {market.rsi:.0f}" + (" (oversold)" if market.rsi < 35 else ""),
                f"MACD {market.macd_signal or 'n/a'}",
                f"Support near {market.support if market.support is not None else 'n/a'}",
            ],
            conviction=0.6,
        )
    return DebateArgument(
        stance="bear",
        thesis=(
            f"{market.symbol} faces headwinds at {market.price:.2f}; momentum looks "
            f"unconvincing (MACD {market.macd_signal or 'n/a'})."
        ),
        key_points=[
            f"MACD {market.macd_signal or 'n/a'}",
            f"Resistance near {market.resistance if market.resistance is not None else 'n/a'}",
            f"RSI {market.rsi:.0f}" + (" (overbought)" if market.rsi > 65 else ""),
        ],
        conviction=0.55,
    )


def _mock_judge(
    market: MarketData,
    bull: DebateArgument,
    bear: DebateArgument,
    chart_image: Optional[str] = None,
) -> AnalystDecision:
    decision = _mock_analyze(market, chart_image)
    decision.reasoning = (
        f"Judge weighed bull (conv {bull.conviction:.0%}) vs bear "
        f"(conv {bear.conviction:.0%}). " + decision.reasoning
    )
    return decision


def _llm_debate(
    market: MarketData, portfolio: PortfolioSnapshot, stance: str
) -> DebateArgument:  # pragma: no cover
    from langchain_openai import ChatOpenAI

    structured = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.3,
        api_key=settings.openai_api_key,
        timeout=8.0,
    ).with_structured_output(DebateArgument)
    system = BULL_SYSTEM if stance == "bull" else BEAR_SYSTEM
    text = (
        f"{system}\n\n"
        f"Symbol: {market.symbol}\nPrice: {market.price}\nRSI: {market.rsi}\n"
        f"{_format_technicals(market)}\n"
        f"Headlines: {market.headlines}\n"
        f"Cash: {portfolio.cash_balance}\nPortfolio value: {portfolio.total_value}"
    )
    arg = structured.invoke(text)
    # Pin the stance so a mislabelled structured output can't flip sides.
    return arg.model_copy(update={"stance": stance})


def _llm_judge(
    market: MarketData,
    portfolio: PortfolioSnapshot,
    bull: DebateArgument,
    bear: DebateArgument,
    chart_image: Optional[str] = None,
) -> AnalystDecision:  # pragma: no cover
    from langchain_openai import ChatOpenAI

    structured = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=settings.openai_api_key,
        timeout=8.0,
    ).with_structured_output(AnalystDecision)
    system = JUDGE_SYSTEM + (ANALYST_VISION_HINT if chart_image else "")
    text = (
        f"{system}\n\n"
        f"Symbol: {market.symbol}\nPrice: {market.price}\nRSI: {market.rsi}\n"
        f"{_format_technicals(market)}\n"
        f"Headlines: {market.headlines}\n"
        f"Cash: {portfolio.cash_balance}\nPortfolio value: {portfolio.total_value}\n\n"
        f"BULL CASE (conviction {bull.conviction:.0%}): {bull.thesis}\n"
        f"Bull points: {bull.key_points}\n"
        f"BEAR CASE (conviction {bear.conviction:.0%}): {bear.thesis}\n"
        f"Bear points: {bear.key_points}"
    )
    if chart_image:
        content = [
            {"type": "text", "text": text},
            {"type": "image_url", "image_url": {"url": chart_image}},
        ]
        return structured.invoke([{"role": "user", "content": content}])
    return structured.invoke(text)


def _llm_assess_risk(
    market: MarketData,
    analyst: AnalystDecision,
    portfolio: PortfolioSnapshot,
    max_pct: float,
) -> RiskDecision:  # pragma: no cover
    from langchain_openai import ChatOpenAI

    structured = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=settings.openai_api_key,
        timeout=8.0,
    ).with_structured_output(RiskDecision)
    text = (
        f"{RISK_MANAGER_SYSTEM}\n\n"
        f"Proposed: {analyst.action} {market.symbol} at {market.price} "
        f"(analyst confidence {analyst.confidence:.0%}, target {analyst.target_price}, "
        f"stop {analyst.stop_loss}).\n"
        f"Technicals — RSI {market.rsi}, MACD {market.macd_signal}, "
        f"MA50 {market.ma50}, MA200 {market.ma200}, support {market.support}, "
        f"resistance {market.resistance}.\n"
        f"Portfolio — cash {portfolio.cash_balance}, total {portfolio.total_value}, "
        f"current {market.symbol} exposure {portfolio.symbol_exposure}.\n"
        f"HARD CAP: adjusted_pct must not exceed {max_pct:.4f}. Approve at or below "
        f"this, size down, or reject — never exceed it."
    )
    result = structured.invoke(text)
    # Enforce the hard cap no matter what the model returns.
    return result.model_copy(update={"adjusted_pct": min(result.adjusted_pct, max_pct)})


def _mock_sentiment(headline: str, symbol: str) -> SentimentResult:
    h = headline.lower()
    score = sum(1 for w in _BULLISH_WORDS if w in h) - sum(
        1 for w in _BEARISH_WORDS if w in h
    )
    if score > 0:
        return SentimentResult(
            sentiment="bullish",
            summary=(
                f"Positive catalyst detected for {symbol}; momentum may accelerate."
            ),
            sentiment_breakdown=(
                f"Bullish for {symbol}: the headline signals increased demand or "
                f"adoption — typically a precursor to upward price pressure as "
                f"buyers accumulate ahead of the catalyst. Positive news cycles "
                f"for {symbol} historically compress the bid-ask spread and "
                f"attract fresh capital into the asset."
            ),
        )
    if score < 0:
        return SentimentResult(
            sentiment="bearish",
            summary=(f"Negative pressure on {symbol}; watch for increased volatility."),
            sentiment_breakdown=(
                f"Bearish for {symbol}: the headline introduces uncertainty or "
                f"downside risk that may trigger defensive selling. Negative "
                f"catalysts — particularly regulatory or macro ones — tend to "
                f"reduce risk appetite across the board, with {symbol} facing "
                f"elevated short-term sell pressure until the issue resolves."
            ),
        )
    return SentimentResult(
        sentiment="neutral",
        summary=(f"Informational update on {symbol}; no immediate directional bias."),
        sentiment_breakdown=(
            f"Neutral for {symbol}: the headline is informational rather than "
            f"directional — it contains neither strong positive nor negative "
            f"signals for price action. Market participants are likely to "
            f"acknowledge the update without materially changing their {symbol} "
            f"exposure in the short term."
        ),
    )


def _llm_sentiment(headline: str, symbol: str) -> SentimentResult:  # pragma: no cover
    from langchain_openai import ChatOpenAI

    structured = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=settings.openai_api_key,
        timeout=8.0,
    ).with_structured_output(SentimentResult)
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

    structured = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=settings.openai_api_key,
        timeout=8.0,
    ).with_structured_output(ChartReading)
    text = CHART_READER_SYSTEM + (f"\nSymbol: {symbol}" if symbol else "")
    content = [
        {"type": "text", "text": text},
        {"type": "image_url", "image_url": {"url": chart_image}},
    ]
    return structured.invoke([{"role": "user", "content": content}])
