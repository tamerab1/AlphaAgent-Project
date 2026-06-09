from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, CheckConstraint, DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import utcnow

# Postgres-native types in production; portable fallbacks so the SQLite test
# database (and any non-Postgres backend) can still create the schema.
_UUID = PG_UUID(as_uuid=True).with_variant(String(36), "sqlite")
_JSON = JSONB().with_variant(JSON(), "sqlite")


class Profile(Base):
    __tablename__ = "profiles"
    __table_args__ = (
        CheckConstraint(
            "trading_mode IN ('Live', 'Paper')", name="ck_profiles_trading_mode"
        ),
        Index("ix_profiles_email", "email", unique=True),
    )

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    trading_mode: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default="Paper"
    )
    settings: Mapped[dict] = mapped_column(_JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )
