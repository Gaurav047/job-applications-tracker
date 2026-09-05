"""Pydantic model for the JSON Resume schema (jsonresume.org), trimmed to the
fields this app actually reads/writes. Using an established open schema means
we don't invent a bespoke resume format and can reuse existing JSON Resume
themes/renderers later if we want.
"""
from typing import Optional

from pydantic import BaseModel, Field


class Basics(BaseModel):
    name: str = ""
    label: str = ""
    email: str = ""
    phone: str = ""
    summary: str = ""
    location: dict = Field(default_factory=dict)
    profiles: list[dict] = Field(default_factory=list)


class WorkItem(BaseModel):
    name: str = ""  # company
    position: str = ""
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    summary: str = ""
    highlights: list[str] = Field(default_factory=list)


class EducationItem(BaseModel):
    institution: str = ""
    studyType: str = ""
    area: str = ""
    startDate: Optional[str] = None
    endDate: Optional[str] = None


class SkillItem(BaseModel):
    name: str = ""
    keywords: list[str] = Field(default_factory=list)


class ProjectItem(BaseModel):
    name: str = ""
    description: str = ""
    highlights: list[str] = Field(default_factory=list)


class JsonResume(BaseModel):
    basics: Basics = Field(default_factory=Basics)
    work: list[WorkItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)
    skills: list[SkillItem] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    certificates: list[dict] = Field(default_factory=list)
