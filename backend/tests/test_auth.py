"""
test_auth.py — Authentication and authorization test suite.

Covers:
  - JWT validation via the real get_current_user_id dependency
  - Protected endpoint access control (success / missing token / invalid token)
  - Portfolio auto-initialization on first authenticated request
  - Behaviour when auth is misconfigured (JWT secret absent)
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Generator
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# sqlite3 has no native UUID type — teach it to coerce UUID → str so that
# Profile.id (stored as String(36) in SQLite) can be bound in queries.
sqlite3.register_adapter(UUID, str)

from app.api.deps import get_current_user_id
from app.core.config import settings
from app.db.session import Base, get_db
from app.main import app
from app.models.portfolio import Portfolio

# ── Constants ──────────────────────────────────────────────────────────────────

TEST_USER_UUID: str = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
TEST_JWT_SECRET: str = "super-secret-test-key-for-pytest-only"
_DEFAULT_CASH: float = 100_000.0


# ── Helpers ────────────────────────────────────────────────────────────────────


def _mint_jwt(
    user_id: str = TEST_USER_UUID,
    secret: str = TEST_JWT_SECRET,
    expired: bool = False,
) -> str:
    """Return a signed HS256 JWT that mirrors Supabase's token shape.

    Pass ``expired=True`` to produce a token whose ``exp`` is one hour in the
    past, or ``secret=<other>`` to produce a token that will fail signature
    verification against TEST_JWT_SECRET.
    """
    now = datetime.now(timezone.utc)
    exp = now - timedelta(hours=1) if expired else now + timedelta(hours=1)
    payload = {
        "sub": user_id,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "role": "authenticated",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def _make_isolated_db() -> sessionmaker[Session]:
    """Spin up an in-memory SQLite engine and return a bound SessionFactory."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _db_override(
    factory: sessionmaker[Session],
) -> Callable[[], Generator[Session, None, None]]:
    """FastAPI dependency override that yields sessions from *factory*."""

    def _get_db_override() -> Generator[Session, None, None]:
        db: Session = factory()
        try:
            yield db
        finally:
            db.close()

    return _get_db_override


# ── Fixtures ───────────────────────────────────────────────────────────────────


@pytest.fixture()
def auth_client() -> Generator[tuple[TestClient, sessionmaker[Session]], None, None]:
    """TestClient where get_current_user_id is stubbed to return TEST_USER_UUID.

    Use this for tests that verify *authenticated* behaviour without caring
    about JWT internals — no real token decoding occurs.

    Yields:
        (TestClient, SessionFactory) so tests can inspect DB state directly.
    """
    factory = _make_isolated_db()

    def _mock_user_id() -> UUID:
        return UUID(TEST_USER_UUID)

    app.dependency_overrides[get_db] = _db_override(factory)
    app.dependency_overrides[get_current_user_id] = _mock_user_id

    with TestClient(app) as client:
        yield client, factory

    app.dependency_overrides.clear()


@pytest.fixture()
def jwt_client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    """TestClient that runs the *real* get_current_user_id dependency.

    supabase_jwt_secret is patched to TEST_JWT_SECRET so that tokens generated
    by ``_mint_jwt()`` pass verification, while all other secrets fail.

    Use this fixture when testing token-validation edge cases directly.

    Yields:
        TestClient (no SessionFactory — DB state is not inspected in these tests).
    """
    factory = _make_isolated_db()
    monkeypatch.setattr(settings, "supabase_jwt_secret", TEST_JWT_SECRET)
    app.dependency_overrides[get_db] = _db_override(factory)

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.pop(get_db, None)


# ── Success path ───────────────────────────────────────────────────────────────


