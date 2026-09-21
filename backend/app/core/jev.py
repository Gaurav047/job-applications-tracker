"""Client for TypeSafe's Jev ("System One") model.

Jev returns typed, calibrated decisions (a score/choice/probability) instead
of prose, over a plain HTTP API — so this calls it directly with httpx
rather than adding the `typesafe-sdk` package, which requires Python >= 3.10
(this backend's venv is on 3.9).
"""
from functools import lru_cache
from typing import Optional

import httpx

from app.core.config import settings

JEV_API_URL = "https://api.typesafe.ai/v1/systemone"
JEV_MODEL = "jev-latest"


@lru_cache
def get_jev_client() -> httpx.Client:
    return httpx.Client(
        headers={"Authorization": f"Bearer {settings.typesafe_api_key}"},
        timeout=10.0,
    )


def system_one(state: str, questions: dict, client: Optional[httpx.Client] = None) -> dict:
    """Call Jev with a set of typed questions about `state`.

    `questions` maps a question key to a dict with `type` ("choice" | "score"
    | "noul"), `instructions`, and `criteria` (a dict of options for
    "choice", a list of scale labels for "score", omitted for "noul").

    Returns the `answers` dict from the response, keyed the same way as
    `questions`, e.g. `{"fit": {"type": "score", "score": 2, "confidence":
    0.81, "probabilities": {...}, "legend": {...}}}`.
    """
    client = client or get_jev_client()
    response = client.post(
        JEV_API_URL, json={"state": state, "model": JEV_MODEL, "questions": questions}
    )
    response.raise_for_status()
    return response.json()["answers"]
