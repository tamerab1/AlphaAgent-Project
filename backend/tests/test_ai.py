import pytest

from app.agents import graph
from app.agents.risk import assess_risk
from app.schemas.agent import AnalystDecision, MarketData, PortfolioSnapshot
from app.services import llm


@pytest.fixture(autouse=True)
def _no_api_key(monkeypatch):
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


def test_risk_note_mock():
    note = llm.risk_note(_market(), _decision("BUY"))
    assert "risk note" in note.lower()


def test_graph_executes_buy(monkeypatch):
    monkeypatch.setattr(llm, "analyze", lambda m, p: _decision("BUY"))
    result = graph.build_graph().invoke(
        {"symbol": "AAPL", "market": _market(), "portfolio": _portfolio()}
    )
    assert result["executed"] is True
    assert result["risk"].approved is True


def test_graph_rejects_hold(monkeypatch):
    monkeypatch.setattr(llm, "analyze", lambda m, p: _decision("HOLD", pct=0.0))
    result = graph.build_graph().invoke(
        {"symbol": "AAPL", "market": _market(), "portfolio": _portfolio()}
    )
    assert result["executed"] is False


def test_graph_ingest_mocks_market(monkeypatch):
    monkeypatch.setattr(llm, "analyze", lambda m, p: _decision("HOLD", pct=0.0))
    result = graph.build_graph().invoke({"symbol": "AAPL"})
    assert result["market"].symbol == "AAPL"
    assert result["executed"] is False


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
