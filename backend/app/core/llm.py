from functools import lru_cache

import anthropic

from app.core.config import settings

MODEL = "claude-opus-5"


@lru_cache
def get_anthropic_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)
