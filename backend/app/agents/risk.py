"""Risk policy: deterministic guardrails + an LLM risk-manager judgment.

The deterministic guardrails (HOLD = no trade, sufficient cash, the 5% position
cap, SELL needs a position) are HARD and non-overridable — they can only veto or
bound a trade, never loosen it. When they allow a trade, the LLM risk manager
adds judgment within that envelope: it may approve, reject, or size the position
down, but can never exceed the cap. Kept separate from the LangGraph node so the
policy can be unit-tested without spinning up the graph.
"""

from app.schemas.agent import (
    AnalystDecision,
    MarketData,
    PortfolioSnapshot,
    RiskDecision,
)
from app.services import llm

MAX_POSITION_PCT = 0.05


def assess_risk(
    analyst: AnalystDecision,
    portfolio: PortfolioSnapshot,
    market: MarketData,
) -> RiskDecision:
    # 1. Deterministic hard guardrails — authoritative.
    hard = _hard_limits(analyst, portfolio)
    if not hard.approved:
        return hard

    # 2. LLM risk manager judges within the allowed size envelope.
    view = llm.assess_risk_llm(market, analyst, portfolio, hard.adjusted_pct)
    if not view.approved:
        return RiskDecision(
            approved=False,
            reason=view.reason or "Risk manager vetoed the trade.",
            adjusted_pct=0.0,
        )
    adjusted = min(view.adjusted_pct, hard.adjusted_pct)  # cap is non-negotiable
    if adjusted <= 0:
        return RiskDecision(
            approved=False,
            reason=view.reason or "Risk manager sized the position to zero.",
            adjusted_pct=0.0,
        )
    return RiskDecision(
        approved=True,
        reason=view.reason or hard.reason,
        adjusted_pct=adjusted,
    )


def _hard_limits(
    analyst: AnalystDecision,
    portfolio: PortfolioSnapshot,
) -> RiskDecision:
    """Deterministic gate. Returns the maximum allowed size, or a hard rejection."""
    if analyst.action == "HOLD":
        return RiskDecision(
            approved=False,
            reason="Analyst recommends HOLD; no trade.",
            adjusted_pct=0.0,
        )

    if analyst.action == "BUY":
        adjusted = min(analyst.suggested_pct, MAX_POSITION_PCT)
        trade_value = adjusted * portfolio.total_value
        if trade_value > portfolio.cash_balance:
            return RiskDecision(
                approved=False,
                reason="Insufficient cash for trade.",
                adjusted_pct=0.0,
            )
        new_exposure = portfolio.symbol_exposure + trade_value
        if new_exposure > MAX_POSITION_PCT * portfolio.total_value:
            return RiskDecision(
                approved=False,
                reason="Position would exceed 5% cap.",
                adjusted_pct=0.0,
            )
        return RiskDecision(
            approved=True,
            reason="Within cash and 5% position limit.",
            adjusted_pct=adjusted,
        )

    # SELL
    if portfolio.symbol_exposure <= 0:
        return RiskDecision(
            approved=False,
            reason="No position to sell.",
            adjusted_pct=0.0,
        )
    return RiskDecision(
        approved=True,
        reason="Sell approved.",
        adjusted_pct=min(analyst.suggested_pct, 1.0),
    )
