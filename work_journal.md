# AlphaAgent Project - Work Journal

| Date | Student Name | Role | Work Done | Time Spent | Problems Found | Next Step |
| :--- | :---         | :--- | :---      | :---       | :---           | :---      |

| 07/06/2026 | Tamer | DevOps | Created GitHub Repository, Monorepo structure, and configured .env.example | 2 hours | None | Prepare basic Dockerfile and Deployment setup |

||||||||
| 07/06/2026 | Sliman | DevOps | Successfully tested local PostgreSQL container baseline, verified multi-container Docker infrastructure. | 30 min | None | test backend container

||||||||
  07/06/2026 | Tamer | DevOps | Successfully provisioned a live cloud infrastructure, connecting Render (FastAPI Docker container) with Supabase (managed PostgreSQL) and verified successful public routing | 1 hour | connection between render to Supabase, Solved.



||||||||
| 08/06/2026 | Idan | Developer / AI lead | Phase 1 backend data layer: added config (pydantic-settings), database (SQLAlchemy engine/session/Base), 4 ORM models (Portfolio, Position, Trade, AgentRun), and wired create_all into the app lifespan. Phase 2 AI flow: built the LangGraph two-agent pipeline (ingest -> analyst -> risk -> execute/reject) with structured Pydantic outputs and an offline mock fallback for demo reliability. All green on CI: 30 tests, 98% coverage, black/flake8/bandit clean. | 4 hours | langchain forced pydantic/openai version bumps (2.6.4->2.13.4, 1.14.0->2.41.0) that conflicted with DevOps pins; verified no endpoint regressions. Resolved. | Phase 3 - market data service (price + RSI + headlines with seed/mock fallback) wired into the ingest node |

||||||||
| 08/06/2026 | Idan | Developer / AI lead | Phase 3 market data service: added get_market_data (seed data by default, live yfinance price/RSI + Tavily headlines behind a flag with per-field fallback) and wired it into the ingest node. Green: 39 tests, 99% coverage. | 1.5 hours | None | Phase 4 - /analyze SSE endpoint + SQL persistence (will need a running Postgres from DevOps) |

||||||||
| 08/06/2026 | Idan | Developer / AI lead | Phase 4 API layer: added the REST/SSE endpoints (portfolio, ai, trading + shared deps) - POST /portfolios, GET portfolio status, SSE /analyze-chart (LangGraph astream_events), agent-run logs, and paper-only toggle-mode. Streams node events live, then persists AgentRun + trades. Green: 53 tests, 99% coverage. | 2.5 hours | SSE generator runs after the endpoint returns, so the request-scoped DB session detaches and cash updates were silently lost; fixed by capturing the engine and opening a fresh session inside the stream. Resolved. | Restructure backend into an app/ package |

||||||||
| 08/06/2026 | Idan | Developer / AI lead | Backend restructure to industry-standard layout: moved everything under an app/ package (core/config, db/session, models/ one file per table, schemas/ agent+api, api/ routers + deps, services/ market_data+llm) and split the single graph.py into agents/graph.py + agents/risk.py + agents/nodes/ one file per node. Updated all imports, the Dockerfile entrypoint (main:app -> app.main:app), and tests. Green: 53 tests, 99% coverage. | 2 hours | flake8 flagged the relationship forward-refs (F821) and an app name collision in main.py; fixed with TYPE_CHECKING imports and a from-import. Resolved. | Phase 5 - Next.js frontend dashboard |

||||||||
| 09/06/2026 | Idan | Developer / AI lead | Phase 5 frontend dashboard: built the Next.js (App Router) dark-mode dashboard in TypeScript + Tailwind - summary cards (value/cash/positions/P&L), positions table, AI action log, paper/live toggle (live stays locked), and a Run Analysis button that opens the analyze-chart SSE stream and renders the analyst -> risk -> execute reasoning live, then refreshes the portfolio. Typed API client + a manual SSE frame reader. Smoke-tested the full click-through in a real browser against the live backend (FastAPI + Postgres): TSLA streamed every node, executed the BUY, cash 100k -> 95k, and the TSLA position + EXECUTED log appeared. Production build + lint clean. | 3 hours | EventSource is GET-only but our analyze-chart is a POST SSE, so I used fetch + a ReadableStream frame parser instead. A rogue local Postgres also shadowed compose's 5433 host mapping; used a throwaway Postgres on a free port for the smoke test. Resolved. | Phase 6 - demo polish (seed a 5-asset portfolio, lock the demo path) |

||||||||
| 09/06/2026 | Idan | Developer / AI lead | Phase 6 seed + SRS gap-closure: added backend/scripts/seed_demo.py (idempotent 5-asset demo portfolio with a winners/losers P&L mix + trade history, deterministic seed prices so it runs with live APIs off); added GET /api/portfolio/{id}/trades + TradeOut schema (SRS trade-history requirement) with 3 new tests; built the frontend Trade History panel (BUY/SELL badges, qty @ price, timestamp, rationale) wired into the dashboard. Also translated the Hebrew SRS to docs/SRS_EN.md and logged remaining tasks in DEV_PLAN §11. Backend green: 56 tests, 99% coverage, black/flake8/bandit clean; frontend build + lint clean. Verified live in-browser against a seeded Postgres. | 2.5 hours | next build clobbered the running next dev .next cache (Cannot find module / HTTP 500); fixed by stopping dev, clearing .next, restarting. Also root .gitignore lib/ rule was hiding frontend/lib (fixed last commit). Resolved. | SRS analyst target-price/stop-loss + Phase 7 multimodal chart upload |

||||||||




||||||||