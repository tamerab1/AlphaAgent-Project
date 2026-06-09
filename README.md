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

## How It Works — AI Trading Engine

The core of AlphaAgent is a **multi-agent decision pipeline** built with LangGraph and
`gpt-4o-mini`. It runs **paper trades only** (no real orders) — a deliberate design
choice: auto-executing real money off model output isn't responsible without guardrails
beyond this demo's scope.

A single analysis call streams a whole desk of agents debating one symbol, live over SSE:

```
POST /api/ai/{portfolio_id}/analyze-chart   ──▶  Server-Sent Events stream
        │
        ▼
  ┌──────────┐      ┌──────────────┐
  │  ingest  │─────▶│  🐂 bull     │──┐
  │ price,   │      │   analyst    │  │    ┌───────────┐    ┌───────────────┐
  │ RSI,MACD,│      └──────────────┘  ├──▶ │ ⚖️  judge │──▶ │ 🛡️  risk mgr  │──▶ execute
  │ MA50/200,│      ┌──────────────┐  │    │  verdict  │    │  (≤ 5% cap)   │      or
  │ S/R      │─────▶│  🐻 bear     │──┘    └───────────┘    └───────────────┘    reject
  └──────────┘      │   analyst    │
                    └──────────────┘
```

| Stage | What it does |
|-------|--------------|
| **ingest** | Pulls live price, RSI, MACD, 50/200-day moving averages and support/resistance for the symbol. |
| **bull / bear** | Two opposing analyst personas argue the strongest evidence-based case (BUY vs SELL), each returning a structured thesis, key points and conviction. They run **in parallel**. |
| **judge** | Weighs both cases against the technicals into a final `BUY / SELL / HOLD` with confidence, target price and stop-loss. |
| **risk manager** | A deterministic **5% position cap** (hard, non-overridable) plus an LLM judgment that can size down or veto within it. |
| **execute** | On approval, writes the paper trade and updates positions + cash; otherwise logs the rejection. |

**Structured & streamed.** Every agent returns a validated Pydantic object, and each
node's output is streamed to the dashboard so you watch the agents reason in real time
(`astream_events` → SSE). An optional chart screenshot is read by the multimodal model
and folded into the judge's decision.

### Core application API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/ai/{id}/analyze-chart` | Run the agent pipeline; SSE-streams each agent, then persists the run + any trade |
| `GET`  | `/api/ai/{id}/logs` | The AI action log — every decision and its rationale |
| `GET`  | `/api/portfolio/{id}/status` | Portfolio value, cash, open positions and live P&L |
| `GET`  | `/api/portfolio/{id}/trades` | Trade history (paper ledger) |
| `GET`  | `/api/market/{symbol}` | Live price, technical indicators and the AI read for one asset |
| `GET`  | `/api/ai/news` | AI-tagged market headlines with sentiment |

### Data model

| Table | Purpose |
|-------|---------|
| `portfolios` | Cash balance + ownership |
| `positions` | Open holdings (symbol, qty, average price) |
| `trades` | Executed paper trades with rationale |
| `agent_runs` | Each analysis run (analyst + risk JSON) — powers the AI action log |

---

## Quick Start

### Prerequisites
- [Docker](https://www.docker.com/) + Docker Compose

### Run locally

```bash
# 1. Clone the repo
git clone https://github.com/tamerab1/AlphaAgent-Project.git
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

