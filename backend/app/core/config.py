from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = "postgresql+psycopg2://localhost/job_apply_assistant"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24
    anthropic_api_key: str = ""
    resume_storage_dir: str = "./storage/resumes"
    rendered_pdf_dir: str = "./storage/rendered"


settings = Settings()
