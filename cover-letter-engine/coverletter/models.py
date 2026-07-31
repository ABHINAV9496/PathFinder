
from pydantic import BaseModel


class JobIn(BaseModel):
    id: int | None = None
    title: str = ""
    company: str = ""
    location: str = ""
    description: str = ""
    matched_skills: list[str] = []
    skill_gaps: list[str] = []
    missing_keywords: list[str] = []


class ProfileIn(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    role: str = ""
    experience_years: int = 1
    location: str = ""
    country: str = ""
    open_to_relocation: str = ""
    availability: str = ""
    github: str = ""
    linkedin: str = ""
    portfolio: str = ""
    skills: dict = {}
    projects: list[dict] = []
    experience: list[dict] = []
    education: str = ""


class AIConfigIn(BaseModel):
    api_key: str = ""
    api_base_url: str = ""
    model: str = ""
    provider: str = ""


class GenerateRequest(BaseModel):
    job: JobIn
    profile: ProfileIn
    mode: str = "template"  # "template" | "ai"
    resume_text: str = ""
    ai: AIConfigIn | None = None


class GenerateResponse(BaseModel):
    cover_letter: str
    template_used: str
    tailored: bool = False
    mode: str = "template"
    issues: list[str] = []
