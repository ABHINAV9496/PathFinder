from fastapi import APIRouter, Depends
from app.deps import verify_service_key
from app.models.requests import EnrichRequest
from app.core.company_scraper import scrape_company_context

router = APIRouter(prefix="/v1", tags=["enrich"])


@router.post("/enrich")
async def enrich(request: EnrichRequest, _auth: bool = Depends(verify_service_key)):
    result = scrape_company_context(
        company_name=request.company,
        apply_url=request.apply_url or None,
    )
    return result
