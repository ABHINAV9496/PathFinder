import base64
import html
import io
import logging
import re

from rest_framework import status

from apps.jobs.matcher import _extract_experience_years
from apps.jobs.models import Job
from apps.jobs.models.cred_store import CredStore
from apps.jobs.profile_manager import load_profile
from apps.jobs.views.base import BaseAPIView

logger = logging.getLogger(__name__)

_SECTION_ALIASES = {
    "professional summary": "summary",
    "summary": "summary",
    "technical skills": "skills",
    "skills": "skills",
    "professional experience": "experience",
    "work experience": "experience",
    "employment history": "experience",
    "experience": "experience",
    "projects": "projects",
    "project": "projects",
    "education": "education",
    "academic qualifications": "education",
}

_CATEGORY_LABELS = {
    "backend": "Backend",
    "frontend": "Frontend",
    "ai_llm": "AI / LLM",
    "ai": "AI / LLM",
    "cloud": "Cloud & Infra",
    "cloud_infra": "Cloud & Infra",
    "devops": "DevOps",
    "devops_ci": "DevOps & CI/CD",
    "tools": "Tools & CI/CD",
}

_HIGH_SEVERITY_GAPS = {
    "kubernetes", "k8s", "terraform", "gcp", "google cloud", "azure",
    "kafka", "rabbitmq", "microservices", "graphql", "mongodb",
}


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


def _parse_resume_sections(text: str) -> dict:
    """Parse the original resume PDF text into sections, preserving raw lines
    verbatim so the tailored resume keeps the candidate's exact template."""
    sections = {
        "header": [],
        "summary": [],
        "skills": {},
        "experience": [],
        "projects": [],
        "education": [],
        "other": [],
    }
    current = None
    header_done = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        lower = line.lower()
        if lower in _SECTION_ALIASES:
            current = _SECTION_ALIASES[lower]
            header_done = True
            continue
        if current is None:
            if not header_done and len(sections["header"]) < 4:
                sections["header"].append(line)
            continue
        if current == "skills":
            m = re.match(r"^([^:]+):\s*(.+)$", line)
            if m:
                cat = m.group(1).strip()
                skills = [s.strip().rstrip(",") for s in m.group(2).split(",")]
                skills = [s for s in skills if s]
                if skills:
                    sections["skills"].setdefault(cat, [])
                    for s in skills:
                        if s not in sections["skills"][cat]:
                            sections["skills"][cat].append(s)
            else:
                sections["other"].append(line)
        elif current == "summary":
            sections["summary"].append(line)
        elif current in ("experience", "projects", "education"):
            sections[current].append(line)
    return sections


def _profile_sections(profile: dict) -> dict:
    sections = {
        "header": [],
        "summary": [],
        "skills": {},
        "experience": [],
        "projects": [],
        "education": [],
        "other": [],
    }
    sections["header"] = [
        profile.get("name", ""),
        profile.get("role", ""),
        " · ".join(filter(None, [
            profile.get("location", ""),
            profile.get("phone", ""),
            profile.get("email", ""),
        ])),
        " · ".join(filter(None, ["GitHub", "LinkedIn", "Portfolio"])),
    ]
    sections["header"] = [h for h in sections["header"] if h]
    for cat, skills in profile.get("skills", {}).items():
        if skills:
            label = _CATEGORY_LABELS.get(cat.lower(), cat.replace("_", " ").title())
            sections["skills"][label] = list(skills)
    for p in profile.get("projects", []):
        sections["projects"].append(f"{p.get('name', '')} — {p.get('description', '')}")
        tech = ", ".join(p.get("tech", [])[:10])
        if tech:
            sections["projects"].append(tech)
        link = (p.get("link") or "").strip()
        if link:
            if "github.com" in link or "github.io" in link:
                sections["projects"].append(f"GitHub: {link}")
            else:
                sections["projects"].append(f"Live: {link} GitHub")
    for e in profile.get("experience", []):
        role = e.get("role", "")
        company = e.get("company", "")
        loc = e.get("location", "")
        dur = e.get("duration", "")
        line = f"{role} at {company}" if company else role
        if loc:
            line += f", {loc}"
        if dur:
            line += f"    {dur}"
        sections["experience"].append(line)
        for h in e.get("highlights", []):
            sections["experience"].append(f"\u2022 {h}")
    if profile.get("education"):
        sections["education"].append(profile["education"])
    return sections


