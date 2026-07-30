from pydantic import BaseModel
from typing import Optional


class JobIn(BaseModel):
    title: str = ""
    company: str = ""
    location: str = ""
    description: str = ""
    matched_skills: list[str] = []
    skill_gaps: list[str] = []
    skill_score_breakdown: dict = {}
    match_score: float = 0
    relevant_project: Optional[dict] = None


class ProfileIn(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    role: str = ""
    experience_years: int = 1
    experience_min: int = 0
    experience_max: int = 2
    location: str = ""
    github: str = ""
    linkedin: str = ""
    portfolio: str = ""
    skills: dict = {}
    projects: list[dict] = []
    experience: list[dict] = []
    education: str = ""
    languages: list[str] = []
    looking_for: list[str] = []


class CVRequest(BaseModel):
    job: JobIn
    profile: ProfileIn
    company_context: Optional[dict] = None


class TailorRequest(BaseModel):
    job: JobIn
    profile: ProfileIn
    company_context: Optional[dict] = None


class CoverLetterRequest(BaseModel):
    job: JobIn
    profile: ProfileIn


class EnrichRequest(BaseModel):
    company: str = ""
    apply_url: str = ""
