from typing import Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.billing.stripe_client import get_or_create_stripe_customer
from app.billing.tiers import TIERS
from app.core.config import settings
from app.core.db import get_db
from app.models.user import User

router = APIRouter(prefix="/billing", tags=["billing"])

_ACTIVE_STATUSES = {"active", "trialing", "past_due"}


@router.post("/checkout-session")
def create_checkout_session(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    customer_id = get_or_create_stripe_customer(user, db)
    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": settings.stripe_pro_price_id, "quantity": 1}],
        success_url=settings.checkout_success_url,
        cancel_url=settings.checkout_cancel_url,
        metadata={"user_id": user.id},
    )
    return {"checkout_url": session.url}


@router.post("/portal-session")
def create_portal_session(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not user.stripe_customer_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No billing account yet — start a checkout first.")
    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=settings.checkout_success_url,
    )
    return {"portal_url": session.url}


@router.get("/status")
def billing_status(user: User = Depends(get_current_user)):
    limits = TIERS[user.subscription_tier]
    return {
        "tier": user.subscription_tier,
        "status": user.subscription_status,
        "usage_count": user.usage_count,
        "monthly_limit": limits.monthly_limit,
        "auto_submit_enabled": limits.auto_submit,
        "current_period_end": user.current_period_end,
    }


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid webhook signature")

    handler = _EVENT_HANDLERS.get(event["type"])
    if handler:
        handler(event["data"]["object"], db)
    return {"received": True}


def _user_by_customer_id(customer_id: str, db: Session) -> Optional[User]:
    return db.query(User).filter(User.stripe_customer_id == customer_id).first()


def _apply_subscription_state(user: User, subscription: dict, db: Session) -> None:
    user.subscription_status = subscription["status"]
    user.current_period_end = None
    period_end = subscription.get("current_period_end")
    if period_end:
        from datetime import datetime, timezone

        user.current_period_end = datetime.fromtimestamp(period_end, tz=timezone.utc)
    user.subscription_tier = "pro" if subscription["status"] in _ACTIVE_STATUSES else "free"
    db.add(user)
    db.commit()


def _handle_checkout_completed(session: dict, db: Session) -> None:
    user = _user_by_customer_id(session["customer"], db)
    if not user or not session.get("subscription"):
        return
    subscription = stripe.Subscription.retrieve(session["subscription"])
    _apply_subscription_state(user, subscription, db)


def _handle_subscription_updated(subscription: dict, db: Session) -> None:
    user = _user_by_customer_id(subscription["customer"], db)
    if not user:
        return
    _apply_subscription_state(user, subscription, db)


def _handle_subscription_deleted(subscription: dict, db: Session) -> None:
    user = _user_by_customer_id(subscription["customer"], db)
    if not user:
        return
    user.subscription_tier = "free"
    user.subscription_status = "canceled"
    user.current_period_end = None
    db.add(user)
    db.commit()


_EVENT_HANDLERS = {
    "checkout.session.completed": _handle_checkout_completed,
    "customer.subscription.updated": _handle_subscription_updated,
    "customer.subscription.deleted": _handle_subscription_deleted,
}
