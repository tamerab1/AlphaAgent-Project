from ai import market_data
from ai.schemas import MarketData


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
