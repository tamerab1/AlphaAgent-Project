from app.schemas.agent import AgentState, PortfolioSnapshot
from app.services import market_data


def ingest_node(state: AgentState) -> AgentState:
    symbol = state["symbol"]
    market = state.get("market") or market_data.get_market_data(symbol)
    portfolio = state.get("portfolio") or _default_portfolio()
    log = state.get("log", [])
    log.append(f"ingest: {symbol} price={market.price:.2f} rsi={market.rsi:.0f}")
    return {"market": market, "portfolio": portfolio, "log": log}


def _default_portfolio() -> PortfolioSnapshot:
    return PortfolioSnapshot(
        cash_balance=10000.0, total_value=100000.0, symbol_exposure=0.0
    )
