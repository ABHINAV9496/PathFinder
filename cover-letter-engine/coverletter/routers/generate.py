from fastapi import APIRouter, Depends, HTTPException

from coverletter.core import ai_generator, generator
from coverletter.core.ai_generator import AIGenerationError
from coverletter.deps import verify_service_key
from coverletter.models import GenerateRequest, GenerateResponse

router = APIRouter(prefix="/v1", tags=["generate"])


@router.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest, _auth: bool = Depends(verify_service_key)):
    job_dict = request.job.model_dump()
    profile_dict = request.profile.model_dump()

    if request.mode == "ai":
        try:
            letter, issues = ai_generator.generate_ai_letter(
                job_dict, profile_dict, request.ai.model_dump() if request.ai else {},
                resume_text=request.resume_text,
            )
        except AIGenerationError as e:
            raise HTTPException(status_code=502, detail=str(e))
        return GenerateResponse(
            cover_letter=letter,
            template_used="ai",
            tailored=bool(job_dict.get("matched_skills")),
            mode="ai",
            issues=issues,
        )

    letter, metadata = generator.generate_cover_letter(
        job_dict, profile_dict, resume_text=request.resume_text
    )
    return GenerateResponse(
        cover_letter=letter,
        template_used="deterministic",
        tailored=bool(metadata["matched_skills"]),
        mode="template",
    )
