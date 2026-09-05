import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ApplicationStatus(str, enum.Enum):
    drafted = "drafted"
    pending_review = "pending_review"
    submitted = "submitted"
    rejected_by_user = "rejected_by_user"
    outcome_rejected = "outcome_rejected"
    outcome_interview = "outcome_interview"


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_posting_id: Mapped[str] = mapped_column(String(36), ForeignKey("job_postings.id"), nullable=False)
    tailored_resume_id: Mapped[str] = mapped_column(String(36), ForeignKey("tailored_resumes.id"), nullable=False)
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus), nullable=False, default=ApplicationStatus.drafted
    )
    submission_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")  # "auto" | "manual"
    submitted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
