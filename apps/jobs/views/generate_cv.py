import base64
import io
import json
import logging
import re

from rest_framework import status
from rest_framework.response import Response

from apps.jobs.models import Job
from apps.jobs.models.cred_store import CredStore
from apps.jobs.profile_manager import load_profile
from apps.jobs.llm_client import generate_with_llm
from apps.jobs.views.base import BaseAPIView

logger = logging.getLogger(__name__)


def _extract_resume_text() -> str:
    creds = CredStore.load()
    if not creds.has_resume:
        return ""
    try:
        import pypdf
        reader = pypdf.PdfReader(creds.resume_file.path)
        text = ""
        for page in reader.pages:
            text += (page.extract_text() or "") + "\n"
        return text.strip()
    except Exception as e:
        logger.warning("Failed to extract resume PDF text: %s", e)
        return ""


def _format_profile_for_prompt(profile: dict) -> str:
    lines = []
    name = profile.get("name", "")
    role = profile.get("role", "")
    location = profile.get("location", "")
    exp_years = profile.get("experience_years", "")
    if name:
        lines.append(f"Name: {name}")
    if role:
        lines.append(f"Current Role: {role}")
    if location:
        lines.append(f"Location: {location}")
    if exp_years:
        lines.append(f"Total Experience: {exp_years} year(s)")

    lines.append("")
    lines.append("--- Projects ---")
    for p in profile.get("projects", []):
        tech = ", ".join(p.get("tech", [])[:8])
        lines.append(f"- {p['name']}: {p.get('description', '')}")
        if tech:
            lines.append(f"  Tech: {tech}")

    lines.append("")
    lines.append("--- Experience ---")
    for e in profile.get("experience", []):
        parts = [e.get("role", ""), "at", e.get("company", "")]
        if e.get("duration"):
            parts.append(f"({e['duration']})")
        lines.append("- " + " ".join(parts))

    lines.append("")
    lines.append("--- Skills ---")
    for cat, skills in profile.get("skills", {}).items():
        if skills:
            lines.append(f"{cat}: {', '.join(skills)}")

    return "\n".join(lines)


def _build_system_prompt() -> str:
    return (
        "You are a resume-tailoring engine. You receive THREE inputs and must treat "
        "them with different levels of trust.\n"
        "\n"
        "## INPUTS\n"
        "\n"
        "1. original_resume (GROUND TRUTH — highest trust)\n"
        "   The candidate's full unedited resume. Every fact used in the tailored "
        "resume — employers, dates, tools, project details — must trace back to "
        "this document. This is the only source that can supply candidate facts.\n"
        "\n"
        "2. job_fetcher_data (JD GROUND TRUTH — highest trust)\n"
        "   The job description as scraped/fetched directly from the posting "
        "(LinkedIn, company careers page, etc). Use this verbatim for role "
        "title, required skills, responsibilities, and stated requirements "
        "(years of experience, must-haves vs nice-to-haves).\n"
        "\n"
        "3. company_web_research (CONTEXTUAL SIGNAL — lower trust, must be labeled)\n"
        "   AI-gathered info about the company: tech stack, recent funding/news, "
        "engineering culture, product direction. This may be incomplete, outdated, "
        "or inferred rather than confirmed. Use this ONLY to:\n"
        "     - inform tone/terminology alignment (e.g. if research shows the "
        "company is Kubernetes-heavy, prioritize the candidate's real K8s "
        "experience higher in the resume)\n"
        "     - flag additional gap context in the gap_report\n"
        "   NEVER use company_web_research to justify inserting a skill, tool, or "
        "qualification into the resume itself. It informs prioritization and "
        "framing, not resume content. Resume content only ever comes from "
        "original_resume.\n"
        "\n"
        "## TRUST HIERARCHY RULE\n"
        "If company_web_research suggests something not confirmed by "
        "job_fetcher_data or original_resume, treat it as a 'consider mentioning "
        "in cover note' signal at most — never as resume fact. Cite in gap_report "
        "as 'unverified — from web research' if relevant, so the candidate knows "
        "it's not sourced from the actual posting.\n"
        "\n"
        "## THE CORE PROBLEM TO SOLVE\n"
        "- NO FABRICATION: Every skill, date, employer, project detail, metric, "
        "and technology in the tailored_resume must have a direct source in "
        "original_resume. If original_resume does not mention it, do not include "
        "it, even if company_web_research or job_fetcher_data suggest it would "
        "be a good fit.\n"
        "- GAP CLASSIFICATION: Categorize each gap between the candidate and the "
        "job into one of three buckets:\n"
        "  (a) confirmed_gap — skill/requirement is in job_fetcher_data and "
        "verifiably absent from original_resume\n"
        "  (b) research_flagged_gap — signal came from company_web_research only "
        "and is not confirmed by job_fetcher_data or original_resume\n"
        "  (c) not a gap — skill appears in original_resume even if under a "
        "different name or category; resolve aliases before flagging\n"
        "- HONEST SCORING: The ATS score must reflect genuine overlap between "
        "original_resume and job_fetcher_data. Do not inflate scores to make the "
        "candidate look stronger. A score of 60 with an honest breakdown is more "
        "useful than a score of 85 with fabricated justification.\n"
        "- SOURCE TRACE: Every substantive claim in the tailored_resume must be "
        "traceable to a specific sentence or section in original_resume.\n"
        "\n"
        "## OUTPUT REQUIRED\n"
        "You MUST respond with valid JSON only (no markdown, no code fences, no "
        "explanatory text). The JSON must have exactly these keys:\n"
        "\n"
        "{\n"
        '  "tailored_resume": "The full tailored resume text, rewritten to '
        'emphasize the most relevant experience for this specific job. '
        'Rewrite section ordering and emphasis but do not fabricate.",\n'
        '  "ats_score_estimate": {\n'
        '    "score": 0-100 integer,\n'
        '    "breakdown": {\n'
        '      "skills_match": 0-100,\n'
        '      "experience_relevance": 0-100,\n'
        '      "projects_alignment": 0-100,\n'
        '      "keyword_coverage": 0-100\n'
        "    },\n"
        '    "summary": "1-2 sentence honest assessment"\n'
        "  },\n"
        '  "gap_report": {\n'
        '    "confirmed_gaps": [\n'
        '      {"item": "Kubernetes", "severity": "high|medium|low", '
        '"detail": "Required in JD, absent from resume"}\n'
        "    ],\n"
        '    "research_flagged_gaps": [\n'
        '      {"item": "Terraform", "severity": "medium", '
        '"detail": "Mentioned in company blog but not in JD — unverified"}\n'
        "    ]\n"
        "  },\n"
        '  "source_trace": [\n'
        '    {"claim": "Built REST APIs with Django", '
        '"source": "original_resume", "confirmed": true}\n'
        "  ]\n"
        "}\n"
        "\n"
        "RULES:\n"
        "- Never let company_web_research leak into resume content as a "
        "fabricated qualification. It is context for framing, not a data source "
        "for facts.\n"
        "- Every entry in source_trace must have confirmed=true. If any claim "
        "cannot be confirmed from original_resume, remove it from the resume.\n"
         "- KEEP THE TAILORED_RESUME under 600 words.\n"
         "- Do not add a cover letter or salutation — this is a resume, not a "
         "cover letter.\n"
         "- Use plain text only, no markdown formatting in the resume text.\n"
         "\n"
         "## FORMAT PRESERVATION — MANDATORY\n"
         "- Section headers must use exact Title Case as in the original resume: "
         "'Professional Summary', 'Technical Skills', 'Projects', 'Experience', "
         "'Education'. Do NOT use ALL CAPS. Do NOT invent new sections like "
         "'Certifications', 'Availability', or 'Highlights'.\n"
         "- Skill category names must be preserved exactly as they appear in the "
         "original: 'Cloud & DevOps', 'AI & Tools'. Do not rename or rephrase them.\n"
         "- Header block formatting must match the original:\n"
         "    Line 1: Name in ALL CAPS (centered)\n"
         "    Line 2: Title in Title Case (centered)\n"
         "    Line 3: Contact line with pipe separators (centered) — "
         "'City, State|email |phone'\n"
         "    Line 4: URLs separated by pipes — 'LinkedIn |Portfolio |GitHub'\n"
         "- Dates must appear right-aligned on the same line as their role or degree.\n"
         "- 'Live Demo' links must appear right-aligned on the same line as the "
         "project name.\n"
         "- Location must appear right-aligned on the same line as the company name.\n"
         "- Use '•' (bullet) characters for skill and description lists.\n"
          "- The overall section ordering must be: Summary → Skills → Projects → "
         "Experience → Education. Do not reorder or insert sections between them.\n"
         "\n"
         "## SPACING RULES — MANDATORY\n"
         "- There must ALWAYS be a space between the role title and the date: "
         "'Full Stack Developer Sep 2025' — never 'Full Stack DeveloperSep 2025'.\n"
         "- There must ALWAYS be a space between the company name and location: "
         "'Bridgeon Solutions Kozhikode' — never 'Bridgeon SolutionsKozhikode'.\n"
         "- There must ALWAYS be a space after a comma: 'Technology, Ernakulam' — "
         "never 'Technology,Ernakulam'.\n"
         "- Skills line format: '�Languages:Python, JavaScript' — the bullet "
         "is followed immediately by the category name and colon, then a single "
         "space before each subsequent item.\n"
         "- Education year: 'Engineering)2025' — no space before the year.\n"
         "- Project name with Live Demo: there must be a space before 'Live Demo': "
         "'Detector Live Demo'."
    )


