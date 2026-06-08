from app.core.config import settings
from app.schemas.agent import MarketData

RSI_PERIOD = 14


def get_market_data(symbol: str) -> MarketData:
    """Price + RSI + headlines for a symbol.

    Returns deterministic seed data by default so the demo never depends on a
    live API. When ``MARKET_DATA_LIVE`` is set, fetches live price/RSI
    (yfinance) and headlines (Tavily), falling back to seed values per-field
    on any failure.
    """
    seed = _seed_market_data(symbol)
    if not settings.market_data_live:
        return seed
    return _live_market_data(symbol, seed)  # pragma: no cover


def _compute_rsi(closes: list[float], period: int = RSI_PERIOD) -> float:
    """Wilder's RSI over a list of closing prices."""
    if len(closes) <= period:
        return 50.0
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_gain == 0 and avg_loss == 0:
        return 50.0
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _seed_market_data(symbol: str) -> MarketData:
    seed = sum(ord(c) for c in symbol)
    return MarketData(
        symbol=symbol,
        price=round(50.0 + (seed % 200), 2),
        rsi=float(20 + (seed % 60)),
        headlines=[
            f"{symbol} in focus as traders weigh momentum",
            f"Analysts revisit {symbol} on shifting sentiment",
        ],
    )


def _live_market_data(symbol: str, seed: MarketData) -> MarketData:  # pragma: no cover
    try:
        price, rsi = _yfinance_price_rsi(symbol)
    except Exception:
        price, rsi = seed.price, seed.rsi
    try:
        headlines = _tavily_headlines(symbol) or seed.headlines
    except Exception:
        headlines = seed.headlines
    return MarketData(symbol=symbol, price=price, rsi=rsi, headlines=headlines)


def _yfinance_price_rsi(symbol: str) -> tuple[float, float]:  # pragma: no cover
    import yfinance as yf

    closes = yf.Ticker(symbol).history(period="3mo")["Close"].dropna().tolist()
    if not closes:
        raise ValueError(f"No price history for {symbol}")
    return float(closes[-1]), _compute_rsi(closes)


def _tavily_headlines(symbol: str, limit: int = 3) -> list[str]:  # pragma: no cover
    from tavily import TavilyClient

    client = TavilyClient(api_key=settings.tavily_api_key)
    resp = client.search(query=f"{symbol} stock news", topic="news", max_results=limit)
    return [r["title"] for r in resp.get("results", [])][:limit]
