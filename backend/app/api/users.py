from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.models.portfolio import Portfolio
from app.models.position import Position
from app.models.profile import Profile
from app.models.trade import Trade
from app.schemas.api import ManualTradeRequest, PortfolioOut, TradeExecuted, TradeOut
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
    # Satisfy portfolios_user_id_fkey without a premature COMMIT: flush the
    # profile into the current transaction so the FK is resolvable when the
    # portfolio row is inserted in the same commit below.
    if db.get(Profile, user_id) is None:
        db.add(Profile(id=user_id))
        db.flush()
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
    # Clear any pending-rollback state on a recycled pool connection before
    # issuing the query — guards against f405 PendingRollbackError.
    db.rollback()
    try:
        rows = (
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
            for t in rows
        ]
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not load trade history — please retry.",
        )


@router.post("/me/trade", response_model=TradeExecuted, status_code=201)
def execute_manual_trade(
    body: ManualTradeRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> TradeExecuted:
    """Execute a manual paper trade at live market price."""
    # Discard any aborted-transaction state on a recycled pool connection.
    # Must happen before the first query so _get_or_create_portfolio is clean.
    db.rollback()
    try:
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

        # Snapshot the balance now — db.commit() below expires all ORM attributes,
        # so reading portfolio.cash_balance after commit would trigger a lazy reload.
        new_cash_balance = portfolio.cash_balance

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
        db.flush()
        db.commit()
        db.refresh(trade)

        return TradeExecuted(
            updated_cash_balance=new_cash_balance,
            trade=TradeOut(
                id=trade.id,
                symbol=trade.symbol,
                side=trade.side,
                qty=trade.qty,
                price=trade.price,
                rationale=trade.rationale,
                created_at=trade.created_at,
            ),
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Trade could not be saved — please retry.",
        )
