import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.db.session import Base, get_db


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_all_tables_registered():
    expected = {"portfolios", "positions", "trades", "agent_runs"}
    assert expected <= set(Base.metadata.tables.keys())


def test_portfolio_with_relationships(session):
    portfolio = models.Portfolio(user="demo", cash_balance=10000.0)
    session.add(portfolio)
    session.flush()

    session.add(
        models.Position(
            portfolio_id=portfolio.id, symbol="AAPL", qty=10, avg_price=150.0
        )
    )
    session.add(
        models.Trade(
            portfolio_id=portfolio.id,
            symbol="AAPL",
            side="BUY",
            qty=10,
            price=150.0,
            rationale="momentum breakout",
        )
    )
    session.add(
        models.AgentRun(
            portfolio_id=portfolio.id,
            symbol="AAPL",
            analyst_json="{}",
            risk_json="{}",
            executed=True,
        )
    )
    session.commit()

    saved = session.query(models.Portfolio).first()
    assert saved.cash_balance == 10000.0
    assert len(saved.positions) == 1
    assert saved.positions[0].symbol == "AAPL"
    assert len(saved.trades) == 1
    assert saved.trades[0].side == "BUY"
    assert len(saved.agent_runs) == 1
    assert saved.agent_runs[0].executed is True


def test_defaults_applied(session):
    portfolio = models.Portfolio(user="demo")
    session.add(portfolio)
    session.commit()

    saved = session.query(models.Portfolio).first()
    assert saved.cash_balance == 0.0
    assert saved.created_at is not None


def test_get_db_yields_and_closes():
    gen = get_db()
    db = next(gen)
    assert db is not None
    gen.close()


def test_lifespan_creates_tables(monkeypatch):
    from fastapi.testclient import TestClient

    from app import main

    sqlite_engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    monkeypatch.setattr(main, "engine", sqlite_engine)

    with TestClient(main.app) as client:
        assert client.get("/health").status_code == 200
