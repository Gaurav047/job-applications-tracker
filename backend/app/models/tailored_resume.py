import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class TailoredResume(Base):
    __tablename__ = "tailored_resumes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    master_resume_id: Mapped[str] = mapped_column(String(36), ForeignKey("master_resumes.id"), nullable=False)
    job_posting_id: Mapped[str] = mapped_column(String(36), ForeignKey("job_postings.id"), nullable=False)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)  # tailored JSON Resume
    cover_letter: Mapped[str] = mapped_column(Text, nullable=True)
    diff: Mapped[dict] = mapped_column(JSON, nullable=True)  # field-level diff vs. master
    rendered_pdf_path: Mapped[str] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
