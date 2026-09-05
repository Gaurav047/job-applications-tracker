import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import Date, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def _first_of_this_month() -> date:
    return date.today().replace(day=1)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Billing / subscription state (see app/billing/)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    subscription_tier: Mapped[str] = mapped_column(String(16), nullable=False, default="free")
    subscription_status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    current_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    usage_period_start: Mapped[date] = mapped_column(Date, nullable=False, default=_first_of_this_month)
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
