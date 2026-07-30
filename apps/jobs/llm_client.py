import logging
import re

import httpx

logger = logging.getLogger(__name__)

REASONING_MODELS = {
    "deepseek-r1",
    "qwq",
    "o1",
    "o3",
    "o4-mini",
    "qwen-qwq",
}


def _strip_think_tags(text: str) -> str:
    text = re.sub(r"<think>[\s\S]*?</think>?", "", text)
    text = re.sub(r"<thinking>[\s\S]*?</thinking>?", "", text)
    text = re.sub(r"<thought>[\s\S]*?</thought>?", "", text)
    text = re.sub(r"^\s*\d+\.\s+\*{2}.*$", "", text, flags=re.MULTILINE)
    return text.strip()


def _strip_output_artifacts(text: str) -> str:
    text = re.sub(r"^(?:Cover Letter|Here(?:'s| is) (?:your |a )?cover letter|Generated Cover Letter)\s*[:\-]?\s*\n", "", text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r"^#{1,3}\s+.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\*{1,2}(.*?)\*{1,2}$", r"\1", text, flags=re.MULTILINE)
    if text.startswith('"') and text.endswith('"') and len(text.split("\n")) > 3:
        text = text[1:-1]
    return text.strip()


def _is_usable(text: str) -> bool:
    if not text:
        return False
    return len(text.split()) >= 50


def _detect_reasoning_model(model: str) -> bool:
    model_lower = model.lower()
    return any(alias in model_lower for alias in REASONING_MODELS)


def _get_payload(
    system_prompt: str,
    user_prompt: str,
    model: str,
    *,
    reasoning_disabled: bool = False,
) -> dict:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": 4000,
        "temperature": 0.7,
    }
    if reasoning_disabled:
        payload["reasoning"] = {"enabled": False}
    return payload


def _call_api(url: str, headers: dict, payload: dict) -> tuple[str, str] | tuple[None, str]:
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, json=payload, headers=headers)
    except httpx.TimeoutException:
        return None, "timeout"
    except Exception as e:
        return None, f"exception: {e}"

    if resp.status_code != 200:
        return None, f"HTTP {resp.status_code}: {resp.text[:300]}"

    data = resp.json()
    choices = data.get("choices", [])
    if not choices:
        return None, "no choices returned"

    choice = choices[0]
    message = choice.get("message", {})
    finish_reason = choice.get("finish_reason", "unknown")

    reasoning = message.get("reasoning_content", "") or ""
    content = message.get("content", "") or ""

    if not content and reasoning:
        return None, f"reasoning-only (finish_reason={finish_reason}, tokens={len(reasoning)})"

    return content.strip(), finish_reason


def generate_with_llm(
    system_prompt: str,
    user_prompt: str,
    api_key: str,
    api_base_url: str,
    model: str,
    *,
    provider: str = "",
) -> tuple[str | None, str | None]:
    url = f"{api_base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if "openrouter" in api_base_url.lower():
        headers["HTTP-Referer"] = "https://jobbloot.dev"
        headers["X-Title"] = "JobbLoot"

    is_reasoning = _detect_reasoning_model(model)

    content, finish_reason = _call_api(
        url, headers,
        _get_payload(system_prompt, user_prompt, model, reasoning_disabled=is_reasoning),
    )

    if content:
        letter = _strip_output_artifacts(_strip_think_tags(content))
        if _is_usable(letter):
            return letter, None
        logger.warning(
            "LLM output too short (finish_reason=%s, words=%d): %s",
            finish_reason, len(letter.split()), letter[:200],
        )
    else:
        logger.warning("LLM attempt 1 failed: %s", finish_reason)

    if not content and ("413" in (finish_reason or "") or "429" in (finish_reason or "")):
        return None, finish_reason

    strict_system = system_prompt + (
        "\n\nIMPORTANT: Output the final cover letter DIRECTLY. "
        "No preamble, no analysis, no commentary."
    )
    content2, finish_reason2 = _call_api(
        url, headers,
        _get_payload(strict_system, user_prompt, model, reasoning_disabled=is_reasoning),
    )

    if content2:
        letter2 = _strip_output_artifacts(_strip_think_tags(content2))
        if _is_usable(letter2):
            return letter2, None
        logger.warning(
            "LLM retry too short (finish_reason=%s, words=%d): %s",
            finish_reason2, len(letter2.split()), letter2[:200],
        )
    else:
        logger.warning("LLM attempt 2 failed: %s", finish_reason2)

    return None, finish_reason2 or "unknown error"
