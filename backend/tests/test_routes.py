import pytest

from app.models import Position, Trade


def _create(client, user="idan", cash=10000.0):
    resp = client.post("/api/portfolios", json={"user": user, "cash_balance": cash})
    assert resp.status_code == 201
    return resp.json()["id"]


def test_create_portfolio(api_client):
    client, _ = api_client
    body = client.post(
        "/api/portfolios", json={"user": "idan", "cash_balance": 5000.0}
    ).json()
    assert body["user"] == "idan"
    assert body["cash_balance"] == 5000.0
    assert isinstance(body["id"], int)


def test_status_empty_portfolio(api_client):
    client, _ = api_client
    pid = _create(client, cash=12345.0)
    body = client.get(f"/api/portfolio/{pid}/status").json()
    assert body["cash_balance"] == 12345.0
    assert body["positions_value"] == 0.0
    assert body["total_value"] == 12345.0
    assert body["positions"] == []


def test_status_with_position(api_client):
    client, Session = api_client
    pid = _create(client, cash=10000.0)
    db = Session()
    db.add(Position(portfolio_id=pid, symbol="AAPL", qty=10.0, avg_price=100.0))
    db.commit()
    db.close()
    body = client.get(f"/api/portfolio/{pid}/status").json()
    assert len(body["positions"]) == 1
    pos = body["positions"][0]
    assert pos["symbol"] == "AAPL"
    assert pos["market_value"] == pytest.approx(pos["current_price"] * 10.0)
    assert body["total_value"] == pytest.approx(
        body["cash_balance"] + body["positions_value"]
    )


def test_status_404(api_client):
    client, _ = api_client
    assert client.get("/api/portfolio/999/status").status_code == 404


def test_trades_empty(api_client):
    client, _ = api_client
    pid = _create(client)
    assert client.get(f"/api/portfolio/{pid}/trades").json() == []


def test_trades_404(api_client):
    client, _ = api_client
    assert client.get("/api/portfolio/999/trades").status_code == 404


def test_trades_returns_newest_first(api_client):
    client, Session = api_client
    pid = _create(client)
    db = Session()
    db.add(Trade(portfolio_id=pid, symbol="AAPL", side="BUY", qty=10.0, price=100.0))
    db.add(Trade(portfolio_id=pid, symbol="TSLA", side="SELL", qty=5.0, price=158.0))
    db.commit()
    db.close()
    body = client.get(f"/api/portfolio/{pid}/trades").json()
    assert len(body) == 2
    assert {t["symbol"] for t in body} == {"AAPL", "TSLA"}
    assert body[0]["created_at"] >= body[1]["created_at"]
    assert body[0]["side"] in {"BUY", "SELL"}


def test_ai_logs_empty(api_client):
    client, _ = api_client
    pid = _create(client)
    assert client.get(f"/api/ai/{pid}/logs").json() == []


def test_ai_logs_404(api_client):
    client, _ = api_client
    assert client.get("/api/ai/999/logs").status_code == 404


def test_toggle_mode_paper(api_client):
    client, _ = api_client
    pid = _create(client)
    body = client.post(f"/api/trading/{pid}/toggle-mode", json={"mode": "paper"}).json()
    assert body["mode"] == "paper"


def test_toggle_mode_live_blocked(api_client):
    client, _ = api_client
    pid = _create(client)
    body = client.post(f"/api/trading/{pid}/toggle-mode", json={"mode": "live"}).json()
    assert body["mode"] == "paper"
    assert "disabled" in body["message"].lower()
