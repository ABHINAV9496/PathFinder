def render_header(profile: dict, job: dict = None, company_type: str = "general") -> str:
    name = profile.get("name", "").upper()
    role = (job.get("title", "") if job else "") or profile.get("role", "Developer")
    phone = profile.get("phone", "")
    email = profile.get("email", "")
    linkedin = profile.get("linkedin", "")
    github = profile.get("github", "")
    portfolio = profile.get("portfolio", "")
    location = profile.get("location", "")

    if company_type == "general":
        loc_parts = [p.strip() for p in location.split(",")]
        if len(loc_parts) > 2:
            location = ", ".join(loc_parts[:2])

    def _clean_url(url: str) -> str:
        return url.replace("https://", "").replace("http://", "").rstrip("/")

    def _is_placeholder(url: str) -> bool:
        if not url:
            return True
        lower = url.lower()
        return "yourusername" in lower or "yourportfolio" in lower

    parts = []
    if location:
        parts.append(location)
    if email:
        parts.append(f'<a href="mailto:{email}">{email}</a>')
    if phone:
        parts.append(f'<a href="tel:{phone}">{phone}</a>')
    if linkedin and not _is_placeholder(linkedin):
        parts.append(f'<a href="{linkedin}">LinkedIn</a>')
    elif linkedin:
        parts.append(f'<a href="#">LinkedIn</a>')
    if github and not _is_placeholder(github):
        parts.append(f'<a href="{github}">GitHub</a>')
    elif github:
        parts.append(f'<a href="#">GitHub</a>')
    if portfolio and not _is_placeholder(portfolio):
        parts.append(f'<a href="{portfolio}">Portfolio</a>')
    elif portfolio:
        parts.append(f'<a href="#">Portfolio</a>')

    contact_line = " | ".join(parts)

    return f"""<div class="header">
<h1>{name}</h1>
<div class="subtitle">{role}</div>
<div class="contact">{contact_line}</div>
</div>"""


def render_summary(profile: dict, job: dict, tailor_result) -> str:
    summary = tailor_result.summary_text if tailor_result else ""
    if not summary:
        role = profile.get("role", "Professional")
        exp = profile.get("experience_years", 1)
        summary = f"{role} with {exp} year{'s' if exp != 1 else ''} of professional experience delivering measurable results."

    return f"""<div class="summary">
<h2>Professional Summary</h2>
<p>{summary}</p>
</div>"""


def render_skills(profile: dict, tailor_result) -> str:
    matched = {s.lower() for s in (tailor_result.matched_skills if tailor_result else [])}

    category_html = []
    for cat, skills in profile.get("skills", {}).items():
        if not isinstance(skills, list) or not skills:
            continue
        label = cat.replace("_", " ").replace("-", " ").title()
        ordered = sorted(
            skills,
            key=lambda s: (0 if s.lower() in matched else 1, s.lower()),
        )
        category_html.append(
            f'<div class="skill-category"><strong>{label}:</strong> {", ".join(ordered)}</div>'
        )

    if not category_html:
        return ""

    return '<div class="skills-container">\n<h2>Skills</h2>\n' + "\n".join(category_html) + "\n</div>"


def render_experience(profile: dict, tailor_result) -> str:
    if tailor_result and tailor_result.experience_order:
        entries = tailor_result.experience_order
    else:
        entries = profile.get("experience", [])

    if not entries:
        return ""

    html = '<h2>Experience</h2>\n'
    for entry in entries:
        role = entry.get("role", "")
        company = entry.get("company", "")
        location = entry.get("location", "")
        duration = entry.get("duration", "")
        entry_id = entry.get("id", "")

        title_line = f"{role}"
        if company:
            title_line += f" | {company}"

        html += f'<div class="entry">\n'
        html += f'<div class="entry-header">{title_line}</div>\n'
        detail_parts = []
        if location:
            detail_parts.append(location)
        if duration:
            detail_parts.append(duration)
        if detail_parts:
            html += f'<div class="entry-subheader">{" | ".join(detail_parts)}</div>\n'

        highlights = entry.get("highlights", [])
        if tailor_result and entry_id in tailor_result.highlights_per_entry:
            highlights = tailor_result.highlights_per_entry[entry_id]

        if highlights:
            html += "<ul>\n"
            for h in highlights:
                html += f"<li>{h}</li>\n"
            html += "</ul>\n"

        html += "</div>\n"

    return html


def _split_description(desc: str) -> list[str]:
    if not desc:
        return []
    sentences = [s.strip() for s in desc.replace(". ", ".\n").split("\n") if s.strip()]
    if len(sentences) <= 1:
        parts = []
        raw = desc
        for sep in [". ", " that ", " with ", " featuring "]:
            if sep in raw:
                pieces = raw.split(sep, 1)
                parts.append(pieces[0].strip() + (sep if sep == ". " else ""))
                raw = pieces[1].strip()
                if raw:
                    parts.append(raw)
                break
        if len(parts) > 1:
            sentences = parts
        else:
            sentences = [desc]
    return [s.strip().rstrip(".") for s in sentences if s.strip()]


def render_projects(profile: dict, tailor_result, job: dict = None) -> str:
    projects = profile.get("projects", [])
    if not projects:
        return ""

    ordered = projects
    if tailor_result and tailor_result.ranked_projects:
        ordered = tailor_result.ranked_projects

    jd_lower = (job.get("description", "") if job else "").lower()

    html = '<h2>Projects</h2>\n'
    for p in ordered:
        name = p.get("name", "")
        desc = p.get("description", "")
        tech = p.get("tech", [])
        link = p.get("link", "")

        html += f'<div class="project">\n'
        if link:
            html += f'<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
            html += f'<td><div class="project-name">{name}</div></td>'
            html += f'<td nowrap="nowrap"><div class="project-link"><a href="{link}">Live Demo</a></div></td>'
            html += f'</tr></table>\n'
        else:
            html += f'<div class="project-name">{name}</div>\n'
        if tech:
            html += f'<div class="project-tech">{", ".join(tech)}</div>\n'

        highlights = p.get("highlights", [])

        if not highlights:
            highlights = _split_description(desc)

        if jd_lower and highlights and len(highlights) > 3:
            scored = []
            for h in highlights:
                h_lower = h.lower()
                relevance = sum(1 for word in h_lower.split() if len(word) > 3 and word in jd_lower)
                scored.append((relevance, h))
            scored.sort(key=lambda x: x[0], reverse=True)
            highlights = [h for _, h in scored[:4]]

        if highlights:
            html += "<ul>\n"
            for s in highlights:
                s = s.strip().rstrip(".")
                if s:
                    html += f"<li>{s}</li>\n"
            html += "</ul>\n"

        html += "</div>\n"

    return html


def render_education(profile: dict) -> str:
    education = profile.get("education", "")
    if not education:
        return ""

    import re
    year_match = re.search(r'\b(20\d{2}|19\d{2})\b', education)
    year = year_match.group(1) if year_match else ""

    degree = education
    school = education
    if " - " in education:
        parts = education.split(" - ", 1)
        degree = parts[0].strip()
        school = parts[1].strip()
        if year and year in school:
            school = school.replace(year, "").replace("()", "").replace("  ", " ").strip().rstrip("()")
    elif year:
        degree = education.replace(year, "").replace("()", "").strip()

    school = school.strip().rstrip("()-").strip()

    return f"""<div class="education-entry">
<h2>Education</h2>
<div class="education-degree">{degree}</div>
<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
<td><div class="education-school">{school}</div></td>
{"<td nowrap='nowrap'><div class='education-year'>" + year + "</div></td>" if year else ""}
</tr></table>
</div>"""
