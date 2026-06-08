from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import utcnow

if TYPE_CHECKING:
    from app.models.portfolio import Portfolio


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.id"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    analyst_json: Mapped[str] = mapped_column(String, nullable=True)
    risk_json: Mapped[str] = mapped_column(String, nullable=True)
    executed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    portfolio: Mapped["Portfolio"] = relationship(back_populates="agent_runs")
