from fastapi import APIRouter

from app.api import ai, portfolio, trading

api_router = APIRouter()
api_router.include_router(portfolio.router)
api_router.include_router(ai.router)
api_router.include_router(trading.router)
