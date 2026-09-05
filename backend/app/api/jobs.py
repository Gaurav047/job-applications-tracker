from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.job_sources import JobNotFoundError, UnsupportedJobBoardError, fetch_job_posting
from app.models.job import JobPosting
from app.models.user import User

router = APIRouter(prefix="/jobs", tags=["jobs"])


class AddJobRequest(BaseModel):
    url: str


@router.post("", status_code=status.HTTP_201_CREATED)
def add_job_posting(
    payload: AddJobRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        fetched = fetch_job_posting(payload.url)
    except UnsupportedJobBoardError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    except JobNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))

    job = JobPosting(
        source=fetched.source,
        url=fetched.url,
        company=fetched.company,
        title=fetched.title,
        description_text=fetched.description_text,
        raw_payload=fetched.raw_payload,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return {
        "id": job.id,
        "source": job.source,
        "company": job.company,
        "title": job.title,
        "description_text": job.description_text,
    }


@router.get("")
def list_job_postings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    jobs = db.query(JobPosting).order_by(JobPosting.created_at.desc()).all()
    return [
        {"id": j.id, "source": j.source, "company": j.company, "title": j.title, "url": j.url}
        for j in jobs
    ]
