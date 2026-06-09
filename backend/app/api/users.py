from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.models.portfolio import Portfolio
from app.models.profile import Profile
from app.models.trade import Trade
from app.schemas.api import PortfolioOut, TradeOut
from app.schemas.profile import ProfileRead, ProfileUpdate

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
