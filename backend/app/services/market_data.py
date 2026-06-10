import logging
import math
import time
import urllib.parse

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

    For crypto assets, fetches real-time price from Binance (public API, no
    key) even when ``MARKET_DATA_LIVE`` is false.  If the asset-detail TTL
    cache is warm (populated by a recent chart load) the cached RSI is reused;
    otherwise the seed RSI is kept.  For stocks in non-live mode the full
    seed value is returned unchanged.
    """
    seed = _seed_market_data(symbol)
    if not settings.market_data_live:
        if _is_crypto_symbol(symbol):  # pragma: no cover
            # Prefer the cached detail (real price + real RSI from klines).
            cached_detail = _cache_get(f"detail:{symbol.upper()}")
            if isinstance(cached_detail, dict):
                return MarketData(
                    symbol=symbol,
                    price=cached_detail["price"],
                    rsi=cached_detail["rsi"],
                    headlines=seed.headlines,
                )
            # Fast fallback: just the current spot price from Binance.
            try:
                pair = BINANCE_PAIRS.get(symbol.upper(), f"{symbol.upper()}USDT")
                price = _binance_spot_price(pair)
                return MarketData(
                    symbol=symbol, price=price, rsi=seed.rsi, headlines=seed.headlines
                )
            except Exception as exc:
                logger.debug("binance market_data skip for %s: %s", symbol, exc)
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

# Binance spot ticker → USDT pair mapping (public API, no key required).
BINANCE_PAIRS: dict[str, str] = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "BNB": "BNBUSDT",
    "XRP": "XRPUSDT",
    "ADA": "ADAUSDT",
    "DOGE": "DOGEUSDT",
    "LTC": "LTCUSDT",
}

# Realistic baseline prices used by synthetic fallbacks when Binance is blocked.
# Keeps charts at the right magnitude even without live data.
_SYNTHETIC_PRICES: dict[str, float] = {
    "BTC": 61800.0,
    "ETH": 1700.0,
    "SOL": 65.0,
    "BNB": 600.0,
    "XRP": 0.55,
    "ADA": 0.45,
    "DOGE": 0.12,
    "LTC": 85.0,
    "AAPL": 190.0,
    "MSFT": 415.0,
    "TSLA": 175.0,
    "NVDA": 875.0,
    "GOOGL": 175.0,
    "AMZN": 185.0,
    "META": 530.0,
    "SPY": 540.0,
}

# Seconds per Binance kline interval — used to space synthetic candle timestamps.
_INTERVAL_SECONDS: dict[str, int] = {
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "2h": 7200,
    "4h": 14400,
    "6h": 21600,
    "12h": 43200,
    "1d": 86400,
    "3d": 259200,
    "1w": 604800,
}


def _is_crypto_symbol(symbol: str) -> bool:
    """True for symbols that can be priced via Binance USDT pairs."""
    sym = symbol.upper()
    return sym in BINANCE_PAIRS or ASSET_META.get(sym, ("", "stock"))[1] == "crypto"


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


def get_execution_price(symbol: str) -> float:
    """Return the freshest available spot price for trade execution.

    Tries the Binance public ticker for every symbol by constructing a
    {SYM}USDT pair (known pairs use the exact mapping from BINANCE_PAIRS).
    Binance returns HTTP 400 immediately for unknown pairs (e.g. stocks) so
    there is no latency penalty — the fall-through to regular market data is
    near-instant.  No API key required.
    """
    sym = symbol.upper()
    pair = BINANCE_PAIRS.get(sym, f"{sym}USDT")
    try:
        price = _binance_spot_price(pair)
        logger.info("execution price %s via binance (%s): %.4f", sym, pair, price)
        return price
    except Exception as exc:
        logger.warning(
            "binance spot price failed %s (%s) [%s]: %s — using market_data fallback",
            sym,
            pair,
            type(exc).__name__,
            exc,
        )
    return get_market_data(sym).price


def _binance_spot_price(pair: str) -> float:  # pragma: no cover
    """Fetch the current spot price for *pair* from the Binance public REST API."""
    import httpx

    resp = httpx.get(
        "https://api3.binance.com/api/v3/ticker/price",
        params={"symbol": pair},
        timeout=10.0,
    )
    resp.raise_for_status()
    price = float(resp.json()["price"])
    if price <= 0:
        raise ValueError(f"non-positive price from Binance for {pair}: {price}")
    return price


def _binance_batch_quotes(symbols: list[str]) -> dict[str, dict]:  # pragma: no cover
    """Real-time 24h ticker for crypto symbols via individual Binance calls.

    Uses the single-symbol ``?symbol=BTCUSDT`` form (the same endpoint used by
    _binance_detail_series, proven reliable) rather than the batch
    ``?symbols=[...]`` JSON-array variant which can fail due to URL-encoding.
    """
    import httpx

    result: dict[str, dict] = {}
    for sym in symbols:
        pair = BINANCE_PAIRS.get(sym, f"{sym}USDT")
        try:
            resp = httpx.get(
                "https://api3.binance.com/api/v3/ticker/24hr",
                params={"symbol": pair},
                timeout=10.0,
            )
            resp.raise_for_status()
            d = resp.json()
            price = float(d.get("lastPrice") or 0.0)
            change = float(d.get("priceChangePercent") or 0.0)
            if price > 0:
                result[sym] = {"symbol": sym, "price": price, "change_24h": change}
        except Exception as exc:
            logger.warning(
                "binance 24hr ticker failed %s (%s) [%s]: %s",
                sym,
                pair,
                type(exc).__name__,
                exc,
            )
    return result


def _binance_detail_series(
    symbol: str,
) -> tuple[list[float], float, float, float, str]:  # pragma: no cover
    """Daily close history + 24h stats from Binance klines (crypto, no API key)."""
    import httpx

    pair = BINANCE_PAIRS.get(symbol.upper(), f"{symbol.upper()}USDT")
    logger.info("binance klines request %s (pair=%s)", symbol, pair)
    klines_resp = httpx.get(
        "https://api3.binance.com/api/v3/klines",
        params={"symbol": pair, "interval": "1d", "limit": 200},
        timeout=12.0,
    )
    klines_resp.raise_for_status()
    closes = [float(k[4]) for k in klines_resp.json()]
    if not closes:
        raise ValueError(f"empty klines for {pair}")
    ticker_resp = httpx.get(
        "https://api3.binance.com/api/v3/ticker/24hr",
        params={"symbol": pair},
        timeout=10.0,
    )
    ticker_resp.raise_for_status()
    t = ticker_resp.json()
    high = float(t.get("highPrice") or closes[-1])
    low = float(t.get("lowPrice") or closes[-1])
    volume = float(t.get("quoteVolume") or t.get("volume") or 0.0)
    return closes, high, low, volume, "binance"


def get_klines(symbol: str, interval: str = "1d", limit: int = 100) -> list[dict]:
    """Return OHLCV candles: Binance for crypto, synthetic for stocks/offline."""
    sym = symbol.upper()
    cache_key = f"klines:{sym}:{interval}:{limit}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached  # type: ignore[return-value]

    candles: list[dict] = []
    if _is_crypto_symbol(sym):  # pragma: no cover
        try:
            candles = _binance_klines(sym, interval, limit)
            logger.info(
                "binance klines OK %s interval=%s limit=%d → %d candles",
                sym,
                interval,
                limit,
                len(candles),
            )
        except Exception as exc:
            logger.warning(
                "binance klines FAILED %s interval=%s limit=%d [%s]: %s"
                " — falling back to synthetic candles",
                sym,
                interval,
                limit,
                type(exc).__name__,
                exc,
            )

    if not candles:
        logger.info(
            "generating synthetic klines for %s interval=%s limit=%d",
            sym,
            interval,
            limit,
        )
        candles = _synthetic_klines(sym, interval, limit)

    _cache_put(cache_key, candles)
    return candles


def _binance_klines(
    symbol: str, interval: str = "1d", limit: int = 100
) -> list[dict]:  # pragma: no cover
    """Fetch full OHLCV candles from Binance public klines endpoint."""
    import httpx

    pair = BINANCE_PAIRS.get(symbol, f"{symbol}USDT")
    logger.info(
        "binance klines fetch %s (pair=%s interval=%s limit=%d)",
        symbol,
        pair,
        interval,
        limit,
    )
    resp = httpx.get(
        "https://api3.binance.com/api/v3/klines",
        params={"symbol": pair, "interval": interval, "limit": limit},
        timeout=12.0,
    )
    resp.raise_for_status()
    candles = []
    for k in resp.json():
        candles.append(
            {
                "t": int(k[0]) // 1000,  # ms → seconds
                "o": float(k[1]),
                "h": float(k[2]),
                "l": float(k[3]),
                "c": float(k[4]),
                "v": round(float(k[7]), 2),  # quote asset volume
            }
        )
    return candles


def _synthetic_klines(
    symbol: str, interval: str = "1d", limit: int = 100
) -> list[dict]:
    """Realistic deterministic OHLCV candles (production fallback when Binance is blocked).

    Uses a table of known realistic prices for common assets so charts render at
    the correct magnitude.  Price motion is a sum of three sine waves at different
    frequencies (multi-timeframe structure) plus a small trend drift, all seeded
    deterministically from the symbol name.  Always returns exactly *limit* candles
    with timestamps spaced by the requested *interval*.
    """
    sym = symbol.upper()
    seed_int = sum(ord(c) for c in sym)

    # Realistic baseline; for unknowns derive a plausible order-of-magnitude price.
    base_price = _SYNTHETIC_PRICES.get(
        sym,
        round(10.0 ** (1 + (seed_int % 4)) * (1.0 + (seed_int % 97) / 100.0), 2),
    )

    interval_secs = _INTERVAL_SECONDS.get(interval, 86400)
    now = int(time.time())

    # Deterministic phase seeds in (0, 1) unique to this symbol.
    s1 = ((seed_int * 17 + 3) % 100) / 100.0
    s2 = ((seed_int * 31 + 7) % 100) / 100.0
    s3 = ((seed_int * 53 + 11) % 100) / 100.0

    # Intraday volatility scales with sqrt(interval / 1d) so short bars look tight.
    vol_scale = math.sqrt(interval_secs / 86400.0)

    # Small linear trend: ±5 % total across the full series (never compounds away).
    trend_dir = 1.0 if (seed_int % 3) != 2 else -1.0
    total_drift = trend_dir * 0.05

    dec = _price_decimals(base_price)
    candles: list[dict] = []

    for i in range(limit):
        frac = i / max(limit - 1, 1)  # 0.0 → 1.0 across the series

        # Additive multi-harmonic oscillation — price orbits base_price, never escapes.
        wave = (
            math.sin(i * 0.21 + s1 * math.pi) * 0.025
            + math.sin(i * 0.07 + s2 * math.pi) * 0.015
            + math.sin(i * 0.03 + s3 * math.pi) * 0.008
        )
        close_frac = 1.0 + wave * vol_scale + total_drift * frac
        close = round(max(base_price * close_frac, base_price * 0.5), dec)

        # Candle body fraction, interval-scaled.
        body_frac = vol_scale * 0.007 * (0.4 + abs(math.sin(i * 0.55 + s2 * 3)) * 0.6)
        bull = (wave + total_drift * frac) >= 0
        body = close * body_frac
        open_p = round(
            max(close - body, close * 0.9) if bull else min(close + body, close * 1.1),
            dec,
        )

        # Wicks — smaller than body, interval-scaled.
        wick_frac = vol_scale * 0.003
        upper_wick = close * wick_frac * (0.5 + abs(math.sin(i * 0.80 + s2 * 5)) * 1.0)
        lower_wick = close * wick_frac * (0.5 + abs(math.cos(i * 0.80 + s3 * 5)) * 1.0)
        high = round(max(open_p, close) + upper_wick, dec)
        low = round(max(min(open_p, close) - lower_wick, close * 0.001), dec)

        volume = round(
            base_price * 500_000 * (0.5 + abs(math.sin(i * 0.44 + s3 * 4)) * 1.0), 2
        )
        t = now - (limit - i) * interval_secs
        candles.append(
            {"t": t, "o": open_p, "h": high, "l": low, "c": close, "v": volume}
        )

    return candles


def _price_decimals(price: float) -> int:
    """Decimal places appropriate for a given price magnitude."""
    if price >= 100:
        return 2
    if price >= 1:
        return 4
    return 6


def get_news_data(symbol: str) -> list[dict]:
    """Return ``[{"headline": str, "url": str}, ...]`` for a symbol.

    In live mode with a Tavily key, fetches real headlines + source URLs.
    Falls back to seed headlines with Google News search links so every
    news card always has a working "Read Original Source" URL.
    """
    sym = symbol.upper()
    if settings.market_data_live and settings.tavily_api_key:  # pragma: no cover
        try:
            items = _tavily_news_items(sym)
            if items:
                return items
        except Exception as exc:
            logger.warning("tavily news_data failed for %s: %s", sym, exc)
    seed = _seed_market_data(sym)
    return [
        {
            "headline": h,
            "url": (
                "https://news.google.com/search?q="
                + urllib.parse.quote_plus(h)
                + "&hl=en&gl=US&ceid=US:en"
            ),
        }
        for h in seed.headlines
    ]


def _tavily_headlines(symbol: str, limit: int = 3) -> list[str]:  # pragma: no cover
    from tavily import TavilyClient

    client = TavilyClient(api_key=settings.tavily_api_key)
    resp = client.search(query=f"{symbol} stock news", topic="news", max_results=limit)
    return [r["title"] for r in resp.get("results", [])][:limit]


def _tavily_news_items(symbol: str, limit: int = 3) -> list[dict]:  # pragma: no cover
    """Fetch real headlines **and** their source URLs from Tavily."""
    from tavily import TavilyClient

    client = TavilyClient(api_key=settings.tavily_api_key)
    resp = client.search(
        query=f"{symbol} crypto stock financial news",
        topic="news",
        max_results=limit,
    )
    return [
        {"headline": r["title"], "url": r.get("url", "")}
        for r in resp.get("results", [])[:limit]
    ]


# --- Asset detail (price chart + technical indicators) -----------------------


def get_asset_detail(symbol: str) -> dict:
    """Market data + technical indicators + price history for one asset.

    Used by the dashboard's price chart / AI-analysis widgets. Uses live data
    (Twelve Data, then Stooq) when MARKET_DATA_LIVE is set, else a deterministic
    synthetic series so the chart looks alive offline. AI fields are added by
    the API layer (it owns the LLM call).
    """
    symbol = symbol.upper()
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

    For crypto, fetches real-time prices from the Binance public 24h-ticker
    endpoint (no API key, TTL-cached per symbol).  For stocks in non-live mode
    returns deterministic seed values so the bar always renders.
    """
    wanted = [s.upper() for s in symbols if s.strip()]
    live: dict[str, dict] = {}

    # Real-time crypto prices via Binance (always enabled, no API key).
    crypto_syms = [s for s in wanted if _is_crypto_symbol(s)]
    uncached_crypto: list[str] = []
    for sym in crypto_syms:
        # 1. Fresh quote cache (populated by previous ticker-bar calls).
        hit = _cache_get(f"quote:{sym}")
        if isinstance(hit, dict):
            live[sym] = hit
            continue
        # 2. Detail cache (populated by chart/analysis fetches) — avoids a
        #    redundant network round-trip when the user has already viewed the asset.
        detail_hit = _cache_get(f"detail:{sym}")
        if isinstance(detail_hit, dict):
            live[sym] = {
                "symbol": sym,
                "price": detail_hit["price"],
                "change_24h": detail_hit.get("change_24h", 0.0),
            }
            continue
        uncached_crypto.append(sym)
    if uncached_crypto:  # pragma: no cover
        try:
            for sym, quote in _binance_batch_quotes(uncached_crypto).items():
                _cache_put(f"quote:{sym}", quote)
                live[sym] = quote
        except Exception as exc:
            logger.warning("binance quotes failed: %s", exc)

    # Stocks (and anything Binance couldn't quote) via Twelve Data when live.
    if settings.market_data_live:  # pragma: no cover
        remaining = [s for s in wanted if s not in live]
        if remaining:
            live.update(_live_quotes(remaining))

    out: list[dict] = []
    for sym in wanted:
        if sym in live:
            out.append(live[sym])
        else:
            base_price = _SYNTHETIC_PRICES.get(sym, _seed_market_data(sym).price)
            out.append({"symbol": sym, "price": base_price, "change_24h": 0.0})
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
    # Binance provides real daily OHLCV for all listed crypto — no API key.
    if _is_crypto_symbol(symbol):  # pragma: no cover
        try:
            return _binance_detail_series(symbol)
        except Exception as exc:
            logger.warning("binance detail series failed for %s: %s", symbol, exc)
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
    """Deterministic wavy close-price series for the offline line chart.

    Uses the realistic price table so BTC renders near $94k, not the tiny
    seed-formula value (~$67) that was showing in production.
    """
    sym = symbol.upper()
    seed_int = sum(ord(c) for c in sym)
    base = _SYNTHETIC_PRICES.get(sym, _seed_market_data(sym).price)
    dec = _price_decimals(base)

    s1 = ((seed_int * 17 + 3) % 100) / 100.0
    s2 = ((seed_int * 31 + 7) % 100) / 100.0
    trend_dir = 1.0 if (seed_int % 3) != 2 else -1.0
    total_drift = trend_dir * 0.05  # ±5% total across series — never compounds

    out = []
    for i in range(n):
        frac = i / max(n - 1, 1)
        wave = (
            math.sin(i * 0.21 + s1 * math.pi) * 0.025
            + math.sin(i * 0.07 + s2 * math.pi) * 0.015
        )
        close_frac = 1.0 + wave + total_drift * frac
        out.append(round(max(base * close_frac, base * 0.5), dec))
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
