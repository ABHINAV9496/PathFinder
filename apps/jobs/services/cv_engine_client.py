import base64
import json
import logging

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class CVEngineUnavailableError(Exception):
    pass


def _get_client():
    return httpx.Client(
        base_url=settings.CV_ENGINE_BASE_URL,
        timeout=12.0,
        headers={"X-Service-Key": settings.CV_ENGINE_SERVICE_KEY},
    )


def generate_cv(job: dict, profile: dict, company_context: dict = None) -> dict:
    try:
        with _get_client() as client:
            payload = {"job": job, "profile": profile}
            if company_context:
                payload["company_context"] = company_context
            response = client.post("/v1/generate-cv", json=payload)
            response.raise_for_status()
            data = response.json()
            data["pdf_bytes"] = base64.b64decode(data["pdf_base64"])
            return data
    except httpx.ConnectError:
        logger.warning("CV engine unavailable")
        raise CVEngineUnavailableError("CV engine service is not running")
    except Exception as e:
        logger.error(f"CV generation failed: {e}")
        raise CVEngineUnavailableError(str(e))


def get_ats_score(job: dict, profile: dict, ai_config: dict = None) -> dict:
    try:
        with _get_client() as client:
            payload = {"job": job, "profile": profile}
            if ai_config:
                payload["ai_config"] = ai_config
            response = client.post("/v1/tailor", json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.ConnectError:
        logger.warning("CV engine unavailable for ATS score")
        return {"score": None, "reason": "cv_engine_unavailable"}
    except Exception as e:
        logger.error(f"ATS score failed: {e}")
        return {"score": None, "reason": str(e)}


def enrich_company(company: str, apply_url: str = "") -> dict:
    try:
        with httpx.Client(
            base_url=settings.CV_ENGINE_BASE_URL,
            timeout=5.0,
            headers={"X-Service-Key": settings.CV_ENGINE_SERVICE_KEY},
        ) as client:
            response = client.post("/v1/enrich", json={
                "company": company,
                "apply_url": apply_url,
            })
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.debug(f"Company enrichment skipped (dev server not running): {e}")
        return {}


_enrich_cache: dict[str, tuple[dict, str]] = {}

def enrich_company_with_ai(company: str, job_description: str,
                           api_key: str, api_base_url: str,
                           model: str, provider: str = "") -> dict:
    cache_key = f"{company}|{api_base_url}|{model}"
    cached = _enrich_cache.get(cache_key)
    if cached and cached[1] == job_description[:1000]:
        return cached[0]

    system_prompt = (
        "You are an ATS resume optimization expert. Given a company name and job description, "
        "extract structured data to help tailor a resume. "
        "Return ONLY valid JSON with these exact keys (no markdown, no explanation):\n"
        "{\n"
        '    "tech_stack": ["Python", "Django", "PostgreSQL"],\n'
        '    "size": "startup or mid-size or enterprise",\n'
        '    "industry": "saas or fintech or healthtech or ecommerce or edtech or ai or general",\n'
        '    "key_focus_areas": ["API design", "scalability", "database optimization"],\n'
        '    "must_have_keywords": ["Python", "Django", "REST API", "PostgreSQL"],\n'
        '    "nice_to_have_keywords": ["Docker", "CI/CD", "Redis"]\n'
        "}\n\n"
        "Rules:\n"
        "- tech_stack: technologies explicitly mentioned or strongly implied in the JD\n"
        "- must_have_keywords: skills/technologies the employer specifically asks for\n"
        "- nice_to_have_keywords: skills mentioned as nice to have or bonus\n"
        "- key_focus_areas: 2-4 most important themes this role requires\n"
        "- Keep lists concise: max 6 items each"
    )

    user_prompt = f"Company: {company}\n\nJob Description:\n{job_description[:2000]}"

    try:
        import re
        url = f"{api_base_url.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        if "openrouter" in api_base_url.lower():
            headers["HTTP-Referer"] = "https://pathfinder.dev"
            headers["X-Title"] = "JobbLoot"

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": 300,
            "temperature": 0.3,
        }

        resp = httpx.post(url, json=payload, headers=headers, timeout=10)
        if resp.status_code != 200:
            logger.warning(f"LLM enrichment HTTP {resp.status_code} for {company}")
            return {}

        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            return {}

        content = choices[0].get("message", {}).get("content", "")
        if not content:
            return {}

        try:
            llm_data = json.loads(content)
        except json.JSONDecodeError:
            json_match = re.search(r"\{[\s\S]*\}", content)
            if json_match:
                llm_data = json.loads(json_match.group())
            else:
                logger.warning(f"LLM enrichment non-JSON for {company}")
                return {}

        merged = {
            "tech_stack": llm_data.get("tech_stack", []),
            "size": llm_data.get("size", ""),
            "industry": llm_data.get("industry", ""),
            "key_focus_areas": llm_data.get("key_focus_areas", []),
            "must_have_keywords": llm_data.get("must_have_keywords", []),
            "nice_to_have_keywords": llm_data.get("nice_to_have_keywords", []),
        }
        _enrich_cache[cache_key] = (merged, job_description[:1000])
        logger.info(f"AI enrichment succeeded for {company}: {len(merged['must_have_keywords'])} must-have keywords")
        return merged

    except Exception as e:
        logger.warning(f"AI enrichment exception for {company}: {e}")
        return {}
