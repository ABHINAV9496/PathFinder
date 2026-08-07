from fastapi import APIRouter, Depends

from app.core.ats_engine import analyze, analyze_with_llm
from app.core.keyword_extractor import extract_jd_keywords
from app.core.tailor_engine import tailor_cv
from app.deps import verify_service_key
from app.models.requests import TailorRequest
from app.models.responses import ATSReportResponse, TailoringResponse

router = APIRouter(prefix="/v1", tags=["tailor"])


@router.post("/tailor", response_model=TailoringResponse)
async def tailor(request: TailorRequest, _auth: bool = Depends(verify_service_key)):
    job_dict = request.job.model_dump()
    profile_dict = request.profile.model_dump()
    company_context = request.company_context

    result = tailor_cv(job_dict, profile_dict, company_context=company_context)

    jd_text = f"{job_dict.get('title', '')} {job_dict.get('description', '')}"
    keywords = extract_jd_keywords(jd_text, profile_dict)

    resume_text = profile_dict.get("resume_text", "") or ""
    if request.ai_config:
        ats_data = analyze_with_llm(
            jd_text, resume_text, profile_dict,
            request.ai_config, prompt_version=request.ats_prompt_version,
        )
    else:
        ats_report = analyze(jd_text, resume_text, profile_dict)
        ats_data = {
            "score": ats_report.score,
            "breakdown": ats_report.breakdown,
            "tiers": ats_report.tiers,
            "parseability": ats_report.parseability,
            "resume_quality": ats_report.resume_quality,
            "frequency_recency": ats_report.frequency_recency,
            "missing_keywords": ats_report.missing_keywords,
            "fixes": ats_report.fixes,
            "caveats": ats_report.caveats,
            "summary": ats_report.summary,
            "source": ats_report.source,
        }

    ats = ATSReportResponse(**ats_data)

    return TailoringResponse(
        score=result.ats_score,
        reason=ats_data.get("source") or "deterministic_tailoring",
        must_have=keywords["must_have"],
        nice_to_have=keywords["nice_to_have"],
        tools=keywords["tools"],
        concepts=keywords["concepts"],
        soft_skills=keywords["soft_skills"],
        experience_order=[e for e in result.experience_order],
        highlights_per_entry=result.highlights_per_entry,
        ats=ats,
    )
