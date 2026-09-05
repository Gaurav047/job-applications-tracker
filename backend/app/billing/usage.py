from datetime import date

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.billing.tiers import TIERS
from app.core.db import get_db
from app.models.user import User


def _reset_if_new_period(user: User) -> None:
    current_period = date.today().replace(day=1)
    if user.usage_period_start < current_period:
        user.usage_period_start = current_period
        user.usage_count = 0


def enforce_usage_limit(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> User:
    """Gate + meter one billed (LLM-calling) action. Reused by every endpoint
    that spends Anthropic API credits, so the monthly cap is enforced in one
    place regardless of which feature triggers it.
    """
    _reset_if_new_period(user)
    limits = TIERS[user.subscription_tier]
    if user.usage_count >= limits.monthly_limit:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            f"Monthly usage limit ({limits.monthly_limit}) reached for the "
            f"'{user.subscription_tier}' tier. Upgrade to Pro for a higher limit.",
        )
    user.usage_count += 1
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def require_pro_tier(user: User = Depends(get_current_user)) -> User:
    """Feature gate for Pro-only capabilities (e.g. auto-submitting applications)."""
    limits = TIERS[user.subscription_tier]
    if not limits.auto_submit:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "This feature requires a Pro subscription."
        )
    return user
