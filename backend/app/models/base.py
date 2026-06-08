from datetime import datetime, timezone


def utcnow() -> datetime:
    """Timezone-aware UTC now, used as a column default across models."""
    return datetime.now(timezone.utc)