def _build_user_prompt(job, resume_text: str, profile: dict, company_research: dict) -> str:
    matched_skills = ", ".join(job.matched_skills or []) or "None listed"
    skill_gaps = ", ".join(job.skill_gaps or []) or "None identified"

    research_lines = []
    if company_research:
        for key, val in company_research.items():
            if isinstance(val, list):
                research_lines.append(f"{key}: {', '.join(val)}")
            elif val:
                research_lines.append(f"{key}: {val}")
    research_text = "\n".join(research_lines) if research_lines else "No additional research available."

    return (
        "## original_resume (GROUND TRUTH — highest trust)\n"
        "Below is the candidate's full resume text extracted from their uploaded PDF, "
        "followed by structured profile data from the system.\n"
        "\n"
        "### Resume PDF Text:\n"
        f"{resume_text or '(No PDF resume uploaded — using structured profile data only)'}\n"
        "\n"
        "### Structured Profile Data:\n"
        f"{_format_profile_for_prompt(profile)}\n"
        "\n"
        "## job_fetcher_data (JD GROUND TRUTH — highest trust)\n"
        f"Company: {job.company}\n"
        f"Title: {job.title}\n"
        f"Location: {job.location or 'Not specified'}\n"
        f"Apply URL: {job.apply_url or 'N/A'}\n"
        f"Matched Skills: {matched_skills}\n"
        f"Skill Gaps: {skill_gaps}\n"
        f"Match Score: {job.match_score or 0}/100\n"
        "\n"
        "### Job Description:\n"
        f"{(job.description or '')[:4000]}\n"
        "\n"
        "## company_web_research (CONTEXTUAL SIGNAL — lower trust)\n"
        f"{research_text}\n"
        "\n"
        "Now produce the tailored resume as specified in the system prompt. "
        "Output ONLY valid JSON."
    )


def _parse_llm_output(raw: str) -> dict:
    cleaned = raw.strip()
    json_match = re.search(r"\{[\s\S]*\}", cleaned)
    if json_match:
        candidate = json_match.group()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    return {}


def _validate_tailored_resume(data: dict, job, profile: dict, resume_text: str) -> list[str]:
    issues = []
    if not isinstance(data, dict):
        issues.append("not_json_object")
        return issues

    if "tailored_resume" not in data or not isinstance(data.get("tailored_resume"), str) or not data["tailored_resume"].strip():
        issues.append("missing_tailored_resume")

    ats = data.get("ats_score_estimate", {})
    if not isinstance(ats, dict):
        issues.append("ats_score_not_object")
    else:
        score = ats.get("score")
        if not isinstance(score, (int, float)) or score < 0 or score > 100:
            issues.append("invalid_ats_score")

    gap_report = data.get("gap_report", {})
    if not isinstance(gap_report, dict):
        issues.append("gap_report_not_object")
    else:
        confirmed = gap_report.get("confirmed_gaps", [])
        if not isinstance(confirmed, list):
            issues.append("confirmed_gaps_not_list")

    source_trace = data.get("source_trace", [])
    if not isinstance(source_trace, list):
        issues.append("source_trace_not_list")
    elif len(source_trace) == 0:
        issues.append("empty_source_trace")
    else:
        for entry in source_trace:
            if not entry.get("confirmed"):
                issues.append("unconfirmed_claim_in_source_trace")

    return issues


