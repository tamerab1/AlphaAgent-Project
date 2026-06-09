from app.schemas.agent import AnalystDecision
from app.services import llm
from app.models import Position


def _create(client, cash=100000.0):
    return client.post(
        "/api/portfolios", json={"user": "idan", "cash_balance": cash}
    ).json()["id"]


def _decision(action, pct=0.05):
    return AnalystDecision(
        action=action,
        symbol="AAPL",
        reasoning="test",
        confidence=0.7,
        suggested_pct=pct,
    )


def _events(resp):
    return [
        line.removeprefix("data: ")
        for line in resp.text.splitlines()
        if line.startswith("data: ")
    ]


def test_analyze_streams_nodes_and_done(api_client, monkeypatch):
    client, _ = api_client
    monkeypatch.setattr(llm, "analyze", lambda m, p: _decision("BUY"))
    pid = _create(client)
    resp = client.post(f"/api/ai/{pid}/analyze-chart", json={"symbol": "AAPL"})
    assert resp.status_code == 200
    events = _events(resp)
    assert events, "expected SSE data events"
    assert events[-1].endswith("}")
    assert any('"node": "ingest"' in e for e in events)
    assert any('"node": "done"' in e for e in events)


def test_analyze_buy_persists_trade_and_logs(api_client, monkeypatch):
    client, _ = api_client
    monkeypatch.setattr(llm, "analyze", lambda m, p: _decision("BUY"))
    pid = _create(client, cash=100000.0)

    resp = client.post(f"/api/ai/{pid}/analyze-chart", json={"symbol": "AAPL"})
    _ = resp.text  # consume the SSE stream so persistence runs

    status = client.get(f"/api/portfolio/{pid}/status").json()
    assert len(status["positions"]) == 1
    assert status["positions"][0]["symbol"] == "AAPL"
    assert status["cash_balance"] < 100000.0  # cash spent on the buy

    logs = client.get(f"/api/ai/{pid}/logs").json()
    assert len(logs) == 1
    assert logs[0]["symbol"] == "AAPL"
    assert logs[0]["executed"] is True
    assert logs[0]["analyst"]["action"] == "BUY"
    assert logs[0]["risk"]["approved"] is True


def test_analyze_hold_records_run_without_trade(api_client, monkeypatch):
    client, _ = api_client
    monkeypatch.setattr(llm, "analyze", lambda m, p: _decision("HOLD", pct=0.0))
    pid = _create(client)

    resp = client.post(f"/api/ai/{pid}/analyze-chart", json={"symbol": "AAPL"})
    _ = resp.text  # consume the SSE stream so persistence runs

    status = client.get(f"/api/portfolio/{pid}/status").json()
    assert status["positions"] == []
    assert status["cash_balance"] == 100000.0

    logs = client.get(f"/api/ai/{pid}/logs").json()
    assert len(logs) == 1
    assert logs[0]["executed"] is False


def test_analyze_sell_reduces_position(api_client, monkeypatch):
    client, Session = api_client
    monkeypatch.setattr(llm, "analyze", lambda m, p: _decision("SELL", pct=0.5))
    pid = _create(client)

    db = Session()
    db.add(Position(portfolio_id=pid, symbol="AAPL", qty=10.0, avg_price=100.0))
    db.commit()
    db.close()

    resp = client.post(f"/api/ai/{pid}/analyze-chart", json={"symbol": "AAPL"})
    _ = resp.text  # consume the SSE stream so persistence runs

    status = client.get(f"/api/portfolio/{pid}/status").json()
    pos = next(p for p in status["positions"] if p["symbol"] == "AAPL")
    assert pos["qty"] == 5.0  # half sold
    assert status["cash_balance"] > 100000.0  # proceeds added

    logs = client.get(f"/api/ai/{pid}/logs").json()
    assert logs[0]["executed"] is True
    assert logs[0]["analyst"]["action"] == "SELL"


def test_analyze_buy_adds_to_existing_position(api_client, monkeypatch):
    client, Session = api_client
    monkeypatch.setattr(llm, "analyze", lambda m, p: _decision("BUY", pct=0.02))
    pid = _create(client)

    db = Session()
    db.add(Position(portfolio_id=pid, symbol="AAPL", qty=1.0, avg_price=136.0))
    db.commit()
    db.close()

    resp = client.post(f"/api/ai/{pid}/analyze-chart", json={"symbol": "AAPL"})
    _ = resp.text  # consume the SSE stream so persistence runs

    status = client.get(f"/api/portfolio/{pid}/status").json()
    positions = [p for p in status["positions"] if p["symbol"] == "AAPL"]
    assert len(positions) == 1  # added to existing, not duplicated
    assert positions[0]["qty"] > 1.0  # shares accumulated
    assert status["cash_balance"] < 100000.0  # cash spent


def test_analyze_404_for_missing_portfolio(api_client):
    client, _ = api_client
    resp = client.post("/api/ai/999/analyze-chart", json={"symbol": "AAPL"})
    assert resp.status_code == 404


def test_analyze_accepts_chart_image(api_client):
    client, _ = api_client
    pid = _create(client)
    resp = client.post(
        f"/api/ai/{pid}/analyze-chart",
        json={"symbol": "AAPL", "chart_image": "data:image/png;base64,AAAA"},
    )
    assert resp.status_code == 200
    assert '"node": "done"' in resp.text

    logs = client.get(f"/api/ai/{pid}/logs").json()
    assert "chart image" in logs[0]["analyst"]["reasoning"].lower()


def test_read_chart_returns_reading(api_client, monkeypatch):
    from app.schemas.agent import ChartReading

    client, _ = api_client
    monkeypatch.setattr(
        llm,
        "read_chart",
        lambda image, symbol=None: ChartReading(summary="patched read", bias="bullish"),
    )
    body = client.post(
        "/api/ai/read-chart",
        json={"chart_image": "data:image/png;base64,AAAA", "symbol": "AAPL"},
    ).json()
    assert body["summary"] == "patched read"
    assert body["bias"] == "bullish"


def test_read_chart_rejects_empty_image(api_client):
    client, _ = api_client
    resp = client.post("/api/ai/read-chart", json={"chart_image": ""})
    assert resp.status_code == 400
