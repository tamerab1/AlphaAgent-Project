from app.schemas.agent import MarketData
from app.services import market_data


def test_seed_is_deterministic():
    a = market_data.get_market_data("AAPL")
    b = market_data.get_market_data("AAPL")
    assert isinstance(a, MarketData)
    assert a == b


def test_seed_differs_by_symbol():
    assert (
        market_data.get_market_data("AAPL").price
        != market_data.get_market_data("MSFT").price
    )


def test_seed_has_headlines():
    data = market_data.get_market_data("AAPL")
    assert data.symbol == "AAPL"
    assert data.headlines
    assert all("AAPL" in h for h in data.headlines)


def test_seed_rsi_in_range():
    rsi = market_data.get_market_data("TSLA").rsi
    assert 0.0 <= rsi <= 100.0


def test_compute_rsi_all_gains():
    closes = [float(i) for i in range(1, 30)]
    assert market_data._compute_rsi(closes) == 100.0


def test_compute_rsi_all_losses():
    closes = [float(i) for i in range(30, 1, -1)]
    assert market_data._compute_rsi(closes) == 0.0


def test_compute_rsi_flat_is_neutral():
    assert market_data._compute_rsi([100.0] * 30) == 50.0


def test_compute_rsi_too_short_is_neutral():
    assert market_data._compute_rsi([1.0, 2.0, 3.0]) == 50.0


def test_compute_rsi_midrange():
    closes = [1.0, 2.0, 1.0, 2.0, 1.0, 2.0, 1.0, 2.0] * 4
    rsi = market_data._compute_rsi(closes)
    assert 0.0 < rsi < 100.0


def test_moving_average():
    assert market_data._moving_average([1.0, 2.0, 3.0, 4.0], 2) == 3.5
    assert market_data._moving_average([5.0, 7.0], 50) == 6.0
    assert market_data._moving_average([], 5) == 0.0


def test_macd_signal_short_is_neutral():
    assert market_data._macd_signal([100.0] * 10) == "neutral"


def test_macd_signal_uptrend_is_bullish():
    closes = [float(i) for i in range(1, 60)]
    assert market_data._macd_signal(closes) == "bullish"


def test_macd_signal_downtrend_is_bearish():
    closes = [float(i) for i in range(60, 1, -1)]
    assert market_data._macd_signal(closes) == "bearish"


def test_get_asset_detail_seed_deterministic():
    a = market_data.get_asset_detail("AAPL")
    b = market_data.get_asset_detail("AAPL")
    assert a == b
    assert a["source"] == "seed"
    assert a["name"] == "Apple" and a["type"] == "stock"
    assert a["price"] > 0
    assert len(a["history"]) == 120
    assert 0.0 <= a["rsi"] <= 100.0


def test_get_asset_detail_crypto_meta():
    d = market_data.get_asset_detail("btc")
    assert d["symbol"] == "BTC"
    assert d["type"] == "crypto" and d["name"] == "Bitcoin"


def test_get_quotes_seed():
    quotes = market_data.get_quotes(["AAPL", "BTC", ""])
    assert {q["symbol"] for q in quotes} == {"AAPL", "BTC"}
    assert all(q["price"] > 0 for q in quotes)
    # Stocks use seed data (change_24h is always 0.0 in non-live mode).
    # Crypto may use Binance real-time data so change_24h can be non-zero.
    aapl = next(q for q in quotes if q["symbol"] == "AAPL")
    assert aapl["change_24h"] == 0.0


def test_cache_put_get_roundtrip():
    market_data._cache_put("test:roundtrip", 42)
    assert market_data._cache_get("test:roundtrip") == 42
    assert market_data._cache_get("test:absent") is None
