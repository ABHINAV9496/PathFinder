"""Shared helpers for the fetch pipeline (remote job boards)."""

import re

from apps.jobs.services import CURRENCY_SYMBOLS

_REMOTE_SYNONYMS = {
    "worldwide", "anywhere", "remote", "global", "fully remote",
    "work from anywhere", "work from home", "wfh",
}

_EMOJI_RE = re.compile(
    r"[\U0001F000-\U0001FAFF\U0001F300-\U0001F64F\U0001F680-\U0001F6FF"
    r"\u2600-\u27BF\uFE0F]"
)


def normalize_remote_location(location: str) -> str:
    """Collapse remote synonyms (and empty/emoji-only values) to ``remote`` so
    cross-board uids match even when boards phrase the location differently."""
    if not location:
        return "remote"
    text = location.strip()
    low = _EMOJI_RE.sub("", text).strip().lower()
    if not low or low in _REMOTE_SYNONYMS:
        return "remote"
    return text


def safe_int(value) -> int:
    """Best-effort int conversion for structured salary fields."""
    if value in (None, "", 0):
        return 0
    try:
        return int(float(str(value).replace(",", "").replace("$", "").strip()))
    except (TypeError, ValueError):
        return 0


def annualize_salary(amount: int, period: str | None = None) -> int:
    """Annualize a structured salary figure from a period label (default yearly)."""
    period = (period or "yearly").lower()
    if "hour" in period:
        return amount * 2080
    if "week" in period:
        return amount * 52
    if "month" in period:
        return amount * 12
    if "day" in period:
        return amount * 260
    return amount


def format_annual_range(salary_min: int, salary_max: int, currency: str = "") -> tuple[int, str]:
    """Build ``(salary, display)`` from an annualized min/max range.

    ``salary`` is the higher bound (matching cutshort/jobdrop behaviour).
    """
    if not salary_min and not salary_max:
        return 0, ""
    salary = salary_max or salary_min
    symbol = CURRENCY_SYMBOLS.get((currency or "").upper())
    if symbol:
        prefix = symbol
    elif currency:
        prefix = f"{currency} "
    else:
        prefix = ""
    if salary_min and salary_max and salary_min != salary_max:
        return salary, f"{prefix}{salary_min:,}-{salary_max:,}/yr"
    return salary, f"{prefix}{salary:,}/yr"
