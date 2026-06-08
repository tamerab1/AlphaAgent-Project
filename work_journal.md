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




||||||||