from dataclasses import dataclass


@dataclass(frozen=True)
class TierLimits:
    monthly_limit: int
    auto_submit: bool


# Tier *shape* is a code concern (tune here, no migration needed); per-user
# *state* (which tier, how much used) lives on the User model.
TIERS = {
    "free": TierLimits(monthly_limit=5, auto_submit=False),
    "pro": TierLimits(monthly_limit=100, auto_submit=True),
}
