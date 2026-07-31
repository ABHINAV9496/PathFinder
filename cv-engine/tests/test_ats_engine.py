"""Tests for the ATS Analyst engine (v3 rubric).

Run from repo root: pytest cv-engine/tests/test_ats_engine.py -q
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.ats_engine import (
    analyze,
    analyze_with_llm,
    build_gap_report,
    build_source_trace,
)
from app.core.profile_skills import resolve_skills

DATA_ANALYST_PROFILE = {
    "name": "Alex Data",
    "role": "Data Analyst",
    "experience_years": 4,
    "skills": {
        "tools": ["Python", "SQL", "Power BI", "Excel", "Tableau"],
        "techniques": ["data cleaning", "statistical analysis", "ETL", "dashboarding"],
    },
}

JD = (
    "Senior Data Analyst. Must have strong SQL and Power BI. "
    "Required: statistical analysis. Nice to have: Tableau. "
    "Excellent communication skills. 3+ years of experience."
)

PERFECT_RESUME = (
    "Alex Data\nData Analyst\nBangalore · 9999999999 · alex@example.com\n"
    "SUMMARY\n"
    "Data Analyst with 4+ years building production dashboards.\n"
    "SKILLS\n"
    "Tools: Python, SQL, Power BI, Excel, Tableau\n"
    "Techniques: data cleaning, statistical analysis, ETL, dashboarding\n"
    "EXPERIENCE\n"
    "Senior Data Analyst at Acme, 2023 - Present\n"
    "  • Built Power BI dashboards and optimized SQL queries\n"
    "  • Reduced reporting time by 40%\n"
    "PROJECTS\n"
    "Sales Dashboard — Power BI\n"
    "EDUCATION\n"
    "B.Tech\n"
)

GAP_RESUME = (
    "Alex Data\nData Analyst\nBangalore · 9999999999 · alex@example.com\n"
    "SUMMARY\n"
    "Data analyst.\n"
    "SKILLS\n"
    "Tools: Excel\n"
    "EXPERIENCE\n"
    "Analyst at Acme, 2022 - Present\n"
    "  • Made reports\n"
)


def test_analyze_tier_classification():
    report = analyze(JD, PERFECT_RESUME, DATA_ANALYST_PROFILE)
    t0 = report.tiers["tier0_required"]
    assert "SQL" in t0["matched"] or "sql" in t0["matched"]
    assert "statistical analysis" in [k.lower() for k in t0["matched"]]


def test_analyze_nice_to_have_tier():
    report = analyze(JD, PERFECT_RESUME, DATA_ANALYST_PROFILE)
    t5 = report.tiers["tier5_nice"]
    assert any("tableau" in k.lower() for k in t5["matched"] + t5["missing"])


def test_analyze_soft_skills_tier():
    report = analyze(JD, PERFECT_RESUME, DATA_ANALYST_PROFILE)
    t4 = report.tiers["tier4_soft"]
    assert any("communication" in k.lower() for k in t4["matched"] + t4["missing"])


def test_perfect_resume_scores_higher_than_gap_resume():
    perfect = analyze(JD, PERFECT_RESUME, DATA_ANALYST_PROFILE)
    gap = analyze(JD, GAP_RESUME, DATA_ANALYST_PROFILE)
    assert perfect.score > gap.score


def test_analyze_missing_keywords_and_fixes():
    report = analyze(JD, GAP_RESUME, DATA_ANALYST_PROFILE)
    assert report.missing_keywords
    assert report.fixes
    assert report.score >= 0 and report.score <= 100


def test_analyze_empty_resume_has_caveats():
    report = analyze(JD, "", DATA_ANALYST_PROFILE)
    assert report.caveats
    assert report.score <= 100


def test_analyze_breakdown_keys():
    report = analyze(JD, PERFECT_RESUME, DATA_ANALYST_PROFILE)
    breakdown_keys = (
        "keyword_coverage", "resume_quality", "parseability",
        "jd_tailoring", "frequency_recency",
    )
    for key in breakdown_keys:
        assert key in report.breakdown


def test_analyze_with_llm_falls_back_without_config():
    result = analyze_with_llm(JD, PERFECT_RESUME, DATA_ANALYST_PROFILE, ai_config={})
    assert result["source"] == "deterministic"
    assert "score" in result


def test_analyze_with_llm_bad_config_falls_back():
    result = analyze_with_llm(
        JD, PERFECT_RESUME, DATA_ANALYST_PROFILE,
        ai_config={"api_key": "x", "api_base_url": "http://127.0.0.1:1", "model": "m"},
    )
    assert result["source"] == "deterministic"


def test_build_gap_report_shape():
    report = analyze(JD, GAP_RESUME, DATA_ANALYST_PROFILE)
    gap = build_gap_report(report)
    assert "confirmed_gaps" in gap
    assert all("item" in g and "severity" in g for g in gap["confirmed_gaps"])


def test_build_source_trace_shape():
    report = analyze(JD, PERFECT_RESUME, DATA_ANALYST_PROFILE)
    trace = build_source_trace(report)
    assert all("claim" in t and "source" in t and "confirmed" in t for t in trace)


def test_profile_derived_vocab_drives_tiers():
    weights, _aliases, cats = resolve_skills(DATA_ANALYST_PROFILE)
    report = analyze(
        JD, GAP_RESUME, DATA_ANALYST_PROFILE,
        skill_weights=weights, skill_categories=cats,
    )
    assert report.source == "deterministic"


def test_signal_after_term_flags_required():
    from app.core.ats_engine import MUST_SIGNALS, _in_sentence_with_signal
    assert _in_sentence_with_signal(
        "We require Python and Django. Django is mandatory.",
        "django", MUST_SIGNALS,
    )


def test_signal_after_term_flags_nice_to_have():
    from app.core.ats_engine import NICE_SIGNALS, _in_sentence_with_signal
    assert _in_sentence_with_signal(
        "Docker is a nice to have. Git preferred.",
        "git", NICE_SIGNALS,
    )
    assert _in_sentence_with_signal(
        "Docker is a nice to have. Git preferred.",
        "docker", NICE_SIGNALS,
    )
