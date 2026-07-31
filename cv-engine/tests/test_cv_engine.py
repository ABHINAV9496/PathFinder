"""Tests for the profession-agnostic CV Engine.

Run from repo root: pytest cv-engine/tests -q
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.profile_skills import (
    derive_skill_categories,
    derive_skill_weights,
    flatten_skills,
    resolve_skills,
)
from app.core.tailor_engine import map_skills, tailor_cv

DATA_ANALYST_PROFILE = {
    "name": "Alex Data",
    "role": "Data Analyst",
    "experience_years": 4,
    "skills": {
        "tools": ["Python", "SQL", "Power BI", "Excel", "Tableau"],
        "techniques": ["data cleaning", "statistical analysis", "ETL", "dashboarding"],
    },
    "projects": [{"name": "Sales Dashboard", "description": "Power BI dashboards"}],
}

DATA_ANALYST_JOB = {
    "title": "Senior Data Analyst",
    "company": "Acme Corp",
    "description": (
        "We need a data analyst with strong SQL, Power BI dashboards, "
        "statistical analysis, data cleaning, and ETL experience."
    ),
}

PYTHON_PROFILE = {
    "role": "Python Developer",
    "experience_years": 3,
    "skills": {
        "backend": ["Python", "Django", "DRF"],
        "frontend": ["React", "TypeScript"],
    },
}


def test_flatten_skills_any_profession():
    assert "SQL" in flatten_skills(DATA_ANALYST_PROFILE)
    assert "Power BI" in flatten_skills(DATA_ANALYST_PROFILE)


def test_derive_skill_weights_any_profession():
    weights = derive_skill_weights(DATA_ANALYST_PROFILE)
    assert weights["sql"] >= 6
    assert weights["statistical analysis"] >= 6


def test_derive_categories_unknown_categories_are_nice_to_have():
    cats = derive_skill_categories(DATA_ANALYST_PROFILE)
    assert "sql" in cats["nice_to_have"]
    assert "power bi" in cats["nice_to_have"]


def test_resolve_skills_falls_back_to_static_only_when_empty():
    weights, aliases, cats = resolve_skills(PYTHON_PROFILE)
    assert weights["python"] > 0
    assert "django" in cats["must_have"] or "python" in cats["must_have"]
    assert "python" in weights


def test_tailor_cv_uses_profile_driven_vocab():
    result = tailor_cv(DATA_ANALYST_JOB, DATA_ANALYST_PROFILE)
    assert "SQL" in result.matched_skills
    assert "Power BI" in result.matched_skills


def test_map_skills_matches_multi_word_without_spaces():
    matched, breakdown = map_skills(
        DATA_ANALYST_JOB["description"],
        DATA_ANALYST_PROFILE["skills"],
        weights=derive_skill_weights(DATA_ANALYST_PROFILE),
    )
    matched_lower = [m.lower() for m in matched]
    assert "Power BI" in matched_lower or "power bi" in matched_lower
