from datetime import date

from app.billing.usage import _reset_if_new_period, enforce_usage_limit
from app.models.user import User


def _make_user(**overrides) -> User:
    defaults = dict(
        id="u1",
        email="u@example.com",
        password_hash="x",
        subscription_tier="free",
        usage_period_start=date.today().replace(day=1),
        usage_count=0,
    )
    defaults.update(overrides)
    return User(**defaults)


def test_reset_if_new_period_resets_stale_counter():
    user = _make_user(usage_period_start=date(2020, 1, 1), usage_count=4)
    _reset_if_new_period(user)
    assert user.usage_count == 0
    assert user.usage_period_start == date.today().replace(day=1)


def test_reset_if_new_period_leaves_current_period_alone():
    user = _make_user(usage_count=3)
    _reset_if_new_period(user)
    assert user.usage_count == 3


class FakeDB:
    def add(self, obj):
        pass

    def commit(self):
        pass

    def refresh(self, obj):
        pass


def test_enforce_usage_limit_increments_under_cap():
    user = _make_user(usage_count=0)
    result = _call_enforce(user)
    assert result.usage_count == 1


def _call_enforce(user):
    return enforce_usage_limit(db=FakeDB(), user=user)


def test_enforce_usage_limit_raises_at_cap():
    import pytest
    from fastapi import HTTPException

    user = _make_user(usage_count=5)  # free tier monthly_limit == 5
    with pytest.raises(HTTPException) as exc_info:
        _call_enforce(user)
    assert exc_info.value.status_code == 402


def test_enforce_usage_limit_pro_tier_has_higher_cap():
    user = _make_user(subscription_tier="pro", usage_count=5)
    result = _call_enforce(user)
    assert result.usage_count == 6
