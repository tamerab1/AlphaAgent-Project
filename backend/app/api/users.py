from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.models.profile import Profile
from app.schemas.profile import ProfileRead, ProfileUpdate

router = APIRouter(prefix="/api/v1/users", tags=["users"])


def _get_or_create_profile(db: Session, user_id: UUID) -> Profile:
    profile = db.get(Profile, user_id)
    if profile is None:
        profile = Profile(id=user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


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