def _enrich_sections(sections: dict, profile: dict) -> dict:
    if not sections["skills"]:
        for cat, skills in profile.get("skills", {}).items():
            if skills:
                label = _CATEGORY_LABELS.get(cat.lower(), cat.replace("_", " ").title())
                sections["skills"][label] = list(skills)
    if not sections["projects"]:
        for p in profile.get("projects", []):
            sections["projects"].append(f"{p.get('name', '')} — {p.get('description', '')}")
            tech = ", ".join(p.get("tech", [])[:10])
            if tech:
                sections["projects"].append(tech)
            link = (p.get("link") or "").strip()
            if link:
                if "github.com" in link or "github.io" in link:
                    sections["projects"].append(f"GitHub: {link}")
                else:
                    sections["projects"].append(f"Live: {link} GitHub")
    if not sections["experience"]:
        for e in profile.get("experience", []):
            role = e.get("role", "")
            company = e.get("company", "")
            loc = e.get("location", "")
            dur = e.get("duration", "")
            line = f"{role} at {company}" if company else role
            if loc:
                line += f", {loc}"
            if dur:
                line += f"    {dur}"
            sections["experience"].append(line)
            for h in e.get("highlights", []):
                sections["experience"].append(f"\u2022 {h}")
    if not sections["education"] and profile.get("education"):
        sections["education"].append(profile["education"])
    if not sections["header"] and profile.get("name"):
        sections["header"] = [
            profile.get("name", ""),
            profile.get("role", ""),
            " · ".join(filter(None, [
                profile.get("location", ""),
                profile.get("phone", ""),
                profile.get("email", ""),
            ])),
            " · ".join(filter(None, ["GitHub", "LinkedIn", "Portfolio"])),
        ]
        sections["header"] = [h for h in sections["header"] if h]
    return sections


def _reorder_skills(skills_by_cat: dict, matched_skills: list) -> dict:
    matched_lower = {s.lower() for s in (matched_skills or [])}

    def rank(skill: str) -> tuple:
        skill_lower = skill.lower()
        for m in matched_lower:
            if m in skill_lower or skill_lower in m:
                return (0, skill_lower)
        return (1, skill_lower)

    ordered = {}
    for cat, skills in skills_by_cat.items():
        ordered[cat] = sorted(skills, key=rank)
    return ordered


_TITLE_KEYWORDS = (
    "python", "backend", "frontend", "full-stack", "full stack", "fullstack",
    "django", "developer", "engineer", "ai", "llm",
)


def _has_skills(profile: dict, *keywords: str) -> bool:
    all_skills = " ".join(
        s.lower()
        for cat in profile.get("skills", {}).values()
        for s in cat
    )
    return any(k in all_skills for k in keywords)


def _choose_header_title(job, profile: dict) -> str:
    """Pick a header title the candidate can legitimately claim for this job.

    Never copies the JD title blindly: the chosen title must be backed by the
    candidate's actual skills. Falls back to the profile role when nothing
    is claimable."""
    jd_title = (getattr(job, "title", "") or "").lower()
    has_backend = _has_skills(profile, "python", "django", "drf", "fastapi", "flask", "sqlalchemy", "celery", "postgresql")
    has_frontend = _has_skills(profile, "react", "react.js", "reactjs", "typescript", "tailwind", "vue", "javascript")
    has_ai = _has_skills(profile, "llm", "groq", "openai", "langchain", "ai", "ast parsing")

    fullstack = any(k in jd_title for k in ("full stack", "fullstack", "full-stack"))
    backend = any(k in jd_title for k in ("backend", "back-end", "back end"))
    frontend = any(k in jd_title for k in ("frontend", "front-end", "front end"))
    python = "python" in jd_title
    django = "django" in jd_title
    ai = (
        any(k in jd_title for k in ("llm", "genai", "generative", "openai", "groq"))
        or " ai" in jd_title
        or jd_title.startswith("ai")
        or "ai/" in jd_title
        or "/ai" in jd_title
    )

    if ai and has_ai:
        title = "Python AI/LLM Developer" if python else "AI/LLM Developer"
    elif fullstack and has_frontend and has_backend:
        title = "Python Full-Stack Developer"
    elif backend and has_backend:
        title = "Python Backend Developer" if python else "Backend Developer"
    elif django and has_backend:
        title = "Django Developer"
    elif frontend and has_frontend:
        title = "Frontend Developer"
    elif python and has_backend:
        title = "Python Developer"
    else:
        title = profile.get("role") or "Python Full-Stack Developer"

    if "engineer" in jd_title:
        title = title.replace(" Developer", " Engineer")
    return title


