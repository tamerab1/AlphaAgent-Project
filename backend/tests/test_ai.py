import pytest

from app.agents import graph
from app.agents.risk import assess_risk
from app.core.config import settings
from app.schemas.agent import AnalystDecision, MarketData, PortfolioSnapshot
from app.services import llm


@pytest.fixture(autouse=True)
def _no_api_key(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def _market(rsi=25.0, symbol="AAPL", price=100.0):
    return MarketData(symbol=symbol, price=price, rsi=rsi, headlines=[])


def _portfolio(cash=20000.0, total=100000.0, exposure=0.0):
    return PortfolioSnapshot(
        cash_balance=cash, total_value=total, symbol_exposure=exposure
    )


def _decision(action, pct=0.05, confidence=0.6):
    return AnalystDecision(
        action=action,
        symbol="AAPL",
        reasoning="test",
        confidence=confidence,
        suggested_pct=pct,
    )


def test_mock_analyze_buy_on_low_rsi():
    assert llm.analyze(_market(rsi=20.0), _portfolio()).action == "BUY"


def test_mock_analyze_sell_on_high_rsi():
    assert llm.analyze(_market(rsi=80.0), _portfolio()).action == "SELL"


def test_mock_analyze_hold_midrange():
    assert llm.analyze(_market(rsi=50.0), _portfolio()).action == "HOLD"


def test_mock_analyze_buy_sets_target_and_stop():
    d = llm.analyze(_market(rsi=20.0, price=100.0), _portfolio())
    assert d.target_price == 110.0
    assert d.stop_loss == 95.0


def test_mock_analyze_sell_sets_target_and_stop():
    d = llm.analyze(_market(rsi=80.0, price=100.0), _portfolio())
    assert d.target_price == 90.0
    assert d.stop_loss == 105.0


def test_mock_analyze_hold_has_no_target():
    d = llm.analyze(_market(rsi=50.0), _portfolio())
    assert d.target_price is None
    assert d.stop_loss is None


def test_mock_analyze_with_chart_image_notes_it():
    d = llm.analyze(
        _market(rsi=20.0),
        _portfolio(),
        chart_image="data:image/png;base64,AAAA",
    )
    assert d.action == "BUY"
    assert "chart image" in d.reasoning.lower()


def test_mock_read_chart_offline_placeholder():
    from app.schemas.agent import ChartReading

    reading = llm.read_chart("data:image/png;base64,AAAA", "AAPL")
    assert isinstance(reading, ChartReading)
    assert reading.bias == "neutral"
    assert "AAPL" in reading.summary


def test_risk_note_mock():
    note = llm.risk_note(_market(), _decision("BUY"))
    assert "risk note" in note.lower()


def test_graph_executes_buy(monkeypatch):
    monkeypatch.setattr(
        llm, "judge", lambda m, p, bull, bear, chart_image=None: _decision("BUY")
    )
    result = graph.build_graph().invoke(
        {"symbol": "AAPL", "market": _market(), "portfolio": _portfolio()}
    )
    assert result["executed"] is True
    assert result["risk"].approved is True
    assert result["bull"].stance == "bull"
    assert result["bear"].stance == "bear"


def test_graph_rejects_hold(monkeypatch):
    monkeypatch.setattr(
        llm, "judge", lambda m, p, bull, bear, chart_image=None: _decision("HOLD", pct=0.0)
    )
    result = graph.build_graph().invoke(
        {"symbol": "AAPL", "market": _market(), "portfolio": _portfolio()}
    )
    assert result["executed"] is False


def test_graph_ingest_mocks_market(monkeypatch):
    monkeypatch.setattr(
        llm, "judge", lambda m, p, bull, bear, chart_image=None: _decision("HOLD", pct=0.0)
    )
    result = graph.build_graph().invoke({"symbol": "AAPL"})
    assert result["market"].symbol == "AAPL"
    assert result["executed"] is False


def test_mock_debate_sides():
    bull = llm.debate_bull(_market(), _portfolio())
    bear = llm.debate_bear(_market(), _portfolio())
    assert bull.stance == "bull" and bear.stance == "bear"
    assert 0.0 <= bull.conviction <= 1.0 and 0.0 <= bear.conviction <= 1.0


def test_graph_runs_debate_end_to_end():
    """Full graph in mock mode: bull and bear argue, then the judge decides."""
    result = graph.build_graph().invoke(
        {"symbol": "AAPL", "market": _market(rsi=20.0), "portfolio": _portfolio()}
    )
    assert result["bull"].stance == "bull"
    assert result["bear"].stance == "bear"
    assert result["bull"].key_points and result["bear"].key_points
    assert result["analyst"].action in {"BUY", "SELL", "HOLD"}


def test_risk_rejects_insufficient_cash():
    risk = assess_risk(
        _decision("BUY"), _portfolio(cash=10.0, total=100000.0), _market()
    )
    assert risk.approved is False
    assert "cash" in risk.reason.lower()


def test_risk_rejects_exposure_over_cap():
    risk = assess_risk(
        _decision("BUY"),
        _portfolio(cash=100000.0, total=100000.0, exposure=5000.0),
        _market(),
    )
    assert risk.approved is False
    assert "5%" in risk.reason


def test_risk_caps_buy_at_5pct():
    risk = assess_risk(
        _decision("BUY", pct=0.5),
        _portfolio(cash=100000.0, total=100000.0),
        _market(),
    )
    assert risk.adjusted_pct == 0.05
    assert risk.approved is True


def test_risk_rejects_sell_without_position():
    risk = assess_risk(_decision("SELL"), _portfolio(exposure=0.0), _market())
    assert risk.approved is False


def test_risk_approves_sell_with_position():
    risk = assess_risk(
        _decision("SELL", pct=0.5), _portfolio(exposure=5000.0), _market()
    )
    assert risk.approved is True
