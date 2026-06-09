import logging
import math
import time

from app.core.config import settings
from app.schemas.agent import MarketData

logger = logging.getLogger("alphaagent")

RSI_PERIOD = 14

# Short in-memory TTL cache so the many widgets (status, chart, ticker bar) that
# all ask for prices share one upstream call per symbol — critical under the
# free Twelve Data tier (~8 requests/minute).
_PRICE_TTL = 60.0
_cache: dict[str, tuple[float, object]] = {}


def _cache_get(key: str):
    hit = _cache.get(key)
    if hit and (time.monotonic() - hit[0]) < _PRICE_TTL:
        return hit[1]
    return None


def _cache_put(key: str, value: object) -> None:
    _cache[key] = (time.monotonic(), value)


# Friendly names for the assets the demo features; default to the ticker.
ASSET_META = {
    "BTC": ("Bitcoin", "crypto"),
    "ETH": ("Ethereum", "crypto"),
    "SOL": ("Solana", "crypto"),
    "DOGE": ("Dogecoin", "crypto"),
    "AAPL": ("Apple", "stock"),
    "MSFT": ("Microsoft", "stock"),
    "TSLA": ("Tesla", "stock"),
    "NVDA": ("NVIDIA", "stock"),
    "GOOGL": ("Alphabet", "stock"),
    "AMZN": ("Amazon", "stock"),
    "META": ("Meta Platforms", "stock"),
    "SPY": ("S&P 500 ETF", "stock"),
}


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
    key = f"md:{symbol.upper()}"  # pragma: no cover
    cached = _cache_get(key)  # pragma: no cover
    if isinstance(cached, MarketData):  # pragma: no cover
        return cached
    data = _live_market_data(symbol, seed)  # pragma: no cover
    _cache_put(key, data)  # pragma: no cover
    return data  # pragma: no cover


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
    closes, *_ = _twelvedata_series(symbol)
    return closes[-1], _compute_rsi(closes)


def _stooq_price_rsi(symbol: str) -> tuple[float, float]:  # pragma: no cover
    closes, *_ = _stooq_series(symbol)
    return closes[-1], _compute_rsi(closes)


