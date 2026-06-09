from fastapi import APIRouter

from app.api import ai, market, portfolio, trading, users

api_router = APIRouter()
api_router.include_router(portfolio.router)
api_router.include_router(ai.router)
api_router.include_router(trading.router)
api_router.include_router(users.router)
api_router.include_router(market.router)
