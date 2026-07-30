from app.core.templates import (
    render_header, render_summary, render_skills,
    render_experience, render_projects, render_education
)


def build_cv_html(profile: dict, job: dict, tailor_result) -> str:
    sections = []

    sections.append(render_header(profile, job, getattr(tailor_result, 'company_type', 'general')))
    sections.append(render_summary(profile, job, tailor_result))
    sections.append(render_skills(profile, tailor_result))
    sections.append(render_experience(profile, tailor_result))
    sections.append(render_projects(profile, tailor_result, job))
    sections.append(render_education(profile))

    body = "\n".join(sections)

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
@page {{
    size: A4;
    margin: 1.2cm 1.5cm;
}}
body {{
    font-size: 10pt;
    line-height: 1.3;
    font-family: Arial, Helvetica, sans-serif;
    color: #000;
    margin: 0;
    padding: 0;
}}
.header {{
    text-align: center;
    margin-bottom: 6pt;
}}
.header h1 {{
    font-size: 16pt;
    margin: 0 0 2pt 0;
    text-transform: uppercase;
    letter-spacing: 0.5pt;
    font-weight: bold;
}}
.header .subtitle {{
    font-size: 12pt;
    color: #333;
    margin-bottom: 2pt;
    font-weight: bold;
}}
.header .contact {{
    font-size: 9pt;
    color: #333;
    line-height: 1.4;
    word-spacing: 1pt;
}}
.header .contact a {{
    color: #000;
    text-decoration: underline;
}}
h2 {{
    font-size: 11pt;
    text-transform: uppercase;
    letter-spacing: 0.5pt;
    margin: 6pt 0 2pt 0;
    padding-bottom: 2pt;
    border-bottom: 1px solid #000;
}}
.summary p {{
    font-size: 10pt;
    margin: 2pt 0;
    line-height: 1.3;
}}
.skills-container {{
    font-size: 9pt;
    line-height: 1.4;
}}
.skill-category {{
    margin-bottom: 1pt;
}}
.entry {{
    margin-bottom: 4pt;
}}
.entry-header {{
    font-size: 10pt;
    margin-bottom: 1pt;
    font-weight: bold;
}}
.entry-subheader {{
    font-size: 9pt;
    color: #333;
    margin-bottom: 1pt;
}}
ul {{
    margin: 1pt 0;
    padding-left: 16pt;
}}
li {{
    margin-bottom: 0.5pt;
    font-size: 9pt;
    line-height: 1.25;
}}
.project {{
    margin-bottom: 4pt;
}}
.project-name {{
    font-size: 10pt;
    font-weight: bold;
    margin: 0;
    padding: 0;
}}
.project-link {{
    font-size: 9pt;
    font-weight: normal;
    white-space: nowrap;
    text-align: right;
}}
.project-link a {{
    color: #000;
    text-decoration: underline;
}}
.project-tech {{
    font-size: 9pt;
    color: #555;
    margin: 1pt 0;
}}
.education-entry {{
    margin-bottom: 3pt;
}}
.education-degree {{
    font-size: 10pt;
    font-weight: bold;
}}
.education-school {{
    font-size: 9.5pt;
    color: #333;
}}
.education-year {{
    font-size: 9.5pt;
    color: #555;
    text-align: right;
    white-space: nowrap;
}}
</style>
</head>
<body>
{body}
</body>
</html>"""

    return html
