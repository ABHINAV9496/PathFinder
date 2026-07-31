"""Tests for the standalone Cover Letter Engine service.

Run from repo root: pytest cover-letter-engine/tests -q
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coverletter.core import ai_generator, generator
from coverletter.models import GenerateRequest, GenerateResponse

DATA_ANALYST_PROFILE = {
    "name": "Alex Data",
    "role": "Data Analyst",
    "experience_years": 4,
    "skills": {
        "tools": ["Python", "SQL", "Power BI", "Excel", "Tableau"],
        "techniques": ["data cleaning", "statistical analysis", "ETL", "dashboarding"],
    },
    "projects": [{
        "name": "Sales Dashboard",
        "description": "Built Power BI dashboards for retail sales",
        "tech": ["Power BI", "SQL"],
    }],
}

DATA_ANALYST_JOB = {
    "title": "Senior Data Analyst",
    "company": "Acme Corp",
    "description": (
        "We need a data analyst with strong SQL, Power BI dashboards, "
        "statistical analysis, data cleaning, and ETL experience."
    ),
}


def test_template_grounded_in_resume():
    letter, meta = generator.generate_cover_letter(
        DATA_ANALYST_JOB, DATA_ANALYST_PROFILE,
        resume_text="Built Power BI dashboards for retail sales.\nPerformed data cleaning and ETL.",
    )
    assert meta["grounded_in_resume"]
    assert "Acme Corp" in letter
    assert "Alex Data" in letter
    assert letter.startswith("Dear Hiring Manager,")


def test_template_falls_back_to_projects():
    letter, meta = generator.generate_cover_letter(DATA_ANALYST_JOB, DATA_ANALYST_PROFILE)
    assert not meta["grounded_in_resume"]
    assert "Sales Dashboard" in letter


def test_template_empty_profile_does_not_crash():
    letter, meta = generator.generate_cover_letter(
        DATA_ANALYST_JOB, {"name": "N", "role": "", "experience_years": 1}
    )
    assert "Acme Corp" in letter


def test_ai_generation_runs_validation(monkeypatch):
    def fake_call(
        system, user, api_key, api_base_url, model,
        provider="", max_tokens=1000, timeout=30.0,
    ):
        return (
            "Dear Hiring Manager,\n\nI am applying for the Senior Data Analyst role at Acme Corp. "
            "My experience with SQL and Power BI maps directly to your needs.\n\n"
            "Thank you.\n\nRegards,\nAlex Data"
        )
    monkeypatch.setattr(ai_generator, "_call_llm", fake_call)
    letter, issues = ai_generator.generate_ai_letter(
        DATA_ANALYST_JOB, DATA_ANALYST_PROFILE,
        {"api_key": "k", "api_base_url": "https://x", "model": "m"},
    )
    assert "Acme Corp" in letter
    assert letter.startswith("Dear Hiring Manager,")
    assert "Alex Data" in letter


def test_ai_generation_retries_on_forbidden_skill(monkeypatch):
    calls = {"n": 0}

    def fake_call(
        system, user, api_key, api_base_url, model,
        provider="", max_tokens=1000, timeout=30.0,
    ):
        calls["n"] += 1
        if calls["n"] == 1:
            return (
                "Dear Hiring Manager,\n\nI have experience with the missing skill Kubernetes. "
                "I am confident in my abilities.\n\nRegards,\nAlex Data"
            )
        return (
            "Dear Hiring Manager,\n\nI bring SQL and Power BI skills to the Senior Data Analyst "
            "role at Acme Corp.\n\nRegards,\nAlex Data"
        )
    monkeypatch.setattr(ai_generator, "_call_llm", fake_call)
    letter, issues = ai_generator.generate_ai_letter(
        {**DATA_ANALYST_JOB, "skill_gaps": ["Kubernetes"]},
        {**DATA_ANALYST_PROFILE, "skills": {"tools": ["SQL", "Power BI"]}},
        {"api_key": "k", "api_base_url": "https://x", "model": "m"},
    )
    assert calls["n"] == 2
    assert not any(i.startswith("forbidden_skill") for i in issues)


def test_ai_config_incomplete_raises():
    import pytest
    with pytest.raises(ai_generator.AIGenerationError):
        ai_generator.generate_ai_letter(DATA_ANALYST_JOB, DATA_ANALYST_PROFILE, {})


def test_template_uses_engine_missing_keywords_filtering():
    job = {
        **DATA_ANALYST_JOB,
        "matched_skills": ["SQL", "Power BI", "Tableau"],
        "missing_keywords": ["Tableau"],
    }
    letter, meta = generator.generate_cover_letter(job, DATA_ANALYST_PROFILE)
    assert "Tableau" not in letter
    assert "SQL" in letter
    assert "Tableau" in meta["missing_keywords"]


def test_ai_generation_uses_engine_missing_keywords(monkeypatch):
    calls = {"n": 0}

    def fake_call(
        system, user, api_key, api_base_url, model,
        provider="", max_tokens=1000, timeout=30.0,
    ):
        calls["n"] += 1
        if calls["n"] == 1:
            return (
                "Dear Hiring Manager,\n\nI have experience with the missing skill Kafka. "
                "I am confident in my abilities.\n\nRegards,\nAlex Data"
            )
        return (
            "Dear Hiring Manager,\n\nI bring SQL and Power BI skills to the Senior Data Analyst "
            "role at Acme Corp.\n\nRegards,\nAlex Data"
        )
    monkeypatch.setattr(ai_generator, "_call_llm", fake_call)
    letter, issues = ai_generator.generate_ai_letter(
        {**DATA_ANALYST_JOB, "missing_keywords": ["Kafka"]},
        {**DATA_ANALYST_PROFILE, "skills": {"tools": ["SQL", "Power BI"]}},
        {"api_key": "k", "api_base_url": "https://x", "model": "m"},
    )
    assert calls["n"] == 2
    assert not any(i.startswith("forbidden_skill") for i in issues)


def test_models():
    req = GenerateRequest(job=DATA_ANALYST_JOB, profile=DATA_ANALYST_PROFILE, mode="template")
    assert req.mode == "template"
    resp = GenerateResponse(cover_letter="x", template_used="t", mode="template")
    assert resp.cover_letter == "x"
