import stripe
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User

stripe.api_key = settings.stripe_secret_key


def get_or_create_stripe_customer(user: User, db: Session) -> str:
    if user.stripe_customer_id:
        return user.stripe_customer_id

    customer = stripe.Customer.create(email=user.email, metadata={"user_id": user.id})
    user.stripe_customer_id = customer["id"]
    db.add(user)
    db.commit()
    db.refresh(user)
    return user.stripe_customer_id
