from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_portfolio_or_404
from app.db.session import get_db
from app.schemas.api import ToggleModeRequest, ToggleModeResponse

router = APIRouter(prefix="/api", tags=["trading"])


@router.post("/trading/{portfolio_id}/toggle-mode", response_model=ToggleModeResponse)
def toggle_mode(
    portfolio_id: int, body: ToggleModeRequest, db: Session = Depends(get_db)
):
    get_portfolio_or_404(db, portfolio_id)
    if body.mode == "live":
        return ToggleModeResponse(
            mode="paper",
            message="Live trading is disabled in this demo; staying in paper mode.",
        )
    return ToggleModeResponse(mode="paper", message="Paper trading mode active.")
