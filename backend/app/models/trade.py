from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import utcnow

if TYPE_CHECKING:
    from app.models.portfolio import Portfolio

# Portable UUID type: native PG UUID in production, String(36) in SQLite tests.
_UUID = PG_UUID(as_uuid=True).with_variant(String(36), "sqlite")


class Trade(Base):
    __tablename__ = "trades"
    __table_args__ = (Index("ix_trades_user_id", "user_id"),)

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=uuid4)
    portfolio_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("portfolios.id"), nullable=False
    )
    user_id: Mapped[UUID | None] = mapped_column(
        _UUID,
        ForeignKey("profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    asset_symbol: Mapped[str] = mapped_column(String, nullable=False)
    market_type: Mapped[str | None] = mapped_column(String, nullable=True)
    action: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    exit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    stop_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    take_profit: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str | None] = mapped_column(String, nullable=True)
    pnl: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_reasoning: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    portfolio: Mapped["Portfolio"] = relationship(back_populates="trades")
