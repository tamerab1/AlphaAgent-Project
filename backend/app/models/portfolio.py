from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import utcnow

if TYPE_CHECKING:
    from app.models.agent_run import AgentRun
    from app.models.position import Position
    from app.models.trade import Trade


class Portfolio(Base):
    __tablename__ = "portfolios"
    __table_args__ = (Index("ix_portfolios_user_id", "user_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user: Mapped[str] = mapped_column(String, nullable=False)
    # Supabase Auth UUID — nullable so existing anonymous portfolios are preserved.
    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    cash_balance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    positions: Mapped[list["Position"]] = relationship(back_populates="portfolio")
    trades: Mapped[list["Trade"]] = relationship(back_populates="portfolio")
    agent_runs: Mapped[list["AgentRun"]] = relationship(back_populates="portfolio")
