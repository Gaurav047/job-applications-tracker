from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.applications import UnsupportedAtsError, run_fill, run_submit
from app.billing.usage import require_pro_tier
from app.core.config import settings
from app.core.db import get_db
from app.models.application import Application, ApplicationStatus
from app.models.job import JobPosting
from app.models.resume import MasterResume
from app.models.tailored_resume import TailoredResume
from app.models.user import User
from app.resume_parser.schema import JsonResume
from app.tailoring.render_pdf import render_tailored_resume_pdf

router = APIRouter(prefix="/applications", tags=["applications"])


class CreateApplicationRequest(BaseModel):
    tailored_resume_id: str


def _get_owned_application(application_id: str, db: Session, user: User) -> Application:
    app_row = (
        db.query(Application)
        .join(TailoredResume, Application.tailored_resume_id == TailoredResume.id)
        .join(MasterResume, TailoredResume.master_resume_id == MasterResume.id)
        .filter(Application.id == application_id, MasterResume.user_id == user.id)
        .first()
    )
    if not app_row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    return app_row


def _owned_tailored_resume(tailored_resume_id: str, db: Session, user: User) -> TailoredResume:
    tailored = (
        db.query(TailoredResume)
        .join(MasterResume, TailoredResume.master_resume_id == MasterResume.id)
        .filter(TailoredResume.id == tailored_resume_id, MasterResume.user_id == user.id)
        .first()
    )
    if not tailored:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tailored resume not found")
    return tailored


def _ensure_pdf(tailored: TailoredResume, user: User, db: Session) -> str:
    if not tailored.rendered_pdf_path or not Path(tailored.rendered_pdf_path).exists():
        dest = Path(settings.rendered_pdf_dir) / user.id / f"{tailored.id}.pdf"
        resume = JsonResume.model_validate(tailored.content)
        render_tailored_resume_pdf(resume, tailored.cover_letter or "", str(dest))
        tailored.rendered_pdf_path = str(dest)
        db.add(tailored)
        db.commit()
    return tailored.rendered_pdf_path


@router.post("", status_code=status.HTTP_201_CREATED)
def create_application(
    payload: CreateApplicationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _pro: User = Depends(require_pro_tier),
):
    """Phase 1: fills the real application form on the job's ATS and stops
    — never clicks submit. Status becomes `pending_review` on success, with
    a screenshot and field-by-field report to review before deciding
    whether to actually submit via POST /applications/{id}/confirm."""
    tailored = _owned_tailored_resume(payload.tailored_resume_id, db, user)
    job = db.get(JobPosting, tailored.job_posting_id)
    if not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job posting not found")

    pdf_path = _ensure_pdf(tailored, user, db)

    application = Application(
        job_posting_id=job.id,
        tailored_resume_id=tailored.id,
        status=ApplicationStatus.drafted,
        submission_mode="auto",
    )
    db.add(application)
    db.commit()
    db.refresh(application)

    try:
        resume = JsonResume.model_validate(tailored.content)
        result = run_fill(
            source=job.source,
            job_url=job.url,
            resume=resume,
            cover_letter=tailored.cover_letter or "",
            resume_pdf_path=pdf_path,
            user_id=user.id,
            application_id=application.id,
        )
    except UnsupportedAtsError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))

    if not result.ok:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Could not fill application form: {result.error}")

    application.status = ApplicationStatus.pending_review
    application.screenshot_path = result.screenshot_path
    application.fields = [
        {"field": f.field, "status": f.status.value, "detail": f.detail} for f in result.fields
    ]
    db.add(application)
    db.commit()
    db.refresh(application)
    return _serialize(application)


@router.get("")
def list_applications(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (
        db.query(Application)
        .join(TailoredResume, Application.tailored_resume_id == TailoredResume.id)
        .join(MasterResume, TailoredResume.master_resume_id == MasterResume.id)
        .filter(MasterResume.user_id == user.id)
        .order_by(Application.created_at.desc())
        .all()
    )
    return [
        {
            "id": a.id,
            "job_posting_id": a.job_posting_id,
            "status": a.status.value,
            "created_at": a.created_at,
        }
        for a in rows
    ]


@router.get("/{application_id}")
def get_application(application_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    application = _get_owned_application(application_id, db, user)
    return _serialize(application)


@router.get("/{application_id}/screenshot")
def get_application_screenshot(
    application_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    application = _get_owned_application(application_id, db, user)
    if not application.screenshot_path or not Path(application.screenshot_path).exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No screenshot available for this application")
    return FileResponse(application.screenshot_path, media_type="image/png")


@router.post("/{application_id}/confirm")
def confirm_application(
    application_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _pro: User = Depends(require_pro_tier),
):
    """Phase 2: the ONLY endpoint that actually clicks Submit on the real
    application form. Requires the application to be in pending_review (i.e.
    already reviewed via GET /applications/{id})."""
    application = _get_owned_application(application_id, db, user)
    if application.status != ApplicationStatus.pending_review:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Application must be pending_review to confirm (currently {application.status.value})",
        )

    tailored = db.get(TailoredResume, application.tailored_resume_id)
    job = db.get(JobPosting, application.job_posting_id)
    resume = JsonResume.model_validate(tailored.content)
    pdf_path = _ensure_pdf(tailored, user, db)

    try:
        run_submit(
            source=job.source,
            job_url=job.url,
            resume=resume,
            cover_letter=tailored.cover_letter or "",
            resume_pdf_path=pdf_path,
        )
    except Exception as exc:
        # Stays pending_review on failure — never marked submitted unless the
        # real submit control was actually clicked successfully.
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Submission failed: {exc}")

    application.status = ApplicationStatus.submitted
    application.submitted_at = datetime.now(timezone.utc)
    db.add(application)
    db.commit()
    db.refresh(application)
    return _serialize(application)


@router.post("/{application_id}/reject")
def reject_application(application_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Cancels a drafted/pending_review application. No Pro-gate: viewing
    and cancelling aren't the metered auto-fill/auto-submit capability."""
    application = _get_owned_application(application_id, db, user)
    if application.status not in (ApplicationStatus.drafted, ApplicationStatus.pending_review):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Application cannot be rejected from status {application.status.value}",
        )
    application.status = ApplicationStatus.rejected_by_user
    db.add(application)
    db.commit()
    db.refresh(application)
    return _serialize(application)


def _serialize(application: Application) -> dict:
    return {
        "id": application.id,
        "job_posting_id": application.job_posting_id,
        "tailored_resume_id": application.tailored_resume_id,
        "status": application.status.value,
        "submission_mode": application.submission_mode,
        "fields": application.fields,
        "has_screenshot": bool(application.screenshot_path),
        "submitted_at": application.submitted_at,
        "created_at": application.created_at,
    }
