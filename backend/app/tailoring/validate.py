"""Server-side guard against the tailoring step inventing content.

The tailoring prompt instructs Claude not to fabricate experience, but a
resume-writing tool that could put a job or degree on someone's resume they
never had is actively harmful to trust — so this is enforced in code, not
left to the prompt alone. It checks structural facts (which employers,
titles, and institutions appear), not wording, since rephrasing bullets and
reordering sections is exactly what tailoring is supposed to do.
"""
from app.resume_parser.schema import JsonResume


class FabricationError(ValueError):
    """Raised when a tailored resume contains work/education/projects not
    present in the master resume it was tailored from."""


def assert_no_fabrication(master: JsonResume, tailored: JsonResume) -> None:
    _assert_subset(
        {(w.name, w.position) for w in tailored.work},
        {(w.name, w.position) for w in master.work},
        "work entries",
    )
    _assert_subset(
        {(e.institution, e.studyType) for e in tailored.education},
        {(e.institution, e.studyType) for e in master.education},
        "education entries",
    )
    _assert_subset(
        {p.name for p in tailored.projects},
        {p.name for p in master.projects},
        "projects",
    )
    if (
        tailored.basics.name != master.basics.name
        or tailored.basics.email != master.basics.email
        or tailored.basics.phone != master.basics.phone
    ):
        raise FabricationError("Tailoring must not change name, email, or phone.")


def _assert_subset(after: set, before: set, label: str) -> None:
    extra = after - before
    if extra:
        raise FabricationError(f"Tailored resume introduced {label} not in the master resume: {extra}")
