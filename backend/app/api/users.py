from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.models.portfolio import Portfolio
from app.models.position import Position
from app.models.profile import Profile
from app.models.trade import Trade
from app.schemas.api import ManualTradeRequest, PortfolioOut, TradeOut
from app.schemas.profile import ProfileRead, ProfileUpdate
from app.services import market_data

router = APIRouter(prefix="/api/v1/users", tags=["users"])

_DEFAULT_CASH = 100_000.0


# ── helpers ───────────────────────────────────────────────────────────────────


def _get_or_create_profile(db: Session, user_id: UUID) -> Profile:
    profile = db.get(Profile, user_id)
    if profile is None:
        profile = Profile(id=user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def _get_or_create_portfolio(db: Session, user_id: UUID) -> Portfolio:
    # Satisfy the portfolios_user_id_fkey constraint: the profiles row must
    # exist before we can insert a portfolio.  This matters for paper-trading
    # sessions where deps.py returns a synthetic UUID that has no Supabase
    # account behind it.
    _get_or_create_profile(db, user_id)
    portfolio = db.query(Portfolio).filter(Portfolio.user_id == user_id).first()
    if portfolio is None:
        portfolio = Portfolio(
            user=str(user_id),
            user_id=user_id,
            cash_balance=_DEFAULT_CASH,
        )
        db.add(portfolio)
        db.commit()
        db.refresh(portfolio)
    return portfolio


# ── profile routes ────────────────────────────────────────────────────────────


@router.get("/me", response_model=ProfileRead)
def get_my_profile(
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Profile:
    return _get_or_create_profile(db, user_id)


@router.patch("/me/trading-mode", response_model=ProfileRead)
def update_trading_mode(
    body: ProfileUpdate,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Profile:
    profile = _get_or_create_profile(db, user_id)
    profile.trading_mode = body.trading_mode
    db.commit()
    db.refresh(profile)
    return profile


# ── portfolio / trade routes (auth-scoped) ────────────────────────────────────


@router.get("/me/portfolio", response_model=PortfolioOut)
def get_my_portfolio(
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Portfolio:
    """Return the authenticated user's portfolio, creating one if it doesn't exist."""
    portfolio = _get_or_create_portfolio(db, user_id)
    return PortfolioOut(
        id=portfolio.id,
        user=portfolio.user,
        cash_balance=portfolio.cash_balance,
    )


@router.get("/me/trades", response_model=list[TradeOut])
def get_my_trades(
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[TradeOut]:
    """Return all trades belonging strictly to the authenticated user."""
    trades = (
        db.query(Trade)
        .filter(Trade.user_id == user_id)
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


@router.post("/me/trade", response_model=TradeOut, status_code=201)
def execute_manual_trade(
    body: ManualTradeRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> TradeOut:
    """Execute a manual paper trade at live market price."""
    portfolio = _get_or_create_portfolio(db, user_id)
    symbol = body.symbol.upper()

    price = market_data.get_execution_price(symbol)
    if price <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No price data for {symbol}",
        )
    if body.usd_amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount must be positive",
        )

    qty = body.usd_amount / price

    if body.side == "BUY":
        if body.usd_amount > portfolio.cash_balance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Insufficient cash balance. "
                    f"Available: ${portfolio.cash_balance:,.2f}"
                ),
            )
        portfolio.cash_balance -= body.usd_amount
        existing = (
            db.query(Position)
            .filter(
                Position.portfolio_id == portfolio.id,
                Position.symbol == symbol,
            )
            .first()
        )
        if existing:
            new_qty = existing.qty + qty
            existing.avg_price = (
                (existing.avg_price * existing.qty + price * qty) / new_qty
                if new_qty
                else price
            )
            existing.qty = new_qty
        else:
            db.add(
                Position(
                    portfolio_id=portfolio.id,
                    symbol=symbol,
                    qty=qty,
                    avg_price=price,
                )
            )
    else:  # SELL
        existing = (
            db.query(Position)
            .filter(
                Position.portfolio_id == portfolio.id,
                Position.symbol == symbol,
            )
            .first()
        )
        available = existing.qty if existing else 0.0
        if existing is None or existing.qty < qty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Insufficient position. "
                    f"Have {available:.4f} {symbol} "
                    f"(need {qty:.4f})"
                ),
            )
        portfolio.cash_balance += body.usd_amount
        existing.qty -= qty

    trade = Trade(
        portfolio_id=portfolio.id,
        user_id=user_id,
        symbol=symbol,
        side=body.side,
        qty=qty,
        price=price,
        rationale="Manual trade",
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)

    return TradeOut(
        id=trade.id,
        symbol=trade.symbol,
        side=trade.side,
        qty=trade.qty,
        price=trade.price,
        rationale=trade.rationale,
        created_at=trade.created_at,
    )
