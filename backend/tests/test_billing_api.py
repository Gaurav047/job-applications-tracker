from unittest.mock import MagicMock, patch

from app.models.user import User


def _signup_and_token(client, email="billing-user@example.com"):
    resp = client.post("/auth/signup", json={"email": email, "password": "secret123"})
    return resp.json()["access_token"]


def _auth_headers(client, email="billing-user@example.com"):
    return {"Authorization": f"Bearer {_signup_and_token(client, email)}"}


def test_checkout_session_creates_customer_and_session(client):
    headers = _auth_headers(client)
    fake_session = MagicMock(url="https://checkout.stripe.com/pay/cs_test_123")

    with patch("app.billing.stripe_client.stripe.Customer.create", return_value={"id": "cus_123"}) as create_customer, \
         patch("app.api.billing.stripe.checkout.Session.create", return_value=fake_session) as create_session:
        resp = client.post("/billing/checkout-session", headers=headers)

    assert resp.status_code == 200
    assert resp.json()["checkout_url"] == "https://checkout.stripe.com/pay/cs_test_123"
    create_customer.assert_called_once()
    _, kwargs = create_session.call_args
    assert kwargs["customer"] == "cus_123"
    assert kwargs["mode"] == "subscription"


def test_checkout_session_reuses_existing_customer(client, db_session):
    headers = _auth_headers(client, email="reuse@example.com")
    user = db_session.query(User).filter(User.email == "reuse@example.com").first()
    user.stripe_customer_id = "cus_existing"
    db_session.add(user)
    db_session.commit()

    fake_session = MagicMock(url="https://checkout.stripe.com/pay/cs_test_456")
    with patch("app.billing.stripe_client.stripe.Customer.create") as create_customer, \
         patch("app.api.billing.stripe.checkout.Session.create", return_value=fake_session):
        resp = client.post("/billing/checkout-session", headers=headers)

    assert resp.status_code == 200
    create_customer.assert_not_called()


def test_portal_session_requires_existing_customer(client):
    headers = _auth_headers(client, email="no-customer@example.com")
    resp = client.post("/billing/portal-session", headers=headers)
    assert resp.status_code == 400


def test_billing_status_defaults_to_free_tier(client):
    headers = _auth_headers(client, email="status@example.com")
    resp = client.get("/billing/status", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["tier"] == "free"
    assert body["monthly_limit"] == 5
    assert body["usage_count"] == 0


def test_webhook_rejects_invalid_signature(client):
    with patch("app.api.billing.stripe.Webhook.construct_event", side_effect=ValueError("bad payload")):
        resp = client.post("/billing/webhook", content=b"{}", headers={"stripe-signature": "bad"})
    assert resp.status_code == 400


def test_webhook_checkout_completed_upgrades_user_to_pro(client, db_session):
    headers = _auth_headers(client, email="webhook-user@example.com")
    user = db_session.query(User).filter(User.email == "webhook-user@example.com").first()
    user.stripe_customer_id = "cus_webhook"
    db_session.add(user)
    db_session.commit()

    fake_event = {
        "type": "checkout.session.completed",
        "data": {"object": {"customer": "cus_webhook", "subscription": "sub_123"}},
    }
    fake_subscription = {"status": "active", "current_period_end": 1900000000, "customer": "cus_webhook"}

    with patch("app.api.billing.stripe.Webhook.construct_event", return_value=fake_event), \
         patch("app.api.billing.stripe.Subscription.retrieve", return_value=fake_subscription):
        resp = client.post("/billing/webhook", content=b"{}", headers={"stripe-signature": "valid"})

    assert resp.status_code == 200
    db_session.refresh(user)
    assert user.subscription_tier == "pro"
    assert user.subscription_status == "active"
    assert user.current_period_end is not None


def test_webhook_subscription_deleted_downgrades_to_free(client, db_session):
    headers = _auth_headers(client, email="downgrade@example.com")
    user = db_session.query(User).filter(User.email == "downgrade@example.com").first()
    user.stripe_customer_id = "cus_downgrade"
    user.subscription_tier = "pro"
    user.subscription_status = "active"
    db_session.add(user)
    db_session.commit()

    fake_event = {
        "type": "customer.subscription.deleted",
        "data": {"object": {"customer": "cus_downgrade"}},
    }
    with patch("app.api.billing.stripe.Webhook.construct_event", return_value=fake_event):
        resp = client.post("/billing/webhook", content=b"{}", headers={"stripe-signature": "valid"})

    assert resp.status_code == 200
    db_session.refresh(user)
    assert user.subscription_tier == "free"
    assert user.subscription_status == "canceled"
