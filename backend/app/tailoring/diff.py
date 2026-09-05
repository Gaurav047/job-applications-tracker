"""Field-level diff between a master resume and its tailored variant, for the
review screen. Work/project items are matched by their identity (company +
position, or project name) rather than by list position, so Claude
reordering a more-relevant job to the top doesn't read as every item having
changed.
"""
from app.resume_parser.schema import JsonResume


def diff_resumes(master: JsonResume, tailored: JsonResume) -> dict:
    diff: dict = {}

    basics_diff = {}
    for field in ("label", "summary"):
        before, after = getattr(master.basics, field), getattr(tailored.basics, field)
        if before != after:
            basics_diff[field] = {"before": before, "after": after}
    if basics_diff:
        diff["basics"] = basics_diff

    work_diff = _diff_work_items(master.work, tailored.work)
    if work_diff:
        diff["work"] = work_diff

    project_diff = _diff_project_items(master.projects, tailored.projects)
    if project_diff:
        diff["projects"] = project_diff

    skills_before = [s.name for s in master.skills]
    skills_after = [s.name for s in tailored.skills]
    if skills_before != skills_after:
        diff["skills"] = {"before": skills_before, "after": skills_after}

    return diff


def _diff_work_items(before_items: list, after_items: list) -> list:
    before_by_key = {(w.name, w.position): w for w in before_items}
    changes = []
    for after in after_items:
        before = before_by_key.get((after.name, after.position))
        if before is None:
            continue  # guarded against separately by assert_no_fabrication
        if before.summary != after.summary or before.highlights != after.highlights:
            changes.append(
                {
                    "company": after.name,
                    "position": after.position,
                    "summary_before": before.summary,
                    "summary_after": after.summary,
                    "highlights_before": before.highlights,
                    "highlights_after": after.highlights,
                }
            )
    return changes


def _diff_project_items(before_items: list, after_items: list) -> list:
    before_by_name = {p.name: p for p in before_items}
    changes = []
    for after in after_items:
        before = before_by_name.get(after.name)
        if before is None:
            continue
        if before.description != after.description or before.highlights != after.highlights:
            changes.append(
                {
                    "name": after.name,
                    "description_before": before.description,
                    "description_after": after.description,
                    "highlights_before": before.highlights,
                    "highlights_after": after.highlights,
                }
            )
    return changes