_RESUME_SAMPLE_CLAIMS_PATTERNS = [
    r"\b\d{2,}\s*%",
    r"\b\d[\d,]*\.?\d*\s*[KkMmBb]",
    r"\b(sub-?\d+|\d+\+?)\s*(ms|seconds?|minutes?|hours?)",
]


def _check_fabricated_numbers(text: str, profile_source: str) -> list[str]:
    issues = []
    source_lower = profile_source.lower()
    for pattern in _RESUME_SAMPLE_CLAIMS_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            raw = match.group()
            normalized = re.sub(r"\s+", "", raw.lower())
            digit_part = re.sub(r"[^\d.]", "", raw)
            if digit_part and digit_part not in source_lower and normalized not in source_lower:
                issues.append(f"unverified_number:{raw.strip()}")
    return issues


_RESUME_SECTION_HEADERS = {
    "professional summary", "technical skills", "projects",
    "experience", "education",
}


def _make_urls_clickable(text: str, url_map: dict) -> str:
    labels = {"linkedin", "portfolio", "github"}
    result = text
    for label in labels:
        url = url_map.get(label)
        if url:
            result = re.sub(
                re.escape(label.capitalize()),
                f'<a href="{url}" target="_blank">{label.capitalize()}</a>',
                result,
                flags=re.IGNORECASE,
            )
    return result


