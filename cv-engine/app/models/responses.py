
from pydantic import BaseModel


class ATSReportResponse(BaseModel):
    score: float | None = None
    breakdown: dict = {}
    tiers: dict = {}
    parseability: dict = {}
    resume_quality: dict = {}
    frequency_recency: dict = {}
    missing_keywords: list[str] = []
    fixes: list[str] = []
    caveats: list[str] = []
    summary: str = ""
    source: str = ""


class TailoringResponse(BaseModel):
    score: float | None = None
    reason: str = ""
    must_have: list[str] = []
    nice_to_have: list[str] = []
    tools: list[str] = []
    concepts: list[str] = []
    soft_skills: list[str] = []
    experience_order: list[dict] = []
    highlights_per_entry: dict = {}
    ats: ATSReportResponse | None = None


class CVResponse(BaseModel):
    pdf_base64: str
    filename: str
    ats_score: float | None = None
    ats_breakdown: dict = {}
    tailored: bool = True
    sections_reordered: list[str] = []
    tailored_resume: str = ""
    gap_report: dict = {}
    source_trace: list = []
    suggested_keywords: list[str] = []
    ats_report: ATSReportResponse | None = None


class CoverLetterResponse(BaseModel):
    cover_letter: str
    template_used: str
    tailored: bool = False