class TestProtectedEndpointSuccess:
    def test_returns_200_with_valid_token(
        self, auth_client: tuple[TestClient, sessionmaker[Session]]
    ) -> None:
        """GET /api/v1/users/me with a valid session returns 200 and the correct UUID.

        The dependency is stubbed — this test verifies the happy-path contract
        of the route handler, not JWT internals.
        """
        # Arrange
        client, _ = auth_client
        headers = {"Authorization": "Bearer stubbed-valid-token"}

        # Act
        response = client.get("/api/v1/users/me", headers=headers)

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == TEST_USER_UUID

    def test_real_jwt_accepted_on_protected_route(self, jwt_client: TestClient) -> None:
        """A well-formed JWT signed with the configured secret passes verification.

        Tests the full auth stack end-to-end: HTTPBearer extraction → jose decode
        → UUID extraction → handler response.
        """
        # Arrange
        token = _mint_jwt()
        headers = {"Authorization": f"Bearer {token}"}

        # Act
        response = jwt_client.get("/api/v1/users/me", headers=headers)

        # Assert
        assert response.status_code == 200
        assert response.json()["id"] == TEST_USER_UUID


# ── Missing token ──────────────────────────────────────────────────────────────


class TestProtectedEndpointMissingToken:
    def test_returns_401_when_authorization_header_absent(
        self, jwt_client: TestClient
    ) -> None:
        """GET /api/v1/users/me without any Authorization header → 401.

        HTTPBearer sets credentials=None when the header is missing;
        get_current_user_id must raise 401 before attempting JWT decode.
        """
        # Arrange — deliberately send no Authorization header

        # Act
        response = jwt_client.get("/api/v1/users/me")

        # Assert
        assert response.status_code == 401
        assert "authenticated" in response.json()["detail"].lower()

    def test_returns_401_when_bearer_prefix_missing(
        self, jwt_client: TestClient
    ) -> None:
        """A raw token without the 'Bearer ' prefix is rejected with 401/403.

        HTTPBearer auto_error=False means a non-bearer scheme yields None
        credentials — the dependency must still refuse access.
        """
        # Arrange
        headers = {"Authorization": _mint_jwt()}  # no "Bearer " prefix

        # Act
        response = jwt_client.get("/api/v1/users/me", headers=headers)

        # Assert
        assert response.status_code in {401, 403}


# ── Invalid / tampered tokens ──────────────────────────────────────────────────


class TestProtectedEndpointInvalidToken:
    def test_returns_401_with_random_string_token(self, jwt_client: TestClient) -> None:
        """A token that is not a JWT structure at all is rejected with 401.

        python-jose raises JWTError on malformed input; get_current_user_id
        must catch it and surface a 401.
        """
        # Arrange
        headers = {"Authorization": "Bearer this.is.not.a.valid.jwt.at.all"}

        # Act
        response = jwt_client.get("/api/v1/users/me", headers=headers)

        # Assert
        assert response.status_code == 401
        assert "invalid token" in response.json()["detail"].lower()

    def test_returns_401_with_expired_token(self, jwt_client: TestClient) -> None:
        """A structurally valid JWT with an ``exp`` in the past is rejected.

        python-jose raises ExpiredSignatureError (a subclass of JWTError);
        get_current_user_id must surface that as 401, not 500.
        """
        # Arrange
        expired_token = _mint_jwt(expired=True)
        headers = {"Authorization": f"Bearer {expired_token}"}

        # Act
        response = jwt_client.get("/api/v1/users/me", headers=headers)

        # Assert
        assert response.status_code == 401

    def test_returns_401_with_wrong_secret(self, jwt_client: TestClient) -> None:
        """A JWT signed with a different secret is rejected as an invalid token.

        Simulates a forged or stolen token signed by an attacker's key;
        HMAC signature verification must fail and return 401.
        """
        # Arrange
        forged_token = _mint_jwt(secret="attacker-owned-secret-key-totally-different")
        headers = {"Authorization": f"Bearer {forged_token}"}

        # Act
        response = jwt_client.get("/api/v1/users/me", headers=headers)

        # Assert
        assert response.status_code == 401

    def test_returns_401_with_tampered_payload(self, jwt_client: TestClient) -> None:
        """A token whose payload was modified after signing is rejected.

        Constructs a JWT, then replaces the payload segment with a different
        base64-encoded sub claim — the signature no longer matches.
        """
        import base64
        import json

        # Arrange — build a valid token, then swap its payload segment
        valid_token = _mint_jwt()
        header_b64, _, sig_b64 = valid_token.split(".")

        tampered_claims = {
            "sub": "00000000-0000-0000-0000-000000000000",
            "role": "authenticated",
        }
        tampered_payload = (
            base64.urlsafe_b64encode(json.dumps(tampered_claims).encode())
            .rstrip(b"=")
            .decode()
        )
        tampered_token = f"{header_b64}.{tampered_payload}.{sig_b64}"
        headers = {"Authorization": f"Bearer {tampered_token}"}

        # Act
        response = jwt_client.get("/api/v1/users/me", headers=headers)

        # Assert
        assert response.status_code == 401


