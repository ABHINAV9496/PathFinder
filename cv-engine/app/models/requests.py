
from pydantic import BaseModel


class JobIn(BaseModel):
    title: str = ""
    company: str = ""
    location: str = ""
    description: str = ""
    matched_skills: list[str] = []
    skill_gaps: list[str] = []
    skill_score_breakdown: dict = {}
    match_score: float = 0
    relevant_project: dict | None = None


class ProfileIn(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    role: str = ""
    experience_years: int = 1
    experience_min: int = 0
    experience_max: int = 2
    location: str = ""
    country: str = ""
    currency: str = ""
    min_salary: int = 0
    github: str = ""
    linkedin: str = ""
    portfolio: str = ""
    skills: dict = {}
    projects: list[dict] = []
    experience: list[dict] = []
    education: str = ""
    languages: list[str] = []
    looking_for: list[str] = []
    excluded_roles: list[str] = []
    excluded_locations: list[str] = []
    resume_text: str = ""


class CVRequest(BaseModel):
    job: JobIn
    profile: ProfileIn
    company_context: dict | None = None


class TailorRequest(BaseModel):
    job: JobIn
    profile: ProfileIn
    company_context: dict | None = None
    ai_config: dict | None = None
    ats_prompt_version: str = "v3"


class CoverLetterRequest(BaseModel):
    job: JobIn
    profile: ProfileIn


class EnrichRequest(BaseModel):
    company: str = ""
    apply_url: str = ""
