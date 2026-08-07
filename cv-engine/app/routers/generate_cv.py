import base64

from fastapi import APIRouter, Depends, HTTPException

from app.core.ats_engine import analyze, build_gap_report, build_source_trace
from app.core.resume_pipeline import build_tailored_cv
from app.core.tailor_engine import tailor_cv
from app.deps import verify_service_key
from app.models.requests import CVRequest
from app.models.responses import ATSReportResponse, CVResponse

router = APIRouter(prefix="/v1", tags=["generate-cv"])


@router.post("/generate-cv", response_model=CVResponse)
async def generate_cv(request: CVRequest, _auth: bool = Depends(verify_service_key)):
    job_dict = request.job.model_dump()
    profile_dict = request.profile.model_dump()
    company_context = request.company_context
    resume_text = profile_dict.get("resume_text", "") or ""

    result = tailor_cv(job_dict, profile_dict, company_context=company_context)
    matched_skills = result.must_have + result.nice_to_have + result.tools
    if not matched_skills:
        matched_skills = result.matched_skills

    tailored_text, project_url_map, pdf_bytes = build_tailored_cv(
        resume_text, profile_dict, job_dict, matched_skills
    )

    if not tailored_text:
        raise HTTPException(
            status_code=400,
            detail="No resume content found. Upload your resume PDF in Profile settings.",
        )

    pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8") if pdf_bytes else ""

    jd_text = f"{job_dict.get('title', '')} {job_dict.get('description', '')}"
    ats_report = analyze(jd_text, resume_text, profile_dict)

    name = profile_dict.get("name", "Developer") or "Developer"
    filename = f"{name.replace(' ', '_')}.pdf"

    return CVResponse(
        pdf_base64=pdf_b64,
        filename=filename,
        ats_score=ats_report.score,
        ats_breakdown=ats_report.breakdown,
        tailored=True,
        sections_reordered=["skills", "experience", "projects"],
        tailored_resume=tailored_text,
        gap_report=build_gap_report(ats_report),
        source_trace=build_source_trace(ats_report),
        suggested_keywords=matched_skills,
        ats_report=ATSReportResponse(
            score=ats_report.score,
            breakdown=ats_report.breakdown,
            tiers=ats_report.tiers,
            parseability=ats_report.parseability,
            resume_quality=ats_report.resume_quality,
            frequency_recency=ats_report.frequency_recency,
            missing_keywords=ats_report.missing_keywords,
            fixes=ats_report.fixes,
            caveats=ats_report.caveats,
            summary=ats_report.summary,
            source=ats_report.source,
        ),
    )