def _twelvedata_series(
    symbol: str,
) -> tuple[list[float], float, float, float]:  # pragma: no cover
    """Daily closes + 24h high/low/volume from Twelve Data (stocks and crypto)."""
    if not settings.twelve_data_api_key:
        raise ValueError("TWELVE_DATA_API_KEY not set")
    import httpx

    td_symbol = f"{symbol}/USD" if symbol.upper() in CRYPTO_SYMBOLS else symbol
    resp = httpx.get(
        "https://api.twelvedata.com/time_series",
        params={
            "symbol": td_symbol,
            "interval": "1day",
            "outputsize": 200,
            "apikey": settings.twelve_data_api_key,
        },
        timeout=8.0,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") == "error" or "values" not in data:
        raise ValueError(data.get("message", "Twelve Data error"))
    values = data["values"]  # newest-first
    closes = [float(v["close"]) for v in reversed(values) if v.get("close")]
    if not closes:
        raise ValueError(f"no closes for {symbol}")
    latest = values[0]
    high = float(latest.get("high") or closes[-1])
    low = float(latest.get("low") or closes[-1])
    volume = float(latest.get("volume") or 0.0)
    return closes, high, low, volume


def _stooq_series(
    symbol: str,
) -> tuple[list[float], float, float, float]:  # pragma: no cover
    """Daily closes + 24h high/low/volume from Stooq's free CSV (no API key)."""
    import httpx

    url = f"https://stooq.com/q/d/l/?s={symbol.lower()}.us&i=d"
    resp = httpx.get(url, timeout=8.0, follow_redirects=True)
    resp.raise_for_status()
    rows = resp.text.strip().splitlines()
    if len(rows) < 2 or rows[0].lower().startswith("<"):
        raise ValueError(f"no Stooq data for {symbol}")
    # CSV columns: Date,Open,High,Low,Close,Volume
    closes: list[float] = []
    last: list[str] = []
    for parts in (r.split(",") for r in rows[1:]):
        if len(parts) >= 5 and parts[4] not in ("", "N/D"):
            closes.append(float(parts[4]))
            last = parts
    if not closes:
        raise ValueError(f"no closes for {symbol}")
    high = float(last[2]) if last[2] not in ("", "N/D") else closes[-1]
    low = float(last[3]) if last[3] not in ("", "N/D") else closes[-1]
    volume = float(last[5]) if len(last) > 5 and last[5] not in ("", "N/D") else 0.0
    return closes, high, low, volume


def _tavily_headlines(symbol: str, limit: int = 3) -> list[str]:  # pragma: no cover
    from tavily import TavilyClient

    client = TavilyClient(api_key=settings.tavily_api_key)
    resp = client.search(query=f"{symbol} stock news", topic="news", max_results=limit)
    return [r["title"] for r in resp.get("results", [])][:limit]


# --- Asset detail (price chart + technical indicators) -----------------------


def get_asset_detail(symbol: str) -> dict:
    """Market data + technical indicators + price history for one asset.

    Used by the dashboard's price chart / AI-analysis widgets. Uses live data
    (Twelve Data, then Stooq) when MARKET_DATA_LIVE is set, else a deterministic
    synthetic series so the chart looks alive offline. AI fields are added by
    the API layer (it owns the LLM call).
    """
    symbol = symbol.upper()
    if settings.market_data_live:  # pragma: no cover
        cached = _cache_get(f"detail:{symbol}")
        if isinstance(cached, dict):
            return cached
    name, asset_type = ASSET_META.get(symbol, (symbol, "stock"))
    closes, high, low, volume, source = _detail_series(symbol)

    price = closes[-1]
    prev = closes[-2] if len(closes) > 1 else price
    change_24h = ((price - prev) / prev * 100.0) if prev else 0.0
    recent = closes[-30:]
    detail = {
        "symbol": symbol,
        "name": name,
        "type": asset_type,
        "price": round(price, 4),
        "change_24h": round(change_24h, 2),
        "volume_24h": round(volume, 2),
        "high_24h": round(max(high, price), 4),
        "low_24h": round(min(low, price), 4),
        "rsi": round(_compute_rsi(closes), 1),
        "macd_signal": _macd_signal(closes),
        "ma50": round(_moving_average(closes, 50), 4),
        "ma200": round(_moving_average(closes, 200), 4),
        "support": round(min(recent), 4),
        "resistance": round(max(recent), 4),
        "source": source,
        "history": [{"t": i, "p": round(c, 4)} for i, c in enumerate(closes)],
    }
    if source != "seed":  # pragma: no cover
        _cache_put(f"detail:{symbol}", detail)
    return detail


def get_quotes(symbols: list[str]) -> list[dict]:
    """Lightweight {symbol, price, change_24h} for several assets (ticker bar).

    Live via one batched Twelve Data quote call (cached per symbol); falls back
    to deterministic seed values per symbol so the bar always renders.
    """
    wanted = [s.upper() for s in symbols if s.strip()]
    live: dict[str, dict] = {}
    if settings.market_data_live:  # pragma: no cover
        live = _live_quotes(wanted)
    out: list[dict] = []
    for sym in wanted:
        if sym in live:
            out.append(live[sym])
        else:
            seed = _seed_market_data(sym)
            out.append({"symbol": sym, "price": seed.price, "change_24h": 0.0})
    return out


def _live_quotes(symbols: list[str]) -> dict[str, dict]:  # pragma: no cover
    result: dict[str, dict] = {}
    uncached: list[str] = []
    for sym in symbols:
        cached = _cache_get(f"quote:{sym}")
        if isinstance(cached, dict):
            result[sym] = cached
        else:
            uncached.append(sym)
    if uncached:
        try:
            for sym, quote in _twelvedata_quotes(uncached).items():
                _cache_put(f"quote:{sym}", quote)
                result[sym] = quote
        except Exception as exc:
            logger.warning("quotes fetch failed: %s", exc)
    return result


def _twelvedata_quotes(symbols: list[str]) -> dict[str, dict]:  # pragma: no cover
    """Batched Twelve Data /quote for multiple symbols in one request."""
    if not settings.twelve_data_api_key:
        raise ValueError("TWELVE_DATA_API_KEY not set")
    import httpx

    # Map the Twelve Data symbol (BTC/USD) back to our ticker (BTC).
    td_map = {(f"{s}/USD" if s in CRYPTO_SYMBOLS else s): s for s in symbols}
    resp = httpx.get(
        "https://api.twelvedata.com/quote",
        params={
            "symbol": ",".join(td_map),
            "apikey": settings.twelve_data_api_key,
        },
        timeout=8.0,
    )
    resp.raise_for_status()
    data = resp.json()
    # One symbol -> a bare quote object; many -> keyed by the requested symbol.
    if "close" in data or "symbol" in data:
        data = {next(iter(td_map)): data}
    out: dict[str, dict] = {}
    for td_sym, ticker in td_map.items():
        q = data.get(td_sym)
        if not isinstance(q, dict) or q.get("status") == "error":
            continue
        price = float(q.get("close") or q.get("price") or 0.0)
        if not price:
            continue
        out[ticker] = {
            "symbol": ticker,
            "price": price,
            "change_24h": float(q.get("percent_change") or 0.0),
        }
    return out


def _detail_series(symbol: str) -> tuple[list[float], float, float, float, str]:
    if settings.market_data_live:  # pragma: no cover
        for name, fetch in (
            ("twelvedata", _twelvedata_series),
            ("stooq", _stooq_series),
        ):
            try:
                closes, high, low, volume = fetch(symbol)
                logger.info("asset detail %s via %s: %d pts", symbol, name, len(closes))
                return closes, high, low, volume, name
            except Exception as exc:
                logger.warning("asset detail %s via %s failed: %s", symbol, name, exc)
    closes = _synth_closes(symbol)
    price = closes[-1]
    return closes, price * 1.02, price * 0.98, 0.0, "seed"


def _synth_closes(symbol: str, n: int = 120) -> list[float]:
    """Deterministic wavy series around the seed price (offline chart)."""
    base = _seed_market_data(symbol).price
    seed = sum(ord(c) for c in symbol)
    out = []
    for i in range(n):
        wave = math.sin(i * 0.15 + (seed % 7)) * (base * 0.03) + math.sin(
            i * 0.05 + 1.1
        ) * (base * 0.02)
        out.append(round(max(base + wave, 0.01), 4))
    return out


def _moving_average(closes: list[float], period: int) -> float:
    window = closes[-period:] if closes else []
    return sum(window) / len(window) if window else 0.0


def _ema_series(values: list[float], period: int) -> list[float]:
    k = 2.0 / (period + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def _macd_signal(closes: list[float]) -> str:
    """MACD(12,26) vs its 9-period signal line -> bullish/bearish/neutral."""
    if len(closes) < 35:
        return "neutral"
    ema12 = _ema_series(closes, 12)
    ema26 = _ema_series(closes, 26)
    macd = [a - b for a, b in zip(ema12, ema26)]
    signal = _ema_series(macd, 9)
    diff = macd[-1] - signal[-1]
    eps = abs(closes[-1]) * 0.0005
    if diff > eps:
        return "bullish"
    if diff < -eps:
        return "bearish"
    return "neutral"
