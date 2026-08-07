"""Resume-preserving tailored CV pipeline (profession-agnostic).

Ported from Django's ``apps/jobs/views/generate_cv.py`` so the CV Engine is
the single source of truth for tailored resume generation. The original
uploaded resume's raw text is parsed into sections and reused verbatim so the
tailored resume keeps the candidate's exact template; the profile is only used
to enrich missing sections, drive skill ordering and pick an honest header
title. No Python-specific vocabulary is hardcoded here.
"""

import html
import io
import logging
import re

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

def _category_label(cat: str) -> str:
    """Human label for a skills category — title-cased, no tech map."""
    return cat.replace("_", " ").title() or cat


def _header_urls(profile: dict) -> str:
    """Header link labels, only for URLs present in the profile."""
    labels = []
    if profile.get("github"):
        labels.append("GitHub")
    if profile.get("linkedin"):
        labels.append("LinkedIn")
    if profile.get("portfolio"):
        labels.append("Website")
    return " · ".join(labels)


_SENIORITY_WORDS = {
    "senior", "lead", "principal", "staff", "head", "chief", "junior",
    "associate", "intern", "fresher", "mid-level", "midlevel", "mid",
}

_RESUME_SECTION_HEADERS = {
    "professional summary", "summary", "technical skills", "skills",
    "projects", "experience", "work experience", "employment history",
    "professional experience", "education",
}


def _strip_seniority(title: str) -> str:
    words = [w for w in title.split() if w.lower() not in _SENIORITY_WORDS]
    return " ".join(words).strip()


def choose_header_title(job: dict, profile: dict) -> str:
    """Pick a header title the candidate can legitimately claim.

    Never copies the JD title blindly. Prefers the candidate's own profile
    role (seniority stripped), falls back to the JD title normalized the same
    way, and finally to a neutral label. Profession-agnostic by construction.
    """
    role = (profile.get("role") or "").strip()
    if role:
        return _strip_seniority(role) or role
    jd_title = (job.get("title") or "").strip()
    if jd_title:
        return _strip_seniority(jd_title) or "Professional"
    return "Professional"


def parse_resume_sections(text: str) -> dict:
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
    for raw in (text or "").splitlines():
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


def profile_sections(profile: dict) -> dict:
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
        _header_urls(profile),
    ]
    sections["header"] = [h for h in sections["header"] if h]
    for cat, skills in profile.get("skills", {}).items():
        if skills:
            sections["skills"][_category_label(cat)] = list(skills)
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


def enrich_sections(sections: dict, profile: dict) -> dict:
    if not sections["skills"]:
        for cat, skills in profile.get("skills", {}).items():
            if skills:
                sections["skills"][_category_label(cat)] = list(skills)
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
            _header_urls(profile),
        ]
        sections["header"] = [h for h in sections["header"] if h]
    return sections


def reorder_skills(skills_by_cat: dict, matched_skills: list) -> dict:
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


def build_summary(profile: dict, job: dict, matched_skills: list) -> str:
    from app.core.profile_skills import flatten_skills

    role = profile.get("role") or choose_header_title(job, profile) or "Professional"
    years = profile.get("experience_years")
    project = job.get("relevant_project") or {}
    if matched_skills:
        strengths = ", ".join(matched_skills[:6])
    else:
        all_skills = flatten_skills(profile)
        strengths = ", ".join(all_skills[:6]) if all_skills else "industry-standard skills"
    parts = []
    if years:
        parts.append(
            f"{role} with {years}+ years of hands-on experience delivering "
            "high-quality, results-driven work."
        )
    else:
        parts.append(
            f"{role} focused on delivering high-quality, results-driven work "
            "with measurable outcomes."
        )
    if project.get("description"):
        parts.append(
            f"Proven experience delivering {project.get('name', '')} "
            f"({project['description']})."
        )
    parts.append(f"Core strengths include {strengths}.")
    if job.get("title") and job.get("company"):
        parts.append(
            f"Actively targeting the {job['title']} role at {job['company']}."
        )
    return " ".join(parts)


def build_tailored_text(sections: dict, profile: dict, job: dict, matched_skills: list) -> str:
    lines = []
    header = sections.get("header") or []
    header_title = choose_header_title(job, profile)
    if len(header) >= 2:
        header_lines = [header[0], header_title] + header[2:]
    else:
        header_lines = list(header) + [header_title]
    for h in header_lines[:4]:
        lines.append(h)
    lines.append("")
    lines.append("PROFESSIONAL SUMMARY")
    lines.append(build_summary(profile, job, matched_skills))
    lines.append("")
    lines.append("SKILLS")
    for cat, skills in reorder_skills(sections.get("skills", {}), matched_skills).items():
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


