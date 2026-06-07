import os

from ai.schemas import AnalystDecision, MarketData, PortfolioSnapshot

ANALYST_SYSTEM = (
    "You are a disciplined trading analyst. Given market data and the current "
    "portfolio, decide whether to BUY, SELL, or HOLD the symbol. Be conservative "
    "and explain your reasoning briefly."
)

RISK_SYSTEM = (
    "You are a risk manager. In one or two sentences give a brief sanity note on "
    "the proposed trade. Do not approve or reject; just flag anything notable."
)


def _has_api_key() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def analyze(market: MarketData, portfolio: PortfolioSnapshot) -> AnalystDecision:
    """Analyst decision, using gpt-4o-mini when a key is set, else a mock."""
    if _has_api_key():
        return _llm_analyze(market, portfolio)  # pragma: no cover
    return _mock_analyze(market)


def risk_note(market: MarketData, decision: AnalystDecision) -> str:
    """Short LLM sanity note on the proposed trade (mocked when offline)."""
    if _has_api_key():
        return _llm_risk_note(market, decision)  # pragma: no cover
    return _mock_risk_note(market, decision)


def _mock_analyze(market: MarketData) -> AnalystDecision:
    if market.rsi < 30:
        action, confidence, pct = "BUY", 0.7, 0.05
    elif market.rsi > 70:
        action, confidence, pct = "SELL", 0.7, 0.05
    else:
        action, confidence, pct = "HOLD", 0.5, 0.0
    return AnalystDecision(
        action=action,
        symbol=market.symbol,
        reasoning=f"RSI {market.rsi:.0f} at price {market.price:.2f} -> {action}.",
        confidence=confidence,
        suggested_pct=pct,
    )


def _mock_risk_note(market: MarketData, decision: AnalystDecision) -> str:
    return (
        f"Mock risk note: {decision.action} {market.symbol} with RSI "
        f"{market.rsi:.0f}; size looks within normal bounds."
    )


def _llm_analyze(
    market: MarketData, portfolio: PortfolioSnapshot
) -> AnalystDecision:  # pragma: no cover
    from langchain_openai import ChatOpenAI

    structured = ChatOpenAI(model="gpt-4o-mini", temperature=0).with_structured_output(
        AnalystDecision
    )
    prompt = (
        f"{ANALYST_SYSTEM}\n\n"
        f"Symbol: {market.symbol}\nPrice: {market.price}\nRSI: {market.rsi}\n"
        f"Headlines: {market.headlines}\n"
        f"Cash: {portfolio.cash_balance}\nPortfolio value: {portfolio.total_value}"
    )
    return structured.invoke(prompt)


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