# ── Portfolio auto-initialization ──────────────────────────────────────────────


class TestPortfolioAutoInitializationOnLogin:
    def test_portfolio_created_with_default_balance_on_first_access(
        self, auth_client: tuple[TestClient, sessionmaker[Session]]
    ) -> None:
        """First call to GET /api/v1/users/me/portfolio auto-creates the account.

        A brand-new user (no prior Portfolio row) must receive a portfolio
        seeded with _DEFAULT_CASH ($100,000) rather than a 404.
        This mirrors the onboarding flow that fires after Supabase login.
        """
        # Arrange
        client, factory = auth_client
        headers = {"Authorization": "Bearer stubbed-valid-token"}

        db = factory()
        pre_existing = (
            db.query(Portfolio)
            .filter(Portfolio.user_id == UUID(TEST_USER_UUID))
            .first()
        )
        db.close()
        assert pre_existing is None, "No portfolio should exist before first login"

        # Act
        response = client.get("/api/v1/users/me/portfolio", headers=headers)

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["cash_balance"] == _DEFAULT_CASH
        assert isinstance(body["id"], int)
        assert body["user"] == TEST_USER_UUID

    def test_portfolio_idempotent_across_repeated_logins(
        self, auth_client: tuple[TestClient, sessionmaker[Session]]
    ) -> None:
        """Repeated calls to /me/portfolio return the *same* portfolio, not duplicates.

        _get_or_create_portfolio must behave idempotently — calling it N times
        for the same user_id must produce exactly one row in the DB.
        """
        # Arrange
        client, factory = auth_client
        headers = {"Authorization": "Bearer stubbed-valid-token"}

        # Act — simulate user logging in twice (page reload, session restore, etc.)
        resp1 = client.get("/api/v1/users/me/portfolio", headers=headers)
        resp2 = client.get("/api/v1/users/me/portfolio", headers=headers)

        # Assert — same portfolio ID both times
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json()["id"] == resp2.json()["id"]

        # Confirm exactly one row exists
        db = factory()
        row_count = (
            db.query(Portfolio)
            .filter(Portfolio.user_id == UUID(TEST_USER_UUID))
            .count()
        )
        db.close()
        assert row_count == 1

    def test_trades_list_empty_for_new_portfolio(
        self, auth_client: tuple[TestClient, sessionmaker[Session]]
    ) -> None:
        """A newly onboarded user has an empty trade history.

        GET /api/v1/users/me/trades must return [] — not 404 or an error —
        so the dashboard can render without a pre-populated account.
        """
        # Arrange
        client, _ = auth_client
        headers = {"Authorization": "Bearer stubbed-valid-token"}

        # Act
        response = client.get("/api/v1/users/me/trades", headers=headers)

        # Assert
        assert response.status_code == 200
        assert response.json() == []


# ── Misconfigured auth guard ───────────────────────────────────────────────────


class TestUnconfiguredAuth:
    def test_returns_503_when_supabase_jwt_secret_not_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When SUPABASE_JWT_SECRET is blank the endpoint returns 503.

        This guards against silent auth bypass in deployments where the secret
        env var was never injected — the API must refuse requests explicitly
        rather than accepting them as unauthenticated or crashing with 500.
        """
        # Arrange
        factory = _make_isolated_db()
        monkeypatch.setattr(settings, "supabase_jwt_secret", "")
        app.dependency_overrides[get_db] = _db_override(factory)

        try:
            with TestClient(app) as client:
                # Act
                response = client.get(
                    "/api/v1/users/me",
                    headers={"Authorization": "Bearer any-token-at-all"},
                )
        finally:
            app.dependency_overrides.pop(get_db, None)

        # Assert
        assert response.status_code == 503
        assert "auth not configured" in response.json()["detail"].lower()