def make_urls_clickable(text: str, url_map: dict) -> str:
    label_map = {
        "github": "GitHub",
        "linkedin": "LinkedIn",
        "portfolio": "Portfolio",
        "website": "Website",
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


def parse_project_links(resume_text: str) -> dict:
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


def build_project_url_map(resume_text: str, profile: dict) -> dict:
    """Resolve each project's Live/GitHub URLs by priority:
    1. URL present in the original resume text
    2. Profile project 'link' field
    3. Inferred from the profile GitHub username + project name
    """
    links = parse_project_links(resume_text)
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


def render_project_links(stripped: str, current_project: str, project_url_map: dict) -> str:
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


def resume_to_html(text: str, profile: dict = None, project_url_map: dict = None) -> str:
    lines = text.split("\n")
    html_parts = ['<div class="resume">']
    in_header = True
    header_count = 0
    in_projects = False
    current_project = None
    project_url_map = project_url_map or {}

    url_map = {}
    if profile:
        if profile.get("linkedin"):
            url_map["linkedin"] = profile["linkedin"]
        if profile.get("portfolio"):
            url_map["portfolio"] = profile["portfolio"]
        if profile.get("github"):
            url_map["github"] = profile["github"]

    for line in lines:
        stripped = line.strip()
        if not stripped:
            html_parts.append('<div class="spacer"></div>')
            if header_count >= 2:
                in_header = False
            continue

        if in_header and header_count < 4:
            rendered = make_urls_clickable(stripped, url_map) if header_count >= 2 else stripped
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
            html_parts.append(
                f'<div class="bullet"><span class="bullet-char">\u2022</span>{content}</div>'
            )
            continue

        if in_projects:
            title_match = re.match(r"^(.+?)\s*[—–]\s*", stripped)
            if title_match and "http" not in stripped:
                candidate = title_match.group(1).strip()
                if candidate and not candidate.lower().startswith(("stack", "live", "github")):
                    current_project = candidate

            if re.search(r"https?://", stripped):
                links_html = render_project_links(stripped, current_project, project_url_map)
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

        date_match = re.search(
            r'(\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\s*[–\-]\s*'
            r'(Present|Current|\d{4})\b|\b\d{4}\s*[–\-]\s*(Present|Current|\d{4})\b|'
            r'\b\w+\s+\d{4}\b)',
            stripped,
        )
        if date_match and len(stripped) > len(date_match.group()) + 5:
            parts = stripped.rsplit(date_match.group(), 1)
            html_parts.append(
                f'<table class="two-col"><tr>'
                f'<td class="left">{parts[0].strip()}</td>'
                f'<td class="right">{date_match.group().strip()}</td>'
                f'</tr></table>'
            )
            continue

        _company_suffixes = {
            "Solutions", "Technologies", "Ltd", "Inc", "Tech", "Digital",
            "Labs", "Systems", "Software", "Group", "Corp", "LLC",
        }
        if header_count >= 4:
            location_match = re.search(r'\s{3,}(\S.*)$', stripped)
            if not location_match:
                location_match = re.search(r',\s*([A-Z][a-zA-Z\s]+)$', stripped)
            if not location_match and any(suffix in stripped for suffix in _company_suffixes):
                location_match = re.search(r'[,]\s*(\w+.*)$', stripped)
            if (
                location_match
                and location_match.group(1)
                and not any(c.isdigit() for c in location_match.group(1)[:3])
            ):
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
        "h2.section-title{font-size:9.5pt;font-weight:bold;margin:5px 0 2px 0;padding:0;"
        "border-bottom:1px solid #ccc;}"
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


def generate_pdf(resume_text: str, profile: dict = None, project_url_map: dict = None) -> bytes:
    html = resume_to_html(resume_text, profile, project_url_map)
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


def build_tailored_cv(resume_text: str, profile: dict, job: dict,
                      matched_skills: list) -> tuple[str, dict, bytes]:
    """Produce the tailored CV for a job.

    Returns (tailored_text, project_url_map, pdf_bytes). Uses the original
    resume text when available; otherwise builds sections from the profile.
    """
    if resume_text:
        sections = parse_resume_sections(resume_text)
    else:
        sections = profile_sections(profile)
    sections = enrich_sections(sections, profile)

    tailored_text = build_tailored_text(sections, profile, job, matched_skills)
    project_url_map = build_project_url_map(resume_text, profile)
    pdf_bytes = generate_pdf(tailored_text, profile, project_url_map)
    return tailored_text, project_url_map, pdf_bytes
