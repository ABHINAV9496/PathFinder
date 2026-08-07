import logging

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class CoverLetterEngineUnavailableError(Exception):
    pass


def _get_client(timeout: float = 30.0):
    return httpx.Client(
        base_url=settings.COVER_LETTER_ENGINE_BASE_URL,
        timeout=timeout,
        headers={"X-Service-Key": settings.COVER_LETTER_ENGINE_SERVICE_KEY},
    )


def generate_cover_letter(
    job: dict,
    profile: dict,
    mode: str = "template",
    resume_text: str = "",
    ai_config: dict = None,
) -> dict:
    """Generate a cover letter via the Cover Letter Engine service.

    Returns {"cover_letter", "template_used", "tailored", "mode", "issues"}.
    Raises CoverLetterEngineUnavailableError when the service cannot be reached.
    """
    payload = {
        "job": job,
        "profile": profile,
        "mode": mode,
        "resume_text": resume_text,
    }
    if ai_config:
        payload["ai"] = ai_config

    try:
        with _get_client() as client:
            response = client.post("/v1/generate", json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.ConnectError:
        logger.warning("Cover letter engine unavailable")
        raise CoverLetterEngineUnavailableError("Cover letter engine service is not running")
    except httpx.HTTPStatusError as e:
        logger.error("Cover letter engine HTTP %s: %s", e.response.status_code, e)
        if e.response.status_code >= 500:
            raise CoverLetterEngineUnavailableError(str(e))
        return {"cover_letter": "", "template_used": "", "tailored": False,
                "mode": mode, "issues": [], "error": e.response.text}
    except Exception as e:
        logger.error("Cover letter generation failed: %s", e)
        raise CoverLetterEngineUnavailableError(str(e))
