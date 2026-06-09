from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_optional_user_id, get_portfolio_or_404
from app.db.session import get_db
from app.models import Portfolio, Trade
from app.schemas.api import (
    PortfolioCreate,
    PortfolioOut,
    PortfolioStatus,
    PositionOut,
    TradeOut,
)
from app.services import market_data

router = APIRouter(prefix="/api", tags=["portfolio"])


def _assert_portfolio_access(portfolio: Portfolio, caller_id: Optional[UUID]) -> None:
    """Raise 403 if the portfolio is user-scoped and the caller doesn't own it."""
    if portfolio.user_id is not None and caller_id is not None:
        if portfolio.user_id != caller_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )


@router.post("/portfolios", response_model=PortfolioOut, status_code=201)
def create_portfolio(
    body: PortfolioCreate,
    db: Session = Depends(get_db),
    caller_id: Optional[UUID] = Depends(get_optional_user_id),
):
    portfolio = Portfolio(
        user=body.user,
        user_id=caller_id,
        cash_balance=body.cash_balance,
    )
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return PortfolioOut(
        id=portfolio.id, user=portfolio.user, cash_balance=portfolio.cash_balance
    )


@router.get("/portfolio/{portfolio_id}/status", response_model=PortfolioStatus)
def portfolio_status(
    portfolio_id: int,
    db: Session = Depends(get_db),
    caller_id: Optional[UUID] = Depends(get_optional_user_id),
):
    portfolio = get_portfolio_or_404(db, portfolio_id)
    _assert_portfolio_access(portfolio, caller_id)
    positions_out: list[PositionOut] = []
    positions_value = 0.0
    unrealized = 0.0
    for pos in portfolio.positions:
        price = market_data.get_market_data(pos.symbol).price
        market_value = price * pos.qty
        pnl = (price - pos.avg_price) * pos.qty
        positions_value += market_value
        unrealized += pnl
        positions_out.append(
            PositionOut(
                symbol=pos.symbol,
                qty=pos.qty,
                avg_price=pos.avg_price,
                current_price=price,
                market_value=market_value,
                unrealized_pnl=pnl,
            )
        )
    return PortfolioStatus(
        id=portfolio.id,
        user=portfolio.user,
        cash_balance=portfolio.cash_balance,
        positions_value=positions_value,
        total_value=portfolio.cash_balance + positions_value,
        unrealized_pnl=unrealized,
        positions=positions_out,
    )


@router.get("/portfolio/{portfolio_id}/trades", response_model=list[TradeOut])
def portfolio_trades(
    portfolio_id: int,
    db: Session = Depends(get_db),
    caller_id: Optional[UUID] = Depends(get_optional_user_id),
):
    portfolio = get_portfolio_or_404(db, portfolio_id)
    _assert_portfolio_access(portfolio, caller_id)
    trades = (
        db.query(Trade)
        .filter(Trade.portfolio_id == portfolio_id)
        .order_by(Trade.created_at.desc())
        .all()
    )
    return [
        TradeOut(
            id=t.id,
            symbol=t.symbol,
            side=t.side,
            qty=t.qty,
            price=t.price,
            rationale=t.rationale,
            created_at=t.created_at,
        )
        for t in trades
    ]
