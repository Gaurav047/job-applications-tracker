"""Fast resume/job fit rating via Jev, TypeSafe's typed-decision model.

This is meant to run before a user commits to a full tailoring pass (which
calls Claude and counts against their usage quota): Jev is cheap and returns
in ~100ms, so it's a reasonable free check to show upfront.
"""
from typing import Optional

import httpx

from app.core.jev import system_one
from app.resume_parser.schema import JsonResume

FIT_LEVELS = ["poor", "weak", "moderate", "strong", "excellent"]


def score_resume_fit(master: JsonResume, job_description: str, client: Optional[httpx.Client] = None) -> dict:
    """Returns `{"fit": "moderate", "confidence": 0.7, "probabilities": {...}}`."""
    state = (
        f"Candidate's resume (JSON):\n{master.model_dump_json()}\n\n"
        f"Job posting description:\n{job_description}"
    )
    answers = system_one(
        state=state,
        questions={
            "fit": {
                "type": "score",
                "instructions": (
                    "Rate how well this candidate's resume matches the job "
                    "posting's requirements."
                ),
                "criteria": FIT_LEVELS,
            }
        },
        client=client,
    )
    fit = answers["fit"]
    # `score` is a continuous expected value over the rungs (e.g. 3.09), not
    # a discrete index — round it and look the label up in `legend`, which
    # maps each rung's stringified index to its criteria label.
    nearest_rung = str(round(fit["score"]))
    return {
        "fit": fit["legend"][nearest_rung],
        "confidence": fit["confidence"],
        "probabilities": fit["probabilities"],
    }