def _build_summary(profile: dict, job, matched_skills: list) -> str:
    role = _choose_header_title(job, profile) or getattr(job, "title", "") or "Software Developer"
    years = profile.get("experience_years")
    project = getattr(job, "relevant_project", None) or {}
    strengths = ", ".join(matched_skills[:6]) if matched_skills else "Python web development"
    parts = []
    if years:
        parts.append(
            f"{role} with {years}+ year of hands-on experience designing, building "
            "and shipping production-ready web applications and APIs."
        )
    else:
        parts.append(
            f"{role} focused on designing, building and shipping "
            "production-ready web applications and APIs."
        )
    if project.get("description"):
        parts.append(
            f"Proven experience delivering {project.get('name', '')} "
            f"({project['description']})."
        )
    parts.append(f"Core strengths include {strengths}.")
    if job and getattr(job, "title", None) and getattr(job, "company", None):
        parts.append(
            f"Actively targeting the {job.title} role at {job.company}."
        )
    return " ".join(parts)


def _build_tailored_text(sections: dict, profile: dict, job, matched_skills: list) -> str:
    lines = []
    header = sections.get("header") or []
    header_title = _choose_header_title(job, profile)
    if len(header) >= 2:
        header_lines = [header[0], header_title] + header[2:]
    else:
        header_lines = list(header) + [header_title]
    for h in header_lines[:4]:
        lines.append(h)
    lines.append("")
    lines.append("PROFESSIONAL SUMMARY")
    lines.append(_build_summary(profile, job, matched_skills))
    lines.append("")
    lines.append("TECHNICAL SKILLS")
    for cat, skills in _reorder_skills(sections.get("skills", {}), matched_skills).items():
        if skills:
            lines.append(f"{cat}: {', '.join(skills)}")
    lines.append("")
    if sections.get("experience"):
        lines.append("PROFESSIONAL EXPERIENCE")
        lines.extend(sections["experience"])
        lines.append("")
    if sections.get("projects"):
        lines.append("PROJECTS")
        lines.extend(sections["projects"])
        lines.append("")
    if sections.get("education"):
        lines.append("EDUCATION")
        lines.extend(sections["education"])
    return "\n".join(lines).strip()


def _compute_ats_estimate(job, profile: dict, matched_skills: list, skill_gaps: list) -> dict:
    matched_skills = matched_skills or []
    skill_gaps = skill_gaps or []
    total_keywords = len(matched_skills) + len(skill_gaps)
    keyword_coverage = int(len(matched_skills) / total_keywords * 100) if total_keywords else 60
    skills_match = keyword_coverage

    jd_text = f"{getattr(job, 'description', '') or ''} {getattr(job, 'full_text', '') or ''}"
    required_years = _extract_experience_years(jd_text)
    exp_years = profile.get("experience_years", 0) or 0
    if required_years is None:
        experience_relevance = 80
    elif exp_years >= required_years:
        experience_relevance = 85
    elif exp_years + 1 >= required_years:
        experience_relevance = 60
    else:
        experience_relevance = 40

    project = getattr(job, "relevant_project", None)
    if project:
        projects_alignment = 85
    elif matched_skills:
        projects_alignment = min(60 + len(matched_skills) * 5, 85)
    else:
        projects_alignment = 40

    title = _choose_header_title(job, profile)

    def _norm(s: str) -> str:
        return (
            s.lower()
            .replace("full-stack", "full stack")
            .replace("fullstack", "full stack")
            .replace("-", " ")
        )

    jd_title_norm = _norm(getattr(job, "title", "") or "")
    title_norm = _norm(title)
    title_terms = [t for t in _TITLE_KEYWORDS if t in jd_title_norm]
    if title_terms:
        title_match = int(
            sum(1 for t in title_terms if t in title_norm)
            / len(title_terms)
            * 100
        )
    else:
        title_match = 70

    score = int(
        0.25 * skills_match
        + 0.2 * experience_relevance
        + 0.2 * projects_alignment
        + 0.2 * keyword_coverage
        + 0.15 * title_match
    )
    score = max(0, min(100, score))

    return {
        "score": score,
        "breakdown": {
            "skills_match": skills_match,
            "experience_relevance": experience_relevance,
            "projects_alignment": projects_alignment,
            "keyword_coverage": keyword_coverage,
            "title_match": title_match,
        },
        "summary": (
            f"Header '{title}' matches the JD title ({title_match}% title match); "
            f"skills match {skills_match}% of JD keywords; "
            f"experience relevance {experience_relevance}%."
        ),
    }


