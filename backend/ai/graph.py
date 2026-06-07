from langgraph.graph import END, StateGraph

from ai import llm
from ai.schemas import (
    AgentState,
    AnalystDecision,
    MarketData,
    PortfolioSnapshot,
    RiskDecision,
)

MAX_POSITION_PCT = 0.05


def ingest_node(state: AgentState) -> AgentState:
    symbol = state["symbol"]
    market = state.get("market") or _mock_market(symbol)
    portfolio = state.get("portfolio") or _default_portfolio()
    log = state.get("log", [])
    log.append(f"ingest: {symbol} price={market.price:.2f} rsi={market.rsi:.0f}")
    return {"market": market, "portfolio": portfolio, "log": log}


def analyst_node(state: AgentState) -> AgentState:
    decision = llm.analyze(state["market"], state["portfolio"])
    log = state.get("log", [])
    log.append(f"analyst: {decision.action} ({decision.confidence:.0%})")
    return {"analyst": decision, "log": log}


def risk_node(state: AgentState) -> AgentState:
    decision = _assess_risk(state["analyst"], state["portfolio"], state["market"])
    verdict = "approved" if decision.approved else "rejected"
    log = state.get("log", [])
    log.append(f"risk: {verdict} - {decision.reason}")
    return {"risk": decision, "log": log}


def execute_node(state: AgentState) -> AgentState:
    analyst = state["analyst"]
    log = state.get("log", [])
    log.append(
        f"execute: {analyst.action} {analyst.symbol} "
        f"at {state['risk'].adjusted_pct:.0%}"
    )
    return {"executed": True, "log": log}


def log_rejection_node(state: AgentState) -> AgentState:
    log = state.get("log", [])
    log.append(f"rejected: {state['risk'].reason}")
    return {"executed": False, "log": log}


def _route(state: AgentState) -> str:
    return "execute" if state["risk"].approved else "log_rejection"


def _assess_risk(
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


def _mock_market(symbol: str) -> MarketData:
    seed = sum(ord(c) for c in symbol)
    return MarketData(
        symbol=symbol,
        price=50.0 + (seed % 200),
        rsi=20.0 + (seed % 60),
        headlines=[f"{symbol} in focus"],
    )


def _default_portfolio() -> PortfolioSnapshot:
    return PortfolioSnapshot(
        cash_balance=10000.0, total_value=100000.0, symbol_exposure=0.0
    )


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("ingest", ingest_node)
    graph.add_node("analyst_agent", analyst_node)
    graph.add_node("risk_agent", risk_node)
    graph.add_node("execute", execute_node)
    graph.add_node("log_rejection", log_rejection_node)
    graph.set_entry_point("ingest")
    graph.add_edge("ingest", "analyst_agent")
    graph.add_edge("analyst_agent", "risk_agent")
    graph.add_conditional_edges(
        "risk_agent",
        _route,
        {"execute": "execute", "log_rejection": "log_rejection"},
    )
    graph.add_edge("execute", END)
    graph.add_edge("log_rejection", END)
    return graph.compile()
