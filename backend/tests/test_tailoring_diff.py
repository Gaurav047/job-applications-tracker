from app.resume_parser.schema import Basics, JsonResume, SkillItem, WorkItem
from app.tailoring.diff import diff_resumes


def test_no_changes_yields_empty_diff():
    resume = JsonResume(basics=Basics(summary="Engineer"))
    assert diff_resumes(resume, resume.model_copy(deep=True)) == {}


def test_summary_change_detected():
    master = JsonResume(basics=Basics(summary="Backend engineer"))
    tailored = master.model_copy(deep=True)
    tailored.basics.summary = "Backend engineer specializing in payments"
    diff = diff_resumes(master, tailored)
    assert diff["basics"]["summary"]["before"] == "Backend engineer"
    assert "payments" in diff["basics"]["summary"]["after"]


def test_reordered_work_items_not_flagged_as_changed():
    job_a = WorkItem(name="Acme", position="Engineer", highlights=["Did A"])
    job_b = WorkItem(name="Widgets Inc", position="Junior Engineer", highlights=["Did B"])
    master = JsonResume(work=[job_a, job_b])
    tailored = JsonResume(work=[job_b.model_copy(), job_a.model_copy()])  # reordered, unchanged
    assert diff_resumes(master, tailored) == {}


def test_work_highlight_change_detected_by_identity_not_position():
    job_a = WorkItem(name="Acme", position="Engineer", highlights=["Did A"])
    job_b = WorkItem(name="Widgets Inc", position="Junior Engineer", highlights=["Did B"])
    master = JsonResume(work=[job_a, job_b])
    tailored_b = job_b.model_copy(deep=True)
    tailored_b.highlights = ["Did B, emphasizing relevant keywords"]
    tailored = JsonResume(work=[tailored_b, job_a.model_copy()])  # reordered AND job_b changed

    diff = diff_resumes(master, tailored)
    assert len(diff["work"]) == 1
    assert diff["work"][0]["company"] == "Widgets Inc"


def test_skills_reorder_detected_as_list_change():
    master = JsonResume(skills=[SkillItem(name="Python"), SkillItem(name="Go")])
    tailored = JsonResume(skills=[SkillItem(name="Go"), SkillItem(name="Python")])
    diff = diff_resumes(master, tailored)
    assert diff["skills"]["before"] == ["Python", "Go"]
    assert diff["skills"]["after"] == ["Go", "Python"]
