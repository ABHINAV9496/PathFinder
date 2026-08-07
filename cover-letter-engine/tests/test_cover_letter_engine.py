"""Tests for the standalone Cover Letter Engine service.

Run from repo root: pytest cover-letter-engine/tests -q
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coverletter.core import ai_generator, classify, generator, templates
from coverletter.core.generator import _build_context
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


NURSE_JOB = {
    "title": "Staff Nurse",
    "company": "City General Hospital",
    "description": (
        "We need a registered nurse for patient care, medication administration, "
        "and care planning at our hospital."
    ),
    "matched_skills": ["patient care", "medication administration", "care planning"],
}

NURSE_PROFILE = {
    "name": "Maya Nurse",
    "role": "Registered Nurse",
    "experience_years": 3,
    "skills": {
        "clinical": ["patient care", "medication administration", "care planning", "EMR"],
    },
    "projects": [{
        "name": "Community Health Clinic",
        "description": "Volunteer clinic delivering patient intake and follow-up care",
        "tech": [],
    }],
}


def test_generator_uses_profession_pack_for_nurse_job():
    letter, meta = generator.generate_cover_letter(NURSE_JOB, NURSE_PROFILE)
    assert meta["source"] == "pack"
    assert meta["template"] == "healthcare"
    assert "City General Hospital" in letter
    assert "Maya Nurse" in letter
    assert "{" not in letter and "}" not in letter


def test_generator_uses_neutral_pack_for_unknown_profession():
    job = {
        "title": "General Helper",
        "company": "Example Co",
        "description": (
            "We need a dependable person to help the team with everyday tasks and shared goals."
        ),
    }
    profile = {
        "name": "O",
        "role": "Generalist",
        "experience_years": 2,
        "skills": {"core": ["communication", "teamwork"]},
    }
    letter, meta = generator.generate_cover_letter(job, profile)
    assert meta["source"] == "pack"
    assert meta["template"] == "neutral"
    assert "Example Co" in letter


def test_generator_letters_vary_by_job_for_same_profile():
    startup_job = {
        **DATA_ANALYST_JOB,
        "description": DATA_ANALYST_JOB["description"] + " Fast-paced startup that ships quickly.",
    }
    formal_job = {
        **DATA_ANALYST_JOB,
        "description": DATA_ANALYST_JOB["description"]
        + " Formal enterprise compliance environment.",
    }
    letter_a, meta_a = generator.generate_cover_letter(startup_job, DATA_ANALYST_PROFILE)
    letter_b, meta_b = generator.generate_cover_letter(formal_job, DATA_ANALYST_PROFILE)
    assert meta_a["source"] == "pack"
    assert meta_b["source"] == "pack"
    assert letter_a != letter_b


def test_pack_letter_is_grounded_in_resume():
    letter, meta = generator.generate_cover_letter(
        NURSE_JOB, NURSE_PROFILE,
        resume_text="Performed patient care and medication administration at a community clinic.",
    )
    assert meta["grounded_in_resume"]
    assert "Community Health Clinic" in letter


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


def test_ai_generation_gives_up_after_retry_limit(monkeypatch):
    import pytest
    calls = {"n": 0}

    def fake_call(
        system, user, api_key, api_base_url, model,
        provider="", max_tokens=1000, timeout=30.0,
    ):
        calls["n"] += 1
        return (
            "Dear Hiring Manager,\n\nI have experience with the missing skill Kubernetes. "
            "I am confident in my abilities.\n\nRegards,\nAlex Data"
        )
    monkeypatch.setattr(ai_generator, "_call_llm", fake_call)
    with pytest.raises(ai_generator.AIGenerationError) as excinfo:
        ai_generator.generate_ai_letter(
            {**DATA_ANALYST_JOB, "skill_gaps": ["Kubernetes"]},
            {**DATA_ANALYST_PROFILE, "skills": {"tools": ["SQL", "Power BI"]}},
            {"api_key": "k", "api_base_url": "https://x", "model": "m"},
        )
    assert calls["n"] == 3
    assert "forbidden_skill:Kubernetes" in str(excinfo.value)


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


RICH_PROFILE = {
    "name": "Riya K",
    "role": "Software Engineer",
    "experience_years": 5,
    "email": "riya@example.com",
    "phone": "555-0100",
    "linkedin": "linkedin.com/in/riya",
    "skills": {
        "backend": ["Python", "Django", "PostgreSQL", "SQL", "Redis", "REST APIs"],
        "ai": ["LLM", "RAG", "prompt engineering", "OpenAI"],
        "infra": ["Docker", "AWS", "CI/CD"],
        "frontend": ["React", "TypeScript"],
        "security": ["JWT", "RBAC"],
    },
    "projects": [
        {
            "name": "RAG Chatbot",
            "description": "Document retrieval chatbot with structured output parsing",
            "tech": ["Python", "LLM", "RAG", "PostgreSQL", "Docker"],
        },
        {
            "name": "Payments API",
            "description": "REST API with auth, RBAC, and idempotent payments",
            "tech": ["Django", "JWT", "RBAC", "PostgreSQL", "Redis"],
        },
    ],
}

RICH_JOB = {
    "title": "Senior AI Backend Engineer",
    "company": "Neura Labs",
    "description": (
        "Build AI features with LLMs, RAG, and machine learning. Fast-paced startup. "
        "Docker, AWS, Python, PostgreSQL, authentication, and secure production APIs."
    ),
}


def test_selector_picks_ai_fresher_template_for_ai_intern():
    job = {
        "title": "AI Intern",
        "company": "Neura",
        "description": (
            "We are building LLM RAG features with Python and machine learning. Fast-paced."
        ),
    }
    features = classify.extract(job, {"experience_years": 0, "skills": {"ai": ["LLM"]}})
    assert templates.select(features)["id"] == "ai_engineer_fresher"


def test_selector_picks_fintech_template_for_formal_banking_job():
    job = {
        "title": "Backend Engineer",
        "company": "Finco Bank",
        "description": (
            "Fintech payment platform. Banking compliance, authentication, SQL, security."
        ),
    }
    features = classify.extract(job, {"experience_years": 4, "skills": {"backend": ["SQL"]}})
    assert templates.select(features)["id"] == "fintech_engineer"


def test_selector_defaults_to_fresher_general_on_empty_signals():
    features = classify.extract({}, {"name": "N"})
    assert templates.select(features)["id"] == "fresher_general"


def test_all_templates_render_with_rich_profile():
    ctx = _build_context(
        RICH_JOB, RICH_PROFILE, "Built RAG Chatbot end to end.\nDeployed on AWS.", []
    )
    for t in templates.TEMPLATES:
        body = t["render"](ctx)
        assert len(body) > 100, t["id"]
        assert body.startswith("Dear") is False, t["id"]
        assert "Riya K" not in body, t["id"]


def test_all_templates_render_with_empty_profile():
    ctx = _build_context(RICH_JOB, {"name": "N"}, "", [])
    for t in templates.TEMPLATES:
        body = t["render"](ctx)
        assert len(body) > 50, t["id"]


def test_all_templates_never_mention_missing_skills():
    job = {
        **RICH_JOB,
        "matched_skills": ["Python", "Docker", "Kubernetes", "Kafka"],
        "missing_keywords": ["Kubernetes", "Kafka"],
    }
    for t in templates.TEMPLATES:
        t["render"](_build_context(job, RICH_PROFILE, "", []))
    letter, meta = generator.generate_cover_letter(job, RICH_PROFILE)
    assert "Kubernetes" not in letter
    assert "Kafka" not in letter
    assert "Python" in letter
    assert set(meta["missing_keywords"]) == {"Kubernetes", "Kafka"}


DEV_PROFILE = {
    "name": "Dennis Joseph",
    "role": "Python Full-Stack Developer",
    "experience_years": 1,
    "phone": "555-0101",
    "email": "dennis@example.com",
    "portfolio": "https://dennis.example.com",
    "github": "https://github.com/dennis",
    "linkedin": "https://www.linkedin.com/in/dennis",
    "skills": {
        "backend": ["Python", "Django", "DRF", "PostgreSQL", "SQLAlchemy", "Gunicorn"],
        "frontend": ["React", "TypeScript", "Vite"],
        "ai_llm": ["Groq", "LLM"],
        "cloud": ["AWS", "RDS", "ElastiCache", "S3", "EC2", "Vercel"],
        "devops": ["Docker", "CI/CD", "Git"],
    },
    "projects": [
        {
            "name": "PyDocAI",
            "description": "AI-powered SaaS documentation generator using Django and React on AWS",
            "tech": ["Django", "DRF", "PostgreSQL", "React", "Groq", "LLM", "Docker", "AWS",
                     "CI/CD"],
        },
        {
            "name": "DENJO-C",
            "description": "Full-stack e-commerce platform with JWT auth and RBAC",
            "tech": ["Django", "DRF", "PostgreSQL", "React", "JWT", "RBAC"],
        },
        {
            "name": "EduCom",
            "description": "Student management platform with role-based access",
            "tech": ["Django", "PostgreSQL", "Bootstrap", "Vercel"],
        },
    ],
}


def _letter_sig():
    return ai_generator._signature(DEV_PROFILE)


def _letter_body(*paragraphs):
    sig = _letter_sig()
    return "Dear Hiring Manager,\n\n" + "\n\n".join(paragraphs) + "\n\n" + sig


def test_validation_accepts_implied_and_general_skills():
    letter = _letter_body(
        "On DENJO-C I used git for version control and deployed the PostgreSQL database "
        "on RDS with the React frontend on Vercel.",
        "PyDocAI is where I worked with SQLAlchemy alongside Django and Celery.",
    )
    repaired, issues = ai_generator._validate(letter, {}, DEV_PROFILE, _letter_sig())
    assert not [i for i in issues if i.startswith("misattribution:")]


def test_validation_still_flags_genuine_misattribution():
    letter = _letter_body(
        "On DENJO-C I used Groq for the AI pipeline.",
        "PyDocAI uses Bootstrap for its admin UI.",
    )
    repaired, issues = ai_generator._validate(letter, {}, DEV_PROFILE, _letter_sig())
    flagged = [i for i in issues if i.startswith("misattribution:")]
    assert "misattribution:groq->DENJO-C" in flagged
    assert "misattribution:bootstrap->PyDocAI" in flagged


def test_validation_accepts_shared_tech_across_two_projects():
    letter = _letter_body(
        "I built PyDocAI and DENJO-C with JWT authentication, RBAC, Celery jobs, and "
        "Groq, all deployed on AWS with React frontends.",
    )
    repaired, issues = ai_generator._validate(letter, {}, DEV_PROFILE, _letter_sig())
    assert not [i for i in issues if i.startswith("misattribution:")]


def test_validation_replaces_truncated_signature():
    sig = _letter_sig()
    truncated = (
        "Dear Hiring Manager,\n\nI am applying for the role.\n\n"
        "Regards,\nDennis Joseph\n555-0101\nPort"
    )
    repaired, issues = ai_generator._validate(truncated, {}, DEV_PROFILE, sig)
    assert repaired.endswith(sig)
    assert repaired.count("Regards,") == 1
    assert "Portfolio:" in repaired
    assert "\nPort\n" not in repaired


def test_validation_keeps_complete_signature_unchanged():
    sig = _letter_sig()
    letter = "Dear Hiring Manager,\n\nI am applying for the role.\n\n" + sig
    repaired, issues = ai_generator._validate(letter, {}, DEV_PROFILE, sig)
    assert repaired.endswith(sig)
    assert repaired.count("Regards,") == 1


def test_system_prompt_enforces_paragraph_separation():
    prompt = ai_generator._build_system_prompt(_letter_sig())
    assert "PARAGRAPH SEPARATION RULE" in prompt
    assert "Never describe two different projects in the same paragraph" in prompt
    assert "The closing paragraph must be its own paragraph" in prompt
    assert (
        "end with a forward-looking statement" in prompt
    )


def test_system_prompt_bans_blanket_claims_in_both_rules():
    prompt = ai_generator._build_system_prompt(_letter_sig())
    blanket = "Do not write blanket claims like 'Both projects run on X'"
    assert blanket in prompt
    # The aggregate-claim guidance is required in BOTH the GROUNDED CLAIM
    # RULE and the PROJECT ATTRIBUTION RULE.
    assert prompt.count(blanket) == 2
    assert "not a vague category like 'automated testing' with no named framework" in prompt
