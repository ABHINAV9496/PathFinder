from pydantic import BaseModel
from typing import Optional


class TailoringResponse(BaseModel):
    score: Optional[float] = None
    reason: str = ""
    must_have: list[str] = []
    nice_to_have: list[str] = []
    tools: list[str] = []
    concepts: list[str] = []
    soft_skills: list[str] = []
    experience_order: list[dict] = []
    highlights_per_entry: dict = {}


class CVResponse(BaseModel):
    pdf_base64: str
    filename: str
    ats_score: Optional[float] = None
    ats_breakdown: dict = {}
    tailored: bool = True
    sections_reordered: list[str] = []


class CoverLetterResponse(BaseModel):
    cover_letter: str
    template_used: str
    tailored: bool = False
