from unittest.mock import patch

from app.applications.types import FieldResult, FieldStatus, FillResult
from app.models.user import User
from tests.test_tailoring_api import _add_job, _fake_tailoring_result, _signup_and_headers, _upload_master_resume


def _make_pro_and_tailor(client, db_session, tmp_path, monkeypatch, email):
    headers = _signup_and_headers(client, email=email)
    _upload_master_resume(client, headers, tmp_path, monkeypatch)
    job_id = _add_job(client, headers)

    user = db_session.query(User).filter(User.email == email).first()
    user.subscription_tier = "pro"
    db_session.add(user)
    db_session.commit()

    with patch("app.api.tailoring.tailor_resume", return_value=_fake_tailoring_result()):
        resp = client.post("/tailoring", json={"job_posting_id": job_id}, headers=headers)
    return headers, resp.json()["id"]


def _fake_fill_result(ok=True) -> FillResult:
    return FillResult(
        ok=ok,
        fields=[
            FieldResult(field="name", status=FieldStatus.filled, detail="#name"),
            FieldResult(field="phone", status=FieldStatus.not_found, detail="selector not present"),
        ],
        screenshot_path="/tmp/fake-screenshot.png",
    )


def test_create_application_requires_pro_tier(client, tmp_path, monkeypatch):
    headers = _signup_and_headers(client, email="free-user@example.com")
    _upload_master_resume(client, headers, tmp_path, monkeypatch)
    job_id = _add_job(client, headers)
    with patch("app.api.tailoring.tailor_resume", return_value=_fake_tailoring_result()):
        tailor_resp = client.post("/tailoring", json={"job_posting_id": job_id}, headers=headers)

    resp = client.post(
        "/applications", json={"tailored_resume_id": tailor_resp.json()["id"]}, headers=headers
    )
    assert resp.status_code == 403


def test_full_prepare_confirm_flow(client, db_session, tmp_path, monkeypatch):
    headers, tailored_id = _make_pro_and_tailor(client, db_session, tmp_path, monkeypatch, "pro-flow@example.com")

    with patch("app.api.applications.run_fill", return_value=_fake_fill_result()) as mock_fill:
        resp = client.post("/applications", json={"tailored_resume_id": tailored_id}, headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "pending_review"
    assert body["has_screenshot"] is True
    assert any(f["field"] == "phone" and f["status"] == "not_found" for f in body["fields"])
    mock_fill.assert_called_once()
    application_id = body["id"]

    get_resp = client.get(f"/applications/{application_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "pending_review"

    with patch("app.api.applications.run_submit", return_value=None) as mock_submit:
        confirm_resp = client.post(f"/applications/{application_id}/confirm", headers=headers)
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["status"] == "submitted"
    assert confirm_resp.json()["submitted_at"] is not None
    mock_submit.assert_called_once()


def test_create_application_stays_drafted_on_fill_failure(client, db_session, tmp_path, monkeypatch):
    headers, tailored_id = _make_pro_and_tailor(client, db_session, tmp_path, monkeypatch, "fill-fail@example.com")

    with patch("app.api.applications.run_fill", return_value=_fake_fill_result(ok=False)):
        resp = client.post("/applications", json={"tailored_resume_id": tailored_id}, headers=headers)
    assert resp.status_code == 502


def test_confirm_fails_and_stays_pending_review_on_submit_error(client, db_session, tmp_path, monkeypatch):
    headers, tailored_id = _make_pro_and_tailor(client, db_session, tmp_path, monkeypatch, "submit-fail@example.com")

    with patch("app.api.applications.run_fill", return_value=_fake_fill_result()):
        resp = client.post("/applications", json={"tailored_resume_id": tailored_id}, headers=headers)
    application_id = resp.json()["id"]

    with patch("app.api.applications.run_submit", side_effect=RuntimeError("submit button not found")):
        confirm_resp = client.post(f"/applications/{application_id}/confirm", headers=headers)
    assert confirm_resp.status_code == 502

    get_resp = client.get(f"/applications/{application_id}", headers=headers)
    assert get_resp.json()["status"] == "pending_review"


def test_confirm_requires_pending_review_status(client, db_session, tmp_path, monkeypatch):
    headers, tailored_id = _make_pro_and_tailor(client, db_session, tmp_path, monkeypatch, "wrong-state@example.com")
    with patch("app.api.applications.run_fill", return_value=_fake_fill_result()):
        resp = client.post("/applications", json={"tailored_resume_id": tailored_id}, headers=headers)
    application_id = resp.json()["id"]

    client.post(f"/applications/{application_id}/reject", headers=headers)

    confirm_resp = client.post(f"/applications/{application_id}/confirm", headers=headers)
    assert confirm_resp.status_code == 409


def test_reject_does_not_require_pro_tier(client, tmp_path, monkeypatch, db_session):
    headers, tailored_id = _make_pro_and_tailor(client, db_session, tmp_path, monkeypatch, "reject-flow@example.com")
    with patch("app.api.applications.run_fill", return_value=_fake_fill_result()):
        resp = client.post("/applications", json={"tailored_resume_id": tailored_id}, headers=headers)
    application_id = resp.json()["id"]

    # Downgrade to free — reject should still work since it's not Pro-gated.
    user = db_session.query(User).filter(User.email == "reject-flow@example.com").first()
    user.subscription_tier = "free"
    db_session.add(user)
    db_session.commit()

    reject_resp = client.post(f"/applications/{application_id}/reject", headers=headers)
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "rejected_by_user"


def test_applications_not_visible_to_other_users(client, db_session, tmp_path, monkeypatch):
    headers_a, tailored_id = _make_pro_and_tailor(client, db_session, tmp_path, monkeypatch, "owner-a@example.com")
    with patch("app.api.applications.run_fill", return_value=_fake_fill_result()):
        resp = client.post("/applications", json={"tailored_resume_id": tailored_id}, headers=headers_a)
    application_id = resp.json()["id"]

    headers_b = _signup_and_headers(client, email="owner-b@example.com")
    get_resp = client.get(f"/applications/{application_id}", headers=headers_b)
    assert get_resp.status_code == 404