def _resume_to_html(text: str, profile: dict = None) -> str:
    lines = text.split("\n")
    html_parts = ['<div class="resume">']
    in_header = True
    header_count = 0

    # Build URL map for clickable links
    url_map = {}
    if profile:
        if profile.get("linkedin"): url_map["linkedin"] = profile["linkedin"]
        if profile.get("portfolio"): url_map["portfolio"] = profile["portfolio"]
        if profile.get("github"): url_map["github"] = profile["github"]

    for line in lines:
        stripped = line.strip()
        if not stripped:
            html_parts.append('<div class="spacer"></div>')
            if header_count >= 2:
                in_header = False
            continue

        # Header block: first 1-4 non-empty lines (name, title, contact, urls)
        if in_header and header_count < 4:
            if header_count == 0:
                html_parts.append(f'<div class="header-name">{stripped}</div>')
            elif header_count == 1:
                html_parts.append(f'<div class="header-title">{stripped}</div>')
            elif header_count == 2:
                html_parts.append(f'<div class="header-contact">{stripped}</div>')
            elif header_count == 3:
                html_parts.append(f'<div class="header-urls">{_make_urls_clickable(stripped, url_map)}</div>')
            header_count += 1
            continue

        # Section headers
        lower = stripped.lower()
        if lower in _RESUME_SECTION_HEADERS:
            html_parts.append(f'<h2 class="section-title">{stripped}</h2>')
            continue

        # Bullet points
        if stripped.startswith("\u2022") or stripped.startswith("- "):
            content = stripped.lstrip("\u2022- ")
            html_parts.append(f'<div class="bullet"><span class="bullet-char">\u2022</span>{content}</div>')
            continue

        # Line with "Live Demo" right-aligned
        if "Live Demo" in stripped:
            parts = stripped.rsplit("Live Demo", 1)
            html_parts.append(
                f'<table class="two-col"><tr>'
                f'<td class="left">{parts[0].strip()}</td>'
                f'<td class="right"><a href="#">Live Demo</a></td>'
                f'</tr></table>'
            )
            continue

        # Line with a date range (e.g. "Sep 2025 – Present", "2025")
        date_match = re.search(r'(\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\s*[–\-]\s*(Present|Current|\d{4})\b|\b\d{4}\s*[–\-]\s*(Present|Current|\d{4})\b|\b\w+\s+\d{4}\b)', stripped)
        if date_match and ("Developer" in stripped or "Engineer" in stripped or "Intern" in stripped or "Bachelor" in stripped or "Master" in stripped or "Degree" in stripped):
            parts = stripped.rsplit(date_match.group(), 1)
            html_parts.append(
                f'<table class="two-col"><tr>'
                f'<td class="left">{parts[0].strip()}</td>'
                f'<td class="right">{date_match.group().strip()}</td>'
                f'</tr></table>'
            )
            continue

        # Line with a location after company name
        if header_count >= 4 and ("Solutions" in stripped or "Technologies" in stripped or "Ltd" in stripped or "Inc" in stripped or "Tech" in stripped or "Digital" in stripped or "Labs" in stripped):
            location_match = re.search(r'\s{3,}(\S.*)$', stripped)
            if not location_match:
                location_match = re.search(r'[,]\s*(\w+.*)$', stripped)
            if location_match and location_match.group(1) and not any(c.isdigit() for c in location_match.group(1)[:3]):
                parts = stripped.rsplit(location_match.group(1), 1)
                html_parts.append(
                    f'<table class="two-col"><tr>'
                    f'<td class="left">{parts[0].strip()}</td>'
                    f'<td class="right">{location_match.group(1).strip()}</td>'
                    f'</tr></table>'
                )
                continue

        # Regular content line (tech stack, descriptions)
        html_parts.append(f'<div class="content-line">{stripped}</div>')

    html_parts.append("</div>")

    return (
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        "<style>"
        "@page{size:letter;margin:14pt 18pt;}"
        "body{margin:0;padding:0;font-family:Helvetica,Arial,sans-serif;font-size:8.5pt;color:#222;}"
        ".resume{width:100%;margin:16px auto;}"
        ".header-name{text-align:center;font-size:13pt;font-weight:bold;margin-bottom:1px;}"
        ".header-title{text-align:center;font-size:9.5pt;color:#444;margin-bottom:3px;}"
        ".header-contact{text-align:center;font-size:7.5pt;color:#555;margin-bottom:1px;}"
        ".header-urls{text-align:center;font-size:7.5pt;color:#555;margin-bottom:4px;}"
        ".spacer{height:3px;}"
        "h2.section-title{font-size:9.5pt;font-weight:bold;margin:5px 0 2px 0;padding:0;border-bottom:1px solid #ccc;}"
        ".bullet{margin:0 0 0 0;padding-left:12px;font-size:8pt;line-height:1.25;}"
        ".bullet-char{margin-left:-12px;float:left;width:12px;}"
        "table.two-col{width:100%;margin:0;border-collapse:collapse;}"
        "td.left{text-align:left;font-weight:bold;font-size:8.5pt;vertical-align:top;padding:0;}"
        "td.right{text-align:right;font-size:8pt;color:#555;vertical-align:top;padding:0;}"
        ".content-line{margin:0 0;font-size:8pt;line-height:1.25;}"
        "</style>"
        "</head><body>"
        f"{''.join(html_parts)}"
        "</body></html>"
    )


def _generate_pdf(resume_text: str, profile: dict = None) -> bytes:
    html = _resume_to_html(resume_text, profile)
    try:
        from xhtml2pdf import pisa
        pdf_buffer = io.BytesIO()
        pisa_status = pisa.CreatePDF(
            io.StringIO(html),
            dest=pdf_buffer,
        )
        if pisa_status.err:
            logger.warning("PDF generation had errors: %s", pisa_status.err)
        return pdf_buffer.getvalue()
    except Exception as e:
        logger.error("PDF generation failed: %s", e)
        return b""


