import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.billing.usage import enforce_usage_limit
from app.core.config import settings
from app.core.db import get_db
from app.models.resume import MasterResume
from app.models.user import User
from app.resume_parser.parse import parse_resume_file

router = APIRouter(prefix="/resumes", tags=["resumes"])

ALLOWED_SUFFIXES = {".docx", ".pdf", ".md", ".markdown", ".txt"}


@router.post("", status_code=status.HTTP_201_CREATED)
def upload_master_resume(
    file: UploadFile,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unsupported file type: {suffix}")

    # Metered here, right before the billed (Claude-calling) step, rather than as a
    # route-level Depends — a Depends runs before this validation and would burn a
    # quota unit even on a request that gets rejected before ever calling Claude.
    enforce_usage_limit(db=db, user=user)

    storage_dir = Path(settings.resume_storage_dir) / user.id
    storage_dir.mkdir(parents=True, exist_ok=True)
    dest_path = storage_dir / file.filename
    with dest_path.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    parsed = parse_resume_file(str(dest_path))

    next_version = (
        db.query(func.max(MasterResume.version)).filter(MasterResume.user_id == user.id).scalar() or 0
    ) + 1
    resume = MasterResume(
        user_id=user.id,
        version=next_version,
        source_filename=file.filename,
        content=parsed.model_dump(),
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return {"id": resume.id, "version": resume.version, "content": resume.content}


@router.get("")
def list_master_resumes(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    resumes = (
        db.query(MasterResume)
        .filter(MasterResume.user_id == user.id)
        .order_by(MasterResume.version.desc())
        .all()
    )
    return [{"id": r.id, "version": r.version, "source_filename": r.source_filename} for r in resumes]


@router.get("/latest")
def get_latest_master_resume(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    resume = (
        db.query(MasterResume)
        .filter(MasterResume.user_id == user.id)
        .order_by(MasterResume.version.desc())
        .first()
    )
    if not resume:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No master resume uploaded yet")
    return {"id": resume.id, "version": resume.version, "content": resume.content}
