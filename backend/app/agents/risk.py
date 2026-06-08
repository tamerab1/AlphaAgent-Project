"""Risk policy: deterministic position-sizing and approval rules.

Kept separate from the LangGraph node so the policy can be unit-tested and
reused without spinning up the graph.
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
    if analyst.action == "HOLD":
        return RiskDecision(
            approved=False,
            reason="Analyst recommends HOLD; no trade.",
            adjusted_pct=0.0,
        )

    note = llm.risk_note(market, analyst)

    if analyst.action == "BUY":
        adjusted = min(analyst.suggested_pct, MAX_POSITION_PCT)
        trade_value = adjusted * portfolio.total_value
        if trade_value > portfolio.cash_balance:
            return RiskDecision(
                approved=False,
                reason=f"Insufficient cash for trade. {note}",
                adjusted_pct=0.0,
            )
        new_exposure = portfolio.symbol_exposure + trade_value
        if new_exposure > MAX_POSITION_PCT * portfolio.total_value:
            return RiskDecision(
                approved=False,
                reason=f"Position would exceed 5% cap. {note}",
                adjusted_pct=0.0,
            )
        return RiskDecision(
            approved=True,
            reason=f"Within cash and 5% position limit. {note}",
            adjusted_pct=adjusted,
        )

    # SELL
    if portfolio.symbol_exposure <= 0:
        return RiskDecision(
            approved=False,
            reason=f"No position to sell. {note}",
            adjusted_pct=0.0,
        )
    return RiskDecision(
        approved=True,
        reason=f"Sell approved. {note}",
        adjusted_pct=min(analyst.suggested_pct, 1.0),
    )
