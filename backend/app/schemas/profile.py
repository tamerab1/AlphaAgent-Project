from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str | None
    email: str | None
    trading_mode: Literal["Live", "Paper"]
    settings: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ProfileUpdate(BaseModel):
    trading_mode: Literal["Live", "Paper"]
