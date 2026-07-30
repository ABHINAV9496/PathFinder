import base64
from fastapi import APIRouter, Depends
from app.deps import verify_service_key
from app.models.requests import CVRequest
from app.models.responses import CVResponse
from app.core.tailor_engine import tailor_cv
from app.core.builder import build_cv_html
from app.core.renderer import render_pdf

router = APIRouter(prefix="/v1", tags=["generate-cv"])


@router.post("/generate-cv", response_model=CVResponse)
async def generate_cv(request: CVRequest, _auth: bool = Depends(verify_service_key)):
    job_dict = request.job.model_dump()
    profile_dict = request.profile.model_dump()
    company_context = request.company_context

    result = tailor_cv(job_dict, profile_dict, company_context=company_context)

    html = build_cv_html(profile_dict, job_dict, result)

    pdf_bytes = render_pdf(html)

    pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")

    name = profile_dict.get("name", "Resume").split()[0]
    filename = f"{name}.pdf"

    return CVResponse(
        pdf_base64=pdf_b64,
        filename=filename,
        ats_score=result.ats_score,
        ats_breakdown={"must_have": result.must_have, "nice_to_have": result.nice_to_have},
        tailored=True,
        sections_reordered=["skills", "experience", "projects"],
    )
