import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app import models  # noqa: F401  (register models on Base.metadata)
from app.api import api_router
from app.db.session import Base, engine

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("alphaagent")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AlphaAgent API starting up")
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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
