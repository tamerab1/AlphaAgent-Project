from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestRootEndpoint:
    def test_returns_200(self):
        assert client.get("/").status_code == 200

    def test_returns_correct_message(self):
        assert client.get("/").json() == {
            "message": "Welcome to AlphaAgent AI Trading API"
        }

    def test_method_not_allowed(self):
        assert client.post("/").status_code == 405


class TestHealthEndpoint:
    def test_returns_200(self):
        assert client.get("/health").status_code == 200

    def test_status_is_always_healthy(self):
        assert client.get("/health").json()["status"] == "healthy"

    def test_response_shape(self):
        data = client.get("/health").json()
        assert {"status", "database_status", "environment"} <= data.keys()

    def test_database_missing_without_env(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        assert client.get("/health").json()["database_status"] == "missing"

    def test_database_unreachable_with_bad_url(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://bad:bad@localhost:9999/test")
        assert client.get("/health").json()["database_status"] == "unreachable"

    def test_environment_development_without_render(self, monkeypatch):
        monkeypatch.delenv("RENDER", raising=False)
        assert client.get("/health").json()["environment"] == "development"

    def test_environment_production_with_render(self, monkeypatch):
        monkeypatch.setenv("RENDER", "true")
        assert client.get("/health").json()["environment"] == "production"


class TestMetricsEndpoint:
    def test_returns_200(self):
        assert client.get("/metrics").status_code == 200

    def test_content_type_is_text(self):
        response = client.get("/metrics")
        assert "text/plain" in response.headers["content-type"]

    def test_contains_http_requests_metric(self):
        response = client.get("/metrics")
        assert b"http_requests_total" in response.content
