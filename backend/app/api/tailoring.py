from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.billing.usage import enforce_usage_limit
from app.core.db import get_db
from app.models.job import JobPosting
from app.models.resume import MasterResume
from app.models.tailored_resume import TailoredResume
from app.models.user import User
from app.resume_parser.schema import JsonResume
from app.tailoring.diff import diff_resumes
from app.tailoring.tailor import tailor_resume
from app.tailoring.validate import FabricationError

router = APIRouter(prefix="/tailoring", tags=["tailoring"])


class CreateTailoringRequest(BaseModel):
    job_posting_id: str


def _latest_master_resume(user: User, db: Session) -> MasterResume:
    resume = (
        db.query(MasterResume)
        .filter(MasterResume.user_id == user.id)
        .order_by(MasterResume.version.desc())
        .first()
    )
    if not resume:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No master resume uploaded yet")
    return resume


@router.post("", status_code=status.HTTP_201_CREATED)
def create_tailored_resume(
    payload: CreateTailoringRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    master_resume = _latest_master_resume(user, db)
    job = db.get(JobPosting, payload.job_posting_id)
    if not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job posting not found")

    # Metered here, right before the billed (Claude-calling) step — see the
    # same reasoning in app/api/resumes.py::upload_master_resume.
    enforce_usage_limit(db=db, user=user)

    master = JsonResume.model_validate(master_resume.content)
    try:
        result = tailor_resume(master, job.description_text or "")
    except FabricationError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Tailoring failed validation: {exc}")

    diff = diff_resumes(master, result.resume)

    tailored = TailoredResume(
        master_resume_id=master_resume.id,
        job_posting_id=job.id,
        content=result.resume.model_dump(),
        cover_letter=result.cover_letter,
        diff=diff,
    )
    db.add(tailored)
    db.commit()
    db.refresh(tailored)
    return _serialize(tailored)


@router.get("")
def list_tailored_resumes(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (
        db.query(TailoredResume)
        .join(MasterResume, TailoredResume.master_resume_id == MasterResume.id)
        .filter(MasterResume.user_id == user.id)
        .order_by(TailoredResume.created_at.desc())
        .all()
    )
    return [
        {
            "id": t.id,
            "job_posting_id": t.job_posting_id,
            "created_at": t.created_at,
        }
        for t in rows
    ]


@router.get("/{tailored_resume_id}")
def get_tailored_resume(
    tailored_resume_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    tailored = (
        db.query(TailoredResume)
        .join(MasterResume, TailoredResume.master_resume_id == MasterResume.id)
        .filter(TailoredResume.id == tailored_resume_id, MasterResume.user_id == user.id)
        .first()
    )
    if not tailored:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tailored resume not found")
    return _serialize(tailored)


def _serialize(tailored: TailoredResume) -> dict:
    return {
        "id": tailored.id,
        "job_posting_id": tailored.job_posting_id,
        "content": tailored.content,
        "cover_letter": tailored.cover_letter,
        "diff": tailored.diff,
        "created_at": tailored.created_at,
    }
