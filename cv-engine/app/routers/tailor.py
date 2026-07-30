from fastapi import APIRouter, Depends
from app.deps import verify_service_key
from app.models.requests import TailorRequest
from app.models.responses import TailoringResponse
from app.core.tailor_engine import tailor_cv
from app.core.keyword_extractor import extract_jd_keywords

router = APIRouter(prefix="/v1", tags=["tailor"])


@router.post("/tailor", response_model=TailoringResponse)
async def tailor(request: TailorRequest, _auth: bool = Depends(verify_service_key)):
    job_dict = request.job.model_dump()
    profile_dict = request.profile.model_dump()
    company_context = request.company_context

    result = tailor_cv(job_dict, profile_dict, company_context=company_context)

    jd_text = f"{job_dict.get('title', '')} {job_dict.get('description', '')}"
    keywords = extract_jd_keywords(jd_text)

    return TailoringResponse(
        score=result.ats_score,
        reason="deterministic_tailoring",
        must_have=keywords["must_have"],
        nice_to_have=keywords["nice_to_have"],
        tools=keywords["tools"],
        concepts=keywords["concepts"],
        soft_skills=keywords["soft_skills"],
        experience_order=[e for e in result.experience_order],
        highlights_per_entry=result.highlights_per_entry,
    )
