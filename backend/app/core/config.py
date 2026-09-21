from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE)

    database_url: str = "postgresql+psycopg2://localhost/job_apply_assistant"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24
    anthropic_api_key: str = ""
    resume_storage_dir: str = "./storage/resumes"
    rendered_pdf_dir: str = "./storage/rendered"
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_pro_price_id: str = ""
    checkout_success_url: str = "http://localhost:8000/billing/success"
    checkout_cancel_url: str = "http://localhost:8000/billing/cancel"
    voyage_api_key: str = ""
    rag_fake_embeddings: bool = False


settings = Settings()