def _build_gap_report(skill_gaps: list) -> dict:
    confirmed = []
    for g in skill_gaps or []:
        severity = "high" if g.lower() in _HIGH_SEVERITY_GAPS else "medium"
        confirmed.append({
            "item": g,
            "severity": severity,
            "detail": "Required in JD, absent from resume",
        })
    return {"confirmed_gaps": confirmed, "research_flagged_gaps": []}


def _build_source_trace(matched_skills: list) -> list:
    trace = []
    for s in matched_skills or []:
        trace.append({
            "claim": f"Proficient in {s}",
            "source": "original_resume",
            "confirmed": True,
        })
    return trace


def _make_urls_clickable(text: str, url_map: dict) -> str:
    label_map = {
        "github": "GitHub",
        "linkedin": "LinkedIn",
        "portfolio": "Portfolio",
    }
    result = text
    for key, display in label_map.items():
        url = url_map.get(key)
        if url:
            result = re.sub(
                re.escape(display),
                f'<a href="{html.escape(url)}" target="_blank">{display}</a>',
                result,
                flags=re.IGNORECASE,
            )
    return result


def _parse_project_links(resume_text: str) -> dict:
    """Extract project names and their Live/GitHub URLs from the original resume
    text. Priority 1 for project link resolution."""
    links = {}
    in_projects = False
    current = None
    for raw in (resume_text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        lower = line.lower()
        if lower == "projects":
            in_projects = True
            continue
        if lower == "education":
            break
        if not in_projects:
            continue
        if line.startswith(("\u2022", "- ")):
            continue
        title_match = re.match(r"^(.+?)\s*[—–]\s*", line)
        if title_match and "http" not in line:
            candidate = title_match.group(1).strip()
            if candidate and not candidate.lower().startswith(("stack", "live", "github")):
                current = candidate
                links.setdefault(current, {})
                continue
        if current is None:
            continue
        live = re.search(r"Live:\s*(https?://\S+)", line, re.IGNORECASE)
        if live:
            links[current]["live"] = live.group(1).strip().rstrip(".,;)")
        github = re.search(r"GitHub:\s*(https?://\S+)", line, re.IGNORECASE)
        if github:
            links[current]["github"] = github.group(1).strip().rstrip(".,;)")
        if "GitHub" in line and "github" not in links[current]:
            links[current]["github"] = ""
    return links


def _build_project_url_map(resume_text: str, profile: dict) -> dict:
    """Resolve each project's Live/GitHub URLs by priority:
    1. URL present in the original resume text
    2. Profile project 'link' field
    3. Inferred from the profile GitHub username + project name
    """
    links = _parse_project_links(resume_text)
    github_base = (profile.get("github") or "").rstrip("/")
    profile_projects = {}
    for p in profile.get("projects", []):
        name = p.get("name", "").strip()
        if name:
            profile_projects[name.lower()] = p

    for name, info in links.items():
        if not info.get("github"):
            pp = profile_projects.get(name.lower())
            if pp and (pp.get("link") or "").strip():
                link = pp["link"].strip()
                if "github.com" in link or "github.io" in link:
                    info["github"] = link
                elif not info.get("live"):
                    info["live"] = link
        if not info.get("github") and github_base:
            slug = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-")
            info["github"] = f"{github_base}/{slug}"

    for p in profile.get("projects", []):
        name = p.get("name", "").strip()
        link_keys_lower = {k.lower() for k in links}
        if not name or name.lower() in link_keys_lower:
            continue
        info = {"live": "", "github": ""}
        link = (p.get("link") or "").strip()
        if link:
            if "github.com" in link or "github.io" in link:
                info["github"] = link
            else:
                info["live"] = link
        if not info["github"] and github_base:
            slug = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-")
            info["github"] = f"{github_base}/{slug}"
        links[name] = info
    return links


def _render_project_links(stripped: str, current_project: str, project_url_map: dict) -> str:
    links = project_url_map.get(current_project, {}) if current_project else {}
    parts = []
    live = None
    m = re.search(r"Live:\s*(https?://\S+)", stripped, re.IGNORECASE)
    if m:
        live = m.group(1).strip().rstrip(".,;)")
    if not live and re.search(r"\bLive\b", stripped, re.IGNORECASE):
        live = links.get("live")
    if not live and "http" in stripped:
        urls = re.findall(r"https?://\S+", stripped)
        if urls:
            live = urls[0].rstrip(".,;)")
    if live:
        parts.append(f'<a href="{html.escape(live)}">{html.escape("Live")}</a>')
    github = None
    m = re.search(r"GitHub:\s*(https?://\S+)", stripped, re.IGNORECASE)
    if m:
        github = m.group(1).strip().rstrip(".,;)")
    if not github and re.search(r"\bGitHub\b", stripped):
        github = links.get("github")
    if github:
        parts.append(f'<a href="{html.escape(github)}">{html.escape("GitHub")}</a>')
    if not parts:
        return ""
    return " &nbsp;|&nbsp; ".join(parts)


_RESUME_SECTION_HEADERS = {
    "professional summary", "summary", "technical skills", "skills",
    "projects", "experience", "work experience", "employment history",
    "professional experience", "education",
}


def _resume_to_html(text: str, profile: dict = None, project_url_map: dict = None) -> str:
    lines = text.split("\n")
    html_parts = ['<div class="resume">']
    in_header = True
    header_count = 0
    in_projects = False
    current_project = None
    project_url_map = project_url_map or {}

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

        if in_header and header_count < 4:
            rendered = _make_urls_clickable(stripped, url_map) if header_count >= 2 else stripped
            if header_count == 0:
                html_parts.append(f'<div class="header-name">{rendered}</div>')
            elif header_count == 1:
                html_parts.append(f'<div class="header-title">{rendered}</div>')
            elif header_count == 2:
                html_parts.append(f'<div class="header-contact">{rendered}</div>')
            elif header_count == 3:
                html_parts.append(f'<div class="header-urls">{rendered}</div>')
            header_count += 1
            continue

        lower = stripped.lower()
        if lower in _RESUME_SECTION_HEADERS:
            in_projects = (lower == "projects")
            current_project = None
            html_parts.append(f'<h2 class="section-title">{stripped}</h2>')
            continue

        if stripped.startswith("\u2022") or stripped.startswith("- "):
            content = stripped.lstrip("\u2022- ")
            html_parts.append(f'<div class="bullet"><span class="bullet-char">\u2022</span>{content}</div>')
            continue

        if in_projects:
            title_match = re.match(r"^(.+?)\s*[—–]\s*", stripped)
            if title_match and "http" not in stripped:
                candidate = title_match.group(1).strip()
                if candidate and not candidate.lower().startswith(("stack", "live", "github")):
                    current_project = candidate

            if re.search(r"https?://", stripped):
                links_html = _render_project_links(stripped, current_project, project_url_map)
                if links_html:
                    html_parts.append(f'<div class="project-links">{links_html}</div>')
                continue

        standalone_link = None
        if in_projects:
            standalone_link = re.match(
                r'^\s*(Live\s+Demo|GitHub(?:\s+Link)?|Demo(?:\s+Link)?)\s*$',
                stripped, re.IGNORECASE
            )
        if standalone_link:
            link_label = standalone_link.group(1)
            href = "#"
            links = project_url_map.get(current_project, {}) if current_project else {}
            if "github" in link_label.lower():
                href = links.get("github") or "#"
            else:
                href = links.get("live") or "#"
            html_parts.append(
                f'<div class="project-links"><a href="{html.escape(href)}">{link_label}</a></div>'
            )
            continue

        date_match = re.search(r'(\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\s*[–\-]\s*(Present|Current|\d{4})\b|\b\d{4}\s*[–\-]\s*(Present|Current|\d{4})\b|\b\w+\s+\d{4}\b)', stripped)
        if date_match and len(stripped) > len(date_match.group()) + 5:
            parts = stripped.rsplit(date_match.group(), 1)
            html_parts.append(
                f'<table class="two-col"><tr>'
                f'<td class="left">{parts[0].strip()}</td>'
                f'<td class="right">{date_match.group().strip()}</td>'
                f'</tr></table>'
            )
            continue

        _COMPANY_SUFFIXES = {"Solutions", "Technologies", "Ltd", "Inc", "Tech", "Digital", "Labs", "Systems", "Software", "Group", "Corp", "LLC"}
        if header_count >= 4:
            location_match = re.search(r'\s{3,}(\S.*)$', stripped)
            if not location_match:
                location_match = re.search(r',\s*([A-Z][a-zA-Z\s]+)$', stripped)
            if not location_match and any(suffix in stripped for suffix in _COMPANY_SUFFIXES):
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

        html_parts.append(f'<div class="content-line">{stripped}</div>')

    html_parts.append("</div>")

    return (
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        "<style>"
        "@page{size:letter;margin:14pt 18pt;}"
        "body{margin:0;padding:0;font-family:Helvetica,Arial,sans-serif;font-size:8.5pt;color:#222;}"
        ".resume{width:100%;margin:16px auto;}"
        ".header-name{text-align:center;font-size:14pt;font-weight:bold;margin-bottom:1px;}"
        ".header-title{text-align:center;font-size:11pt;font-weight:bold;color:#333;margin-bottom:3px;}"
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
        ".project-links{text-align:right;font-size:8pt;color:#2a5db0;margin:0 0 1px 0;}"
        ".project-links a{color:#2a5db0;text-decoration:none;}"
        "</style>"
        "</head><body>"
        f"{''.join(html_parts)}"
        "</body></html>"
    )


def _generate_pdf(resume_text: str, profile: dict = None, project_url_map: dict = None) -> bytes:
    html = _resume_to_html(resume_text, profile, project_url_map)
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

        profile = load_profile()
        resume_text = _extract_resume_text()
        profile["resume_text"] = resume_text

        if not resume_text and not profile.get("skills") and not profile.get("experience") and not profile.get("projects"):
            return self.error(
                "No resume content found. Upload your resume PDF in Profile settings.",
                status.HTTP_400_BAD_REQUEST,
            )

        job_dict = {
            "title": job.title or "",
            "company": job.company or "",
            "location": job.location or "",
            "description": job.description or "",
            "matched_skills": job.matched_skills or [],
            "skill_gaps": job.skill_gaps or [],
            "skill_score_breakdown": job.skill_score_breakdown or {},
            "match_score": job.match_score or 0,
            "relevant_project": getattr(job, "relevant_project", None),
        }

        try:
            from apps.jobs.services.cv_engine_client import CVEngineUnavailableError, generate_cv
            result = generate_cv(job_dict, profile)
            ats = result.get("ats_report") or {}
            score_estimate = {
                "score": ats.get("score"),
                "breakdown": ats.get("breakdown") or {},
                "summary": ats.get("summary") or "",
            }
            if ats.get("source") == "deterministic":
                score_estimate["summary"] = ats.get("summary") or score_estimate["summary"]
            return self.success({
                "tailored_resume": result.get("tailored_resume", ""),
                "ats_score_estimate": score_estimate,
                "gap_report": result.get(
                    "gap_report", {"confirmed_gaps": [], "research_flagged_gaps": []}
                ),
                "source_trace": result.get("source_trace", []),
                "suggested_keywords": result.get("suggested_keywords", []),
                "ats_report": ats,
                "pdf_base64": result.get("pdf_base64", ""),
                "filename": result.get("filename", "Resume.pdf"),
            })
        except CVEngineUnavailableError as e:
            logger.warning("CV engine unavailable for job %d; using local fallback: %s", job_id, e)

        matched_skills = job.matched_skills or []
        skill_gaps = job.skill_gaps or []
        if not matched_skills or not skill_gaps:
            from apps.jobs.matcher import _find_matching_skills, _find_skill_gaps
            jd_text = f"{job.title or ''} {job.description or ''}"
            if not matched_skills:
                matched_skills, _ = _find_matching_skills(jd_text)
            if not skill_gaps:
                skill_gaps = _find_skill_gaps(jd_text)

        if resume_text:
            sections = _parse_resume_sections(resume_text)
        else:
            sections = _profile_sections(profile)
        sections = _enrich_sections(sections, profile)

        if not sections["skills"] and not sections["experience"] and not sections["projects"]:
            return self.error(
                "No resume content found. Upload your resume PDF in Profile settings.",
                status.HTTP_400_BAD_REQUEST,
            )

        tailored_text = _build_tailored_text(sections, profile, job, matched_skills)
        project_url_map = _build_project_url_map(resume_text, profile)
        ats_estimate = _compute_ats_estimate(job, profile, matched_skills, skill_gaps)
        gap_report = _build_gap_report(skill_gaps)
        source_trace = _build_source_trace(matched_skills)

        pdf_bytes = _generate_pdf(tailored_text, profile, project_url_map)
        pdf_base64_str = base64.b64encode(pdf_bytes).decode() if pdf_bytes else ""

        filename = f"{profile.get('name', 'Developer').replace(' ', '_')}.pdf"

        response_data = {
            "tailored_resume": tailored_text,
            "ats_score_estimate": ats_estimate,
            "gap_report": gap_report,
            "source_trace": source_trace,
            "suggested_keywords": matched_skills,
            "pdf_base64": pdf_base64_str,
            "filename": filename,
        }
        return self.success(response_data)
