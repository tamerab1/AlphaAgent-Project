import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app import models  # noqa: F401  (register models on Base.metadata)
from app.api import api_router
from app.core.config import settings
from app.db.session import Base, engine

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("alphaagent")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AlphaAgent API starting up")
    logger.info(
        "Market data mode: %s",
        (
            "LIVE (Stooq/yfinance + Tavily)"
            if settings.market_data_live
            else "SEED (deterministic)"
        ),
    )
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables ensured")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not create database tables: %s", exc)
    yield
    logger.info("AlphaAgent API shutting down")


app = FastAPI(
    title="AlphaAgent API",
    version="1.0.0",
    description="AI-powered trading portfolio manager",
    lifespan=lifespan,
)

# Parse allowed origins from settings. We don't use cookies/credentials, so
# allow_credentials stays False — that keeps a "*" default spec-valid and lets
# production pin CORS_ORIGINS to the deployed frontend URL(s).
_cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins or ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)

app.include_router(api_router)


def _check_database() -> str:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return "missing"
    try:
        import psycopg2

        conn = psycopg2.connect(db_url, connect_timeout=3)
        conn.close()
        return "connected"
    except Exception as exc:
        logger.warning("Database health check failed: %s", exc)
        return "unreachable"


@app.get("/")
def read_root():
    return {"message": "Welcome to AlphaAgent AI Trading API"}


@app.get("/health")
def health_check():
    db_status = _check_database()
    return {
        "status": "healthy",
        "database_status": db_status,
        "environment": "production" if os.getenv("RENDER") else "development",
    }
