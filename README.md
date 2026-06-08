# AlphaAgent — AI Trading Portfolio Manager

AlphaAgent is an AI-powered backend system for automated trading analysis and portfolio management, built with FastAPI, PostgreSQL, and a full observability stack.

---

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌────────────┐
│   Client /  │────▶│  FastAPI Backend  │────▶│ PostgreSQL │
│  Frontend   │     │   (port 8000)     │     │ (port 5433)│
└─────────────┘     └──────────┬───────┘     └────────────┘
                               │ /metrics
                    ┌──────────▼───────┐
                    │    Prometheus     │
                    │   (port 9090)    │
                    └──────────┬───────┘
                               │
                    ┌──────────▼───────┐
                    │     Grafana       │
                    │   (port 3000)    │
                    └──────────────────┘
```

---

## Quick Start

### Prerequisites
- [Docker](https://www.docker.com/) + Docker Compose

### Run locally

```bash
# 1. Clone the repo
git clone https://github.com/Sliman1012/AlphaAgent-Project.git
cd AlphaAgent-Project

# 2. Set up environment variables
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys

# 3. Start all services
docker-compose up --build
```

All services start automatically. No manual configuration needed.

### Available services

| Service    | URL                          | Credentials  |
|------------|------------------------------|--------------|
| API        | http://localhost:8000        | —            |
| API Docs   | http://localhost:8000/docs   | —            |
| Prometheus | http://localhost:9090        | —            |
| Grafana    | http://localhost:3000        | admin / admin |

---

## API Endpoints

| Method | Endpoint   | Description                              |
|--------|------------|------------------------------------------|
| GET    | `/`        | Welcome message                          |
| GET    | `/health`  | Database + environment status            |
| GET    | `/metrics` | Prometheus metrics (request rate, etc.)  |
| GET    | `/docs`    | Interactive Swagger UI                   |

### Example responses

```bash
# Health check
curl http://localhost:8000/health
# {
#   "status": "healthy",
#   "database_status": "connected",
#   "environment": "development"
# }
```

---

## Running Tests

```bash
cd backend
pip install -r requirements-dev.txt

# Run all tests with coverage
pytest tests/ --cov=. --cov-report=term-missing

# Run a specific test class
pytest tests/test_endpoints.py::TestHealthEndpoint -v
```

Coverage must be ≥ 80% — the CI pipeline enforces this.

---

## CI/CD Pipeline

GitHub Actions runs automatically on every push and pull request to `Dev` and `main`.

```
push / PR
    │
    ▼
┌─────────────────────────┐
│  1. Code Quality        │  black (format) · flake8 (lint) · bandit (security)
└────────────┬────────────┘
             │ passes
             ▼
┌─────────────────────────┐
│  2. Tests & Coverage    │  pytest · coverage ≥ 80%
└────────────┬────────────┘
             │ passes
             ▼
┌─────────────────────────┐
│  3. Docker Build        │  builds image · smoke-tests /health endpoint
└─────────────────────────┘
```

If any stage fails, the merge is **blocked**.

---

## Monitoring

The Grafana dashboard loads automatically at http://localhost:3000.

**Dashboard panels:**
- Request Rate (req/s)
- Average Response Time
- Error Rate (%)
- Active Requests
- Requests by Endpoint
- Response Time Percentiles (p50 / p95 / p99)
- HTTP Status Code Distribution (2xx / 4xx / 5xx)

**Prometheus alert rules** (defined in `monitoring/alerts.yml`):

| Alert              | Condition                        | Severity |
|--------------------|----------------------------------|----------|
| `BackendDown`      | Backend unreachable > 1 min      | critical |
| `HighErrorRate`    | 5xx rate > 5% over 5 min         | warning  |
| `SlowResponseTime` | p95 latency > 1s over 5 min      | warning  |
| `HighRequestRate`  | Request rate > 100 req/s         | info     |

---

## Environment Variables

See [`backend/.env.example`](backend/.env.example) for all variables. Key ones:

| Variable            | Required | Description                        |
|---------------------|----------|------------------------------------|
| `DATABASE_URL`      | Yes      | PostgreSQL connection string        |
| `OPENAI_API_KEY`    | Yes      | OpenAI API key for AI analysis      |
| `EXCHANGE_API_KEY`  | Yes      | Exchange API key (Binance/Bybit)    |
| `EXCHANGE_SECRET_KEY` | Yes    | Exchange secret key                 |
| `LOG_LEVEL`         | No       | Logging level (default: `INFO`)     |

---

## Project Structure

```
AlphaAgent-Project/
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── requirements.txt        # Production dependencies
│   ├── requirements-dev.txt    # Dev + test dependencies
│   ├── setup.cfg               # Tool configuration (flake8, pytest, mypy)
│   ├── Dockerfile              # Container image (non-root, healthcheck)
│   ├── .env.example            # Environment variable template
│   └── tests/
│       ├── conftest.py         # Shared pytest fixtures
│       └── test_endpoints.py   # Endpoint tests
├── monitoring/
│   ├── prometheus.yml          # Scrape config + alert rules reference
│   ├── alerts.yml              # Prometheus alert rules
│   └── grafana/
│       └── provisioning/       # Auto-provisioned datasource + dashboard
├── .github/
│   └── workflows/
│       └── backend-ci.yml      # CI pipeline (quality → tests → docker)
├── docker-compose.yml          # Full local stack
└── README.md
```

---

## Contributing

1. Branch from `Dev` (never commit directly to `main`)
2. Write tests for every new feature
3. Run `black .` and `flake8 .` locally before pushing
4. Ensure the CI pipeline passes before requesting a review
5. Keep PRs focused — one feature or fix per PR

---

## Team

| Name   | Role              |
|--------|-------------------|
| Sliman & Tamer | DevOps / Backend  |
| Idan  | Backend / AI      |
| Ron & amit  | project managment & system analysis   |

