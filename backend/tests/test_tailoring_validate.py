import pytest

from app.resume_parser.schema import Basics, EducationItem, JsonResume, ProjectItem, WorkItem
from app.tailoring.validate import FabricationError, assert_no_fabrication


def _master() -> JsonResume:
    return JsonResume(
        basics=Basics(name="Jane Doe", email="jane@example.com", phone="555-1234"),
        work=[WorkItem(name="Acme", position="Engineer", highlights=["Built things"])],
        education=[EducationItem(institution="State U", studyType="B.S.")],
        projects=[ProjectItem(name="Widget", description="A widget")],
    )


def test_rephrased_content_passes():
    master = _master()
    tailored = master.model_copy(deep=True)
    tailored.work[0].highlights = ["Built distributed things at scale"]
    assert_no_fabrication(master, tailored)  # should not raise


def test_fabricated_work_entry_raises():
    master = _master()
    tailored = master.model_copy(deep=True)
    tailored.work.append(WorkItem(name="FakeCorp", position="CEO", highlights=["Ran a company"]))
    with pytest.raises(FabricationError):
        assert_no_fabrication(master, tailored)


def test_fabricated_education_raises():
    master = _master()
    tailored = master.model_copy(deep=True)
    tailored.education.append(EducationItem(institution="Made Up University", studyType="PhD"))
    with pytest.raises(FabricationError):
        assert_no_fabrication(master, tailored)


def test_fabricated_project_raises():
    master = _master()
    tailored = master.model_copy(deep=True)
    tailored.projects.append(ProjectItem(name="Invented Project"))
    with pytest.raises(FabricationError):
        assert_no_fabrication(master, tailored)


def test_changed_contact_info_raises():
    master = _master()
    tailored = master.model_copy(deep=True)
    tailored.basics.email = "someone-else@example.com"
    with pytest.raises(FabricationError):
        assert_no_fabrication(master, tailored)