class GenerateCV(BaseAPIView):
    def post(self, request, job_id):
        try:
            job = Job.objects.get(pk=job_id)
        except Job.DoesNotExist:
            return self.error("Job not found", status.HTTP_404_NOT_FOUND)

        from apps.jobs.models.ai_config import AIConfig
        ai = AIConfig.load()
        if not ai.has_ai_config:
            return self.error(
                "AI not configured. Set your API key in Profile > AI Settings.",
                status.HTTP_400_BAD_REQUEST,
            )

        api_key = ai.get_api_key()
        if not api_key:
            return self.error(
                "Could not decrypt API key. Please re-save your AI Settings.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        profile = load_profile()
        resume_text = _extract_resume_text()

        company_research = {}
        try:
            if job.company:
                from apps.jobs.services.cv_engine_client import enrich_company_with_ai
                company_research = enrich_company_with_ai(
                    company=job.company,
                    job_description=job.description or "",
                    api_key=api_key,
                    api_base_url=ai.api_base_url,
                    model=ai.model_name,
                    provider=ai.provider,
                )
                logger.info("AI enrichment for %s: %d keywords", job.company,
                            len(company_research.get("must_have_keywords", [])))
        except Exception as e:
            logger.warning("AI enrichment failed for %s: %s", job.company, e)

        system_prompt = _build_system_prompt()
        user_prompt = _build_user_prompt(job, resume_text, profile, company_research)

        raw_output, llm_error = generate_with_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            api_key=api_key,
            api_base_url=ai.api_base_url,
            model=ai.model_name,
            provider=ai.provider,
        )

        if not raw_output:
            msg = f"AI generation failed: {llm_error}" if llm_error else "AI generation failed. Check your API key and model in AI Settings."
            return self.error(msg, status.HTTP_502_BAD_GATEWAY)

        parsed = _parse_llm_output(raw_output)
        issues = _validate_tailored_resume(parsed, job, profile, resume_text)

        profile_source_text = resume_text + " " + _format_profile_for_prompt(profile)
        resume_body = parsed.get("tailored_resume", "")
        if resume_body:
            numeric_issues = _check_fabricated_numbers(resume_body, profile_source_text)
            issues.extend(numeric_issues)

        hard_issues = [i for i in issues if i not in ("missing_salutation", "signature_repaired")]

        if hard_issues:
            retry_prompt = (
                f"Your previous attempt had these issues: "
                f"{'; '.join(hard_issues)}. Fix each one. "
                f"Ensure output is valid JSON with all required keys. "
                f"Do not fabricate any data. Every claim must trace to the resume."
            )
            retry_system = system_prompt + "\n\n" + retry_prompt
            retry_raw, retry_error = generate_with_llm(
                system_prompt=retry_system,
                user_prompt=user_prompt,
                api_key=api_key,
                api_base_url=ai.api_base_url,
                model=ai.model_name,
                provider=ai.provider,
            )

            if retry_raw:
                retry_parsed = _parse_llm_output(retry_raw)
                retry_issues = _validate_tailored_resume(retry_parsed, job, profile, resume_text)
                retry_body = retry_parsed.get("tailored_resume", "")
                if retry_body:
                    retry_numeric = _check_fabricated_numbers(retry_body, profile_source_text)
                    retry_issues.extend(retry_numeric)
                retry_hard = [i for i in retry_issues if i not in ("missing_salutation", "signature_repaired")]

                if retry_hard:
                    logger.warning(
                        "Retry still has hard issues for job %d (%s): %s",
                        job.id, job.company, "; ".join(retry_hard),
                    )
                    return Response(
                        {
                            "error": (
                                "Resume tailoring had accuracy issues that could not be "
                                f"auto-corrected: {'; '.join(retry_hard)}. Try again."
                            ),
                            "draft_with_warnings": retry_parsed,
                        },
                        status=status.HTTP_502_BAD_GATEWAY,
                    )

                parsed = retry_parsed
                resume_body = parsed.get("tailored_resume", "")

        # Generate PDF from the tailored resume text
        pdf_bytes = _generate_pdf(resume_body, profile) if resume_body else b""
        pdf_base64_str = base64.b64encode(pdf_bytes).decode() if pdf_bytes else ""

        filename = f"{profile.get('name', 'Developer').replace(' ', '_')}.pdf"

        response_data = {
            **parsed,
            "pdf_base64": pdf_base64_str,
            "filename": filename,
        }
        return self.success(response_data)
