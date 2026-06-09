from app.schemas.agent import AgentState, MarketData, PortfolioSnapshot
from app.services import market_data


def ingest_node(state: AgentState) -> AgentState:
    symbol = state["symbol"]
    market = state.get("market") or market_data.get_market_data(symbol)
    market = _enrich(symbol, market)
    portfolio = state.get("portfolio") or _default_portfolio()
    log = state.get("log", [])
    log.append(
        f"ingest: {symbol} price={market.price:.2f} rsi={market.rsi:.0f} "
        f"macd={market.macd_signal or 'n/a'}"
    )
    return {"market": market, "portfolio": portfolio, "log": log}


def _enrich(symbol: str, market: MarketData) -> MarketData:
    """Augment base market data with technical indicators from asset detail.

    Detail computes MACD, 50/200-day moving averages and support/resistance from
    the price series (available even offline via the synthetic seed series). This
    is best-effort: on any failure the unmodified market data is returned so the
    graph never breaks on a transient data issue.
    """
    try:
        detail = market_data.get_asset_detail(symbol)
    except Exception:
        return market
    return market.model_copy(
        update={
            "macd_signal": detail.get("macd_signal"),
            "ma50": detail.get("ma50"),
            "ma200": detail.get("ma200"),
            "support": detail.get("support"),
            "resistance": detail.get("resistance"),
            "change_24h": detail.get("change_24h"),
        }
    )


def _default_portfolio() -> PortfolioSnapshot:
    return PortfolioSnapshot(
        cash_balance=10000.0, total_value=100000.0, symbol_exposure=0.0
    )
