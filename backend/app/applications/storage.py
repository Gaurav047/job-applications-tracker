from pathlib import Path

from app.core.config import settings


def screenshot_path(user_id: str, application_id: str) -> str:
    d = Path(settings.screenshot_dir) / user_id
    d.mkdir(parents=True, exist_ok=True)
    return str(d / f"{application_id}.png")
