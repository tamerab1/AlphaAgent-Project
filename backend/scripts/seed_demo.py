"""Seed a deterministic demo portfolio for presentations.

Idempotent: removes any existing portfolio for the given user (and its rows),
then recreates a 5-asset portfolio with a mix of winning/losing positions plus
trade history, so the dashboard opens on a populated, known-good state. Uses the
deterministic seed prices from ``market_data``, so it works with the live API
disabled.

Run from ``backend/`` with the venv active and DATABASE_URL pointing at the demo
DB::

    python scripts/seed_demo.py
    python scripts/seed_demo.py --user demo --cash 50000
"""

import argparse
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import Base, SessionLocal, engine  # noqa: E402
from app.models import AgentRun, Portfolio, Position, Trade  # noqa: E402
from app.models.base import utcnow  # noqa: E402
from app.services import market_data  # noqa: E402

# symbol -> (quantity, avg-price factor vs. current seed price).
# Factor < 1 => unrealized gain, > 1 => unrealized loss. A deliberate mix.
HOLDINGS = [
    ("AAPL", 60.0, 0.90),
    ("MSFT", 50.0, 1.05),
    ("TSLA", 40.0, 0.80),
    ("NVDA", 55.0, 1.10),
    ("GOOGL", 30.0, 0.95),
]

DEFAULT_CASH = 50000.0


def _reset_user(db, user: str) -> None:
    for portfolio in db.query(Portfolio).filter(Portfolio.user == user).all():
        pid = portfolio.id
        db.query(Trade).filter(Trade.portfolio_id == pid).delete()
        db.query(Position).filter(Position.portfolio_id == pid).delete()
        db.query(AgentRun).filter(AgentRun.portfolio_id == pid).delete()
        db.delete(portfolio)
    db.commit()


def seed(user: str = "demo", cash: float = DEFAULT_CASH) -> int:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        _reset_user(db, user)
        portfolio = Portfolio(user=user, cash_balance=cash)
        db.add(portfolio)
        db.flush()

        now = utcnow()
        for i, (symbol, qty, factor) in enumerate(HOLDINGS):
            price = market_data.get_market_data(symbol).price
            avg = round(price * factor, 2)
            db.add(
                Position(
                    portfolio_id=portfolio.id,
                    symbol=symbol,
                    qty=qty,
                    avg_price=avg,
                )
            )
            db.add(
                Trade(
                    portfolio_id=portfolio.id,
                    symbol=symbol,
                    side="BUY",
                    qty=qty,
                    price=avg,
                    rationale=f"Opened {symbol} on momentum + favorable RSI.",
                    created_at=now - timedelta(days=len(HOLDINGS) - i, hours=2),
                )
            )

        # A realized SELL so the trade history shows both sides.
        tsla_price = market_data.get_market_data("TSLA").price
        db.add(
            Trade(
                portfolio_id=portfolio.id,
                symbol="TSLA",
                side="SELL",
                qty=10.0,
                price=round(tsla_price * 0.95, 2),
                rationale="Trimmed TSLA to lock in partial gains.",
                created_at=now - timedelta(hours=6),
            )
        )

        db.commit()
        return portfolio.id
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed a demo portfolio.")
    parser.add_argument("--user", default="demo")
    parser.add_argument("--cash", type=float, default=DEFAULT_CASH)
    args = parser.parse_args()
    pid = seed(args.user, args.cash)
    print(f"Seeded demo portfolio id={pid} (user={args.user!r}).")
    print(
        "In the dashboard, set localStorage 'alphaagent_portfolio_id' to "
        f"{pid} to open this portfolio."
    )


if __name__ == "__main__":
    main()
