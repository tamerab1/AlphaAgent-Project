import logging

from app.core.config import settings
from app.schemas.agent import MarketData

logger = logging.getLogger("alphaagent")

RSI_PERIOD = 14


def get_market_data(symbol: str) -> MarketData:
    """Price + RSI + headlines for a symbol.

    Returns deterministic seed data by default so the demo never depends on a
    live API. When ``MARKET_DATA_LIVE`` is set, fetches live price/RSI
    (Twelve Data, then Stooq) and headlines (Tavily), falling back to seed
    values per-field on any failure.
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


# Symbols Twelve Data quotes as crypto pairs (e.g. BTC/USD) rather than tickers.
CRYPTO_SYMBOLS = {"BTC", "ETH", "SOL", "DOGE", "ADA", "XRP", "BNB", "LTC"}


def _live_market_data(symbol: str, seed: MarketData) -> MarketData:  # pragma: no cover
    price, rsi, source = seed.price, seed.rsi, "seed"
    for name, fetch in (
        ("twelvedata", _twelvedata_price_rsi),
        ("stooq", _stooq_price_rsi),
    ):
        try:
            price, rsi = fetch(symbol)
            source = name
            break
        except Exception as exc:
            logger.warning("live price via %s failed for %s: %s", name, symbol, exc)
    logger.info(
        "live market data %s: price=%.2f rsi=%.0f (source=%s)",
        symbol,
        price,
        rsi,
        source,
    )
    try:
        headlines = _tavily_headlines(symbol) or seed.headlines
        logger.info("live headlines for %s: %d via tavily", symbol, len(headlines))
    except Exception as exc:
        logger.warning("tavily failed for %s: %s", symbol, exc)
        headlines = seed.headlines
    return MarketData(symbol=symbol, price=price, rsi=rsi, headlines=headlines)


def _twelvedata_price_rsi(symbol: str) -> tuple[float, float]:  # pragma: no cover
    """Daily price + RSI from Twelve Data (free API key; stocks and crypto)."""
    if not settings.twelve_data_api_key:
        raise ValueError("TWELVE_DATA_API_KEY not set")
    import httpx

    td_symbol = f"{symbol}/USD" if symbol.upper() in CRYPTO_SYMBOLS else symbol
    resp = httpx.get(
        "https://api.twelvedata.com/time_series",
        params={
            "symbol": td_symbol,
            "interval": "1day",
            "outputsize": 30,
            "apikey": settings.twelve_data_api_key,
        },
        timeout=8.0,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") == "error" or "values" not in data:
        raise ValueError(data.get("message", "Twelve Data error"))
    # API returns newest-first; reverse to oldest -> newest for RSI.
    closes = [float(v["close"]) for v in reversed(data["values"]) if v.get("close")]
    if not closes:
        raise ValueError(f"no closes for {symbol}")
    return closes[-1], _compute_rsi(closes)


def _stooq_price_rsi(symbol: str) -> tuple[float, float]:  # pragma: no cover
    """Daily price + RSI from Stooq's free CSV endpoint (no API key)."""
    import httpx

    url = f"https://stooq.com/q/d/l/?s={symbol.lower()}.us&i=d"
    resp = httpx.get(url, timeout=8.0, follow_redirects=True)
    resp.raise_for_status()
    rows = resp.text.strip().splitlines()
    if len(rows) < 2 or rows[0].lower().startswith("<"):
        raise ValueError(f"no Stooq data for {symbol}")
    # CSV columns: Date,Open,High,Low,Close,Volume
    closes = [
        float(parts[4])
        for parts in (r.split(",") for r in rows[1:])
        if len(parts) >= 5 and parts[4] not in ("", "N/D")
    ]
    if not closes:
        raise ValueError(f"no closes for {symbol}")
    return float(closes[-1]), _compute_rsi(closes)


def _tavily_headlines(symbol: str, limit: int = 3) -> list[str]:  # pragma: no cover
    from tavily import TavilyClient

    client = TavilyClient(api_key=settings.tavily_api_key)
    resp = client.search(query=f"{symbol} stock news", topic="news", max_results=limit)
    return [r["title"] for r in resp.get("results", [])][:limit]
