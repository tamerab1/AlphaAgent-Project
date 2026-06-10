import sqlite3
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.session import Base, get_db
from app.main import app

# SQLite has no native UUID type; register a global adapter so UUID primary
# keys (e.g. Trade.id) can be stored as String(36) in all test databases.
sqlite3.register_adapter(UUID, str)


@pytest.fixture(autouse=True)
def _deterministic_env(monkeypatch):
    """Keep tests offline and deterministic regardless of a local .env.

    A developer's backend/.env may set MARKET_DATA_LIVE=true or an API key;
    pydantic-settings reads it automatically. Force seed market data and the
    mock LLM so the suite never hits the network.
    """
    monkeypatch.setattr(settings, "market_data_live", False)
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def api_client():
    """TestClient backed by an isolated in-memory SQLite DB.

    Yields (client, SessionFactory) so tests can seed rows directly.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, TestingSession
    app.dependency_overrides.clear()
