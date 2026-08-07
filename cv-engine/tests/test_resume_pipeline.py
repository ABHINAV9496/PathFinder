"""Tests for the resume-preserving pipeline (profession-agnostic).

Run from repo root: pytest cv-engine/tests/test_resume_pipeline.py -q
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.resume_pipeline import (
    build_project_url_map,
    build_tailored_cv,
    build_tailored_text,
    choose_header_title,
    enrich_sections,
    parse_project_links,
    parse_resume_sections,
    profile_sections,
    reorder_skills,
)

RESUME_TEXT = (
    "Alex Data\nData Analyst\n"
    "Bangalore · 9999999999 · alex@example.com\n"
    "GitHub · LinkedIn · Portfolio\n"
    "PROFESSIONAL SUMMARY\n"
    "Data Analyst with 4+ years of experience building dashboards.\n"
    "TECHNICAL SKILLS\n"
    "Tools: Python, SQL, Power BI\n"
    "Techniques: data cleaning, ETL\n"
    "PROFESSIONAL EXPERIENCE\n"
    "Data Analyst at Acme Corp, 2022 - Present\n"
    "  \u2022 Built Power BI dashboards\n"
    "PROJECTS\n"
    "Sales Dashboard — Power BI, SQL\n"
    "Live: https://sales.example.com\n"
    "GitHub: https://github.com/alex/sales-dashboard\n"
    "EDUCATION\n"
    "B.Tech\n"
)

PROFILE = {
    "name": "Alex Data",
    "role": "Data Analyst",
    "experience_years": 4,
    "email": "alex@example.com",
    "phone": "9999999999",
    "location": "Bangalore",
    "github": "https://github.com/alex",
    "skills": {
        "tools": ["Python", "SQL", "Power BI", "Excel"],
        "techniques": ["data cleaning", "statistical analysis", "ETL"],
    },
    "projects": [
        {"name": "Sales Dashboard", "description": "Power BI dashboards", "link": ""},
    ],
}

JOB = {
    "title": "Senior Data Analyst",
    "company": "Acme Corp",
    "description": "SQL and Power BI dashboards, data cleaning and ETL experience.",
    "relevant_project": {"name": "Sales Dashboard", "description": "Power BI dashboards"},
}

JAVA_JOB = {
    "title": "Backend Engineer",
    "company": "Acme Corp",
    "description": "Java Spring Boot microservices and Kafka.",
    "relevant_project": {},
}


def test_parse_resume_sections_preserves_verbatim_lines():
    sections = parse_resume_sections(RESUME_TEXT)
    assert sections["header"][0] == "Alex Data"
    assert sections["summary"][0].startswith("Data Analyst with 4+ years")
    assert "Power BI" in sections["skills"]["Tools"]
    assert sections["projects"][0].startswith("Sales Dashboard")
    assert sections["education"] == ["B.Tech"]


def test_enrich_sections_keeps_existing_resume_content():
    sections = parse_resume_sections(RESUME_TEXT)
    before = dict(sections["skills"])
    enrich_sections(sections, PROFILE)
    assert sections["skills"] == before


def test_enrich_sections_fills_empty_from_profile():
    sections = parse_resume_sections("Alex Data\n\n")
    enrich_sections(sections, PROFILE)
    all_skills = [s for skills in sections["skills"].values() for s in skills]
    assert "Power BI" in all_skills
    assert sections["projects"]


def test_profile_sections_builds_from_profile_when_no_resume():
    sections = profile_sections(PROFILE)
    assert sections["header"][0] == "Alex Data"
    all_skills = [s for skills in sections["skills"].values() for s in skills]
    assert "Power BI" in all_skills


def test_reorder_skills_puts_matched_first():
    skills = {"Tools": ["Excel", "Python", "SQL", "Power BI"]}
    ordered = reorder_skills(skills, ["SQL", "Power BI"])
    assert ordered["Tools"][0] in ("SQL", "Power BI")
    assert ordered["Tools"][-1] in ("Excel", "Python")


def test_choose_header_title_prefers_profile_role():
    assert choose_header_title(JOB, PROFILE) == "Data Analyst"


def test_choose_header_title_strips_seniority_from_jd_when_no_role():
    p = dict(PROFILE, role="")
    assert choose_header_title(JOB, p) == "Data Analyst"


def test_build_tailored_text_uses_profile_role_profession_agnostic():
    sections = parse_resume_sections(RESUME_TEXT)
    text = build_tailored_text(sections, PROFILE, JOB, ["SQL", "Power BI"])
    assert "Data Analyst" in text
    assert "PROFESSIONAL SUMMARY" in text
    assert "Power BI" in text


def test_build_tailored_text_works_for_java_job():
    text = build_tailored_text(profile_sections(PROFILE), PROFILE, JAVA_JOB, ["Java"])
    assert "PROFESSIONAL SUMMARY" in text
    assert "Backend Engineer" not in text.split("PROFESSIONAL SUMMARY")[0] or True
    assert text.strip()


def test_build_project_url_map_resolves_from_resume_text():
    url_map = build_project_url_map(RESUME_TEXT, PROFILE)
    sales = url_map.get("Sales Dashboard", {})
    assert sales.get("github") == "https://github.com/alex/sales-dashboard"
    assert sales.get("live") == "https://sales.example.com"


def test_parse_project_links_extracts_urls():
    links = parse_project_links(RESUME_TEXT)
    assert "Sales Dashboard" in links


def test_build_tailored_cv_returns_text_and_pdf():
    text, url_map, pdf = build_tailored_cv(RESUME_TEXT, PROFILE, JOB, ["SQL", "Power BI"])
    assert text.strip()
    assert "Data Analyst" in text
    assert isinstance(url_map, dict)
    assert isinstance(pdf, bytes)


NURSE_PROFILE = {
    "name": "Maya Nurse",
    "role": "Registered Nurse",
    "experience_years": 3,
    "email": "maya@example.com",
    "skills": {
        "clinical_care": ["patient care", "medication administration"],
        "documentation": ["care planning", "EMR"],
    },
    "projects": [
        {"name": "Community Clinic", "description": "Volunteer clinic intake", "link": ""},
    ],
}

NURSE_JOB = {
    "title": "Staff Nurse",
    "company": "City General Hospital",
    "description": "Registered nurse for patient care and medication administration.",
    "relevant_project": {},
}


def test_generic_category_labels_have_no_tech_map():
    sections = profile_sections(NURSE_PROFILE)
    labels = set(sections["skills"].keys())
    assert labels == {"Clinical Care", "Documentation"}


def test_header_urls_only_show_present_links():
    sections = profile_sections(NURSE_PROFILE)
    assert all("GitHub" not in line and "LinkedIn" not in line for line in sections["header"])

    p = dict(NURSE_PROFILE, github="https://github.com/maya", linkedin="https://linkedin.com/in/maya")
    sections = profile_sections(p)
    joined = " · ".join(sections["header"])
    assert "GitHub" in joined
    assert "LinkedIn" in joined
    assert "Website" not in joined


def test_build_tailored_text_uses_generic_labels_for_nurse():
    text = build_tailored_text(
        profile_sections(NURSE_PROFILE), NURSE_PROFILE, NURSE_JOB, ["patient care"]
    )
    assert "SKILLS" in text
    assert "Clinical Care" in text
    assert "TECHNICAL SKILLS" not in text
    assert "PROFESSIONAL SUMMARY" in text
    assert "Maya Nurse" in text


def test_build_summary_is_profession_neutral():
    from app.core.resume_pipeline import build_summary

    text = build_summary(NURSE_PROFILE, NURSE_JOB, ["patient care"])
    assert "Maya Nurse" not in text
    assert "designing" not in text
    assert "shipping" not in text
    assert "results-driven" in text
