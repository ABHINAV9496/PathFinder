import html as html_mod


def _esc(text: str) -> str:
    return html_mod.escape(str(text))


def _skills_html(skills: list[str], color: str) -> str:
    return " ".join(
        f'<span class="skill-tag" style="background:{color}15;color:{color};border:1px solid {color}30;">{_esc(s)}</span>'
        for s in skills
    )


def _project_html(proj: dict, accent: str) -> str:
    techs = ", ".join(proj.get("tech", []))
    return f"""
    <div class="project">
      <div class="project-name">{_esc(proj['name'])}</div>
      <div class="project-desc">{_esc(proj.get('description', ''))}</div>
      <div class="project-tech">{_esc(techs)}</div>
    </div>"""


def modern(data: dict) -> str:
    accent = "#2563EB"
    skills_html = ""
    for cat, items in data.get("skill_groups", {}).items():
        skills_html += f'<div class="skill-group"><span class="skill-cat">{_esc(cat)}</span> {_skills_html(items, accent)}</div>'

    projects_html = "".join(_project_html(p, accent) for p in data.get("projects", []))
    links = []
    if data.get("github"):
        links.append(f'<a href="{_esc(data["github"])}">{_esc(data["github"].replace("https://", ""))}</a>')
    if data.get("linkedin"):
        links.append(f'<a href="{_esc(data["linkedin"])}">{_esc(data["linkedin"].replace("https://", ""))}</a>')
    if data.get("portfolio"):
        links.append(f'<a href="{_esc(data["portfolio"])}">{_esc(data["portfolio"].replace("https://", ""))}</a>')
    links_html = " &middot; ".join(links)

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<style>
@page {{ size: A4; margin: 18mm 16mm 18mm 16mm; }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: Helvetica, Arial, sans-serif; font-size: 9.5pt; color: #1a1a1a; line-height: 1.45; }}
.header {{ border-bottom: 3px solid {accent}; padding-bottom: 12px; margin-bottom: 14px; }}
.name {{ font-size: 22pt; font-weight: 700; color: {accent}; letter-spacing: -0.5px; }}
.role {{ font-size: 11pt; color: #555; margin-top: 2px; }}
.contact {{ font-size: 8.5pt; color: #666; margin-top: 6px; }}
.contact a {{ color: {accent}; text-decoration: none; }}
.section {{ margin-bottom: 12px; }}
.section-title {{ font-size: 10.5pt; font-weight: 700; color: {accent}; text-transform: uppercase; letter-spacing: 1px; border-bottom: 1.5px solid {accent}30; padding-bottom: 3px; margin-bottom: 8px; }}
.summary {{ font-size: 9.5pt; color: #333; line-height: 1.5; }}
.skill-group {{ margin-bottom: 5px; }}
.skill-cat {{ font-weight: 600; font-size: 8.5pt; color: #444; margin-right: 6px; }}
.skill-tag {{ display: inline-block; padding: 2px 7px; border-radius: 3px; font-size: 8pt; margin: 1px 2px; }}
.project {{ margin-bottom: 8px; }}
.project-name {{ font-weight: 700; font-size: 9.5pt; }}
.project-desc {{ font-size: 8.5pt; color: #555; margin-top: 1px; }}
.project-tech {{ font-size: 8pt; color: {accent}; margin-top: 2px; }}
.two-col {{ display: flex; gap: 20px; }}
.two-col > div {{ flex: 1; }}
.links {{ font-size: 8.5pt; color: #666; }}
.links a {{ color: {accent}; text-decoration: none; }}
.edu {{ font-size: 9pt; color: #333; }}
.lang {{ font-size: 9pt; color: #555; }}
</style></head><body>
<div class="header">
  <div class="name">{_esc(data['name'])}</div>
  <div class="role">{_esc(data['role'])}</div>
  <div class="contact">{_esc(data['email'])} &middot; {_esc(data['phone'])} &middot; {_esc(data['location'])}</div>
  <div class="links" style="margin-top:4px;">{links_html}</div>
</div>
<div class="section">
  <div class="section-title">Summary</div>
  <div class="summary">{_esc(data['summary'])}</div>
</div>
<div class="section">
  <div class="section-title">Skills</div>
  {skills_html}
</div>
<div class="section">
  <div class="section-title">Projects</div>
  {projects_html}
</div>
<div class="two-col">
  <div class="section">
    <div class="section-title">Education</div>
    <div class="edu">{_esc(data.get('education', ''))}</div>
  </div>
  <div class="section">
    <div class="section-title">Languages</div>
    <div class="lang">{_esc(', '.join(data.get('languages', [])))}</div>
  </div>
</div>
</body></html>"""


def professional(data: dict) -> str:
    accent = "#1B2A4A"
    secondary = "#4A6FA5"
    skills_html = ""
    for cat, items in data.get("skill_groups", {}).items():
        skills_html += f'<div class="skill-row"><span class="skill-cat">{_esc(cat)}</span><span class="skill-list">{_esc(", ".join(items))}</span></div>'

    projects_html = "".join(_project_html(p, secondary) for p in data.get("projects", []))
    links = []
    if data.get("github"):
        links.append(f'{_esc(data["github"].replace("https://", ""))}')
    if data.get("linkedin"):
        links.append(f'{_esc(data["linkedin"].replace("https://", ""))}')
    if data.get("portfolio"):
        links.append(f'{_esc(data["portfolio"].replace("https://", ""))}')
    links_html = " | ".join(links)

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<style>
@page {{ size: A4; margin: 20mm 18mm 20mm 18mm; }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: Georgia, 'Times New Roman', serif; font-size: 9.5pt; color: #222; line-height: 1.5; }}
.header {{ text-align: center; border-bottom: 2px solid {accent}; padding-bottom: 10px; margin-bottom: 14px; }}
.name {{ font-size: 20pt; font-weight: 700; color: {accent}; }}
.role {{ font-size: 10pt; color: #666; margin-top: 3px; letter-spacing: 2px; text-transform: uppercase; }}
.contact {{ font-size: 8.5pt; color: #555; margin-top: 6px; }}
.section {{ margin-bottom: 12px; }}
.section-title {{ font-size: 10pt; font-weight: 700; color: {accent}; text-transform: uppercase; letter-spacing: 1.5px; border-bottom: 1px solid #ccc; padding-bottom: 3px; margin-bottom: 8px; }}
.summary {{ font-size: 9.5pt; color: #333; font-style: italic; }}
.skill-row {{ margin-bottom: 4px; }}
.skill-cat {{ font-weight: 700; font-size: 9pt; color: {accent}; display: inline; }}
.skill-list {{ font-size: 9pt; color: #444; }}
.project {{ margin-bottom: 8px; }}
.project-name {{ font-weight: 700; font-size: 9.5pt; color: {accent}; }}
.project-desc {{ font-size: 8.5pt; color: #555; margin-top: 1px; }}
.project-tech {{ font-size: 8pt; color: {secondary}; margin-top: 2px; font-style: italic; }}
.links {{ font-size: 8pt; color: #888; text-align: center; margin-top: 4px; }}
.edu {{ font-size: 9pt; color: #333; }}
.lang {{ font-size: 9pt; color: #555; }}
.two-col {{ display: flex; gap: 20px; }}
.two-col > div {{ flex: 1; }}
</style></head><body>
<div class="header">
  <div class="name">{_esc(data['name'])}</div>
  <div class="role">{_esc(data['role'])}</div>
  <div class="contact">{_esc(data['email'])} | {_esc(data['phone'])} | {_esc(data['location'])}</div>
  <div class="links">{links_html}</div>
</div>
<div class="section">
  <div class="section-title">Professional Summary</div>
  <div class="summary">{_esc(data['summary'])}</div>
</div>
<div class="section">
  <div class="section-title">Technical Skills</div>
  {skills_html}
</div>
<div class="section">
  <div class="section-title">Key Projects</div>
  {projects_html}
</div>
<div class="two-col">
  <div class="section">
    <div class="section-title">Education</div>
    <div class="edu">{_esc(data.get('education', ''))}</div>
  </div>
  <div class="section">
    <div class="section-title">Languages</div>
    <div class="lang">{_esc(', '.join(data.get('languages', [])))}</div>
  </div>
</div>
</body></html>"""


def technical(data: dict) -> str:
    accent = "#059669"
    skills_html = ""
    for cat, items in data.get("skill_groups", {}).items():
        tags = " ".join(
            f'<span class="tag">{_esc(s)}</span>' for s in items
        )
        skills_html += f'<div class="skill-row"><span class="cat">{_esc(cat)}:</span> {tags}</div>'

    projects_html = ""
    for p in data.get("projects", []):
        techs = " ".join(f'<span class="tag-sm">{_esc(t)}</span>' for t in p.get("tech", []))
        projects_html += f"""
        <div class="proj">
          <div class="proj-head"><span class="proj-name">{_esc(p['name'])}</span></div>
          <div class="proj-desc">{_esc(p.get('description', ''))}</div>
          <div class="proj-tech">{techs}</div>
        </div>"""

    links = []
    if data.get("github"):
        links.append(f'<span class="link-item">&#9741; {_esc(data["github"].replace("https://", ""))}</span>')
    if data.get("linkedin"):
        links.append(f'<span class="link-item">&#9742; {_esc(data["linkedin"].replace("https://", ""))}</span>')
    if data.get("portfolio"):
        links.append(f'<span class="link-item">&#9744; {_esc(data["portfolio"].replace("https://", ""))}</span>')
    links_html = " &nbsp;|&nbsp; ".join(links)

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<style>
@page {{ size: A4; margin: 15mm 14mm 15mm 14mm; }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Courier New', Consolas, monospace; font-size: 9pt; color: #e2e8f0; background: #0f172a; line-height: 1.5; }}
.header {{ border-bottom: 1px solid #334155; padding-bottom: 10px; margin-bottom: 12px; }}
.name {{ font-size: 18pt; font-weight: 700; color: {accent}; }}
.role {{ font-size: 10pt; color: #94a3b8; margin-top: 2px; }}
.contact {{ font-size: 8pt; color: #64748b; margin-top: 5px; }}
.links {{ margin-top: 4px; font-size: 7.5pt; }}
.link-item {{ color: #64748b; }}
.section {{ margin-bottom: 10px; }}
.section-title {{ font-size: 9pt; font-weight: 700; color: {accent}; text-transform: uppercase; letter-spacing: 2px; border-bottom: 1px solid #1e293b; padding-bottom: 3px; margin-bottom: 6px; }}
.summary {{ font-size: 9pt; color: #cbd5e1; }}
.skill-row {{ margin-bottom: 4px; font-size: 8.5pt; }}
.cat {{ color: {accent}; font-weight: 700; }}
.tag {{ display: inline-block; background: #1e293b; color: #e2e8f0; padding: 1px 6px; border-radius: 2px; font-size: 7.5pt; margin: 1px 2px; border: 1px solid #334155; }}
.proj {{ margin-bottom: 8px; }}
.proj-name {{ font-weight: 700; font-size: 9pt; color: #f1f5f9; }}
.proj-desc {{ font-size: 8pt; color: #94a3b8; margin-top: 1px; }}
.proj-tech {{ margin-top: 3px; }}
.tag-sm {{ display: inline-block; background: #064e3b; color: #6ee7b7; padding: 0px 5px; border-radius: 2px; font-size: 7pt; margin: 1px 1px; }}
.two-col {{ display: flex; gap: 16px; }}
.two-col > div {{ flex: 1; }}
.edu {{ font-size: 8.5pt; color: #cbd5e1; }}
.lang {{ font-size: 8.5pt; color: #94a3b8; }}
</style></head><body>
<div class="header">
  <div class="name">{_esc(data['name'])}</div>
  <div class="role">{_esc(data['role'])}</div>
  <div class="contact">{_esc(data['email'])} | {_esc(data['phone'])} | {_esc(data['location'])}</div>
  <div class="links">{links_html}</div>
</div>
<div class="section">
  <div class="section-title">// About</div>
  <div class="summary">{_esc(data['summary'])}</div>
</div>
<div class="section">
  <div class="section-title">// Stack</div>
  {skills_html}
</div>
<div class="section">
  <div class="section-title">// Projects</div>
  {projects_html}
</div>
<div class="two-col">
  <div class="section">
    <div class="section-title">// Education</div>
    <div class="edu">{_esc(data.get('education', ''))}</div>
  </div>
  <div class="section">
    <div class="section-title">// Languages</div>
    <div class="lang">{_esc(', '.join(data.get('languages', [])))}</div>
  </div>
</div>
</body></html>"""


def creative(data: dict) -> str:
    accent = "#9333EA"
    warm = "#F59E0B"
    skills_html = ""
    for cat, items in data.get("skill_groups", {}).items():
        tags = " ".join(
            f'<span class="ctag">{_esc(s)}</span>' for s in items
        )
        skills_html += f'<div class="cskill-row"><span class="ccat">{_esc(cat)}</span><div class="ctags">{tags}</div></div>'

    projects_html = ""
    for i, p in enumerate(data.get("projects", [])):
        bg = "#FDF4FF" if i % 2 == 0 else "#FFFBEB"
        border = f"{accent}40" if i % 2 == 0 else f"{warm}40"
        techs = ", ".join(p.get("tech", []))
        projects_html += f"""
        <div class="cproj" style="background:{bg};border-left:3px solid {border};">
          <div class="cproj-name">{_esc(p['name'])}</div>
          <div class="cproj-desc">{_esc(p.get('description', ''))}</div>
          <div class="cproj-tech">{_esc(techs)}</div>
        </div>"""

    links = []
    if data.get("github"):
        links.append(f'{_esc(data["github"].replace("https://", ""))}')
    if data.get("linkedin"):
        links.append(f'{_esc(data["linkedin"].replace("https://", ""))}')
    if data.get("portfolio"):
        links.append(f'{_esc(data["portfolio"].replace("https://", ""))}')
    links_html = " &nbsp;/&nbsp; ".join(links)

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<style>
@page {{ size: A4; margin: 16mm 16mm 16mm 16mm; }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: Helvetica, Arial, sans-serif; font-size: 9.5pt; color: #1f2937; line-height: 1.5; }}
.header {{ background: linear-gradient(135deg, {accent}, #7C3AED); color: white; padding: 16px 20px; border-radius: 6px; margin-bottom: 14px; }}
.name {{ font-size: 20pt; font-weight: 700; }}
.role {{ font-size: 10pt; opacity: 0.9; margin-top: 2px; }}
.contact {{ font-size: 8pt; opacity: 0.8; margin-top: 6px; }}
.links {{ font-size: 7.5pt; opacity: 0.7; margin-top: 4px; }}
.section {{ margin-bottom: 12px; }}
.section-title {{ font-size: 10pt; font-weight: 700; color: {accent}; margin-bottom: 6px; display: flex; align-items: center; gap: 6px; }}
.section-title::before {{ content: ""; display: inline-block; width: 4px; height: 14px; background: {accent}; border-radius: 2px; }}
.summary {{ font-size: 9.5pt; color: #374151; }}
.cskill-row {{ margin-bottom: 4px; }}
.ccat {{ font-weight: 700; font-size: 8pt; color: {accent}; text-transform: uppercase; letter-spacing: 0.5px; margin-right: 6px; }}
.ctags {{ display: inline; }}
.ctag {{ display: inline-block; background: {accent}10; color: {accent}; padding: 1px 7px; border-radius: 10px; font-size: 7.5pt; margin: 1px 2px; border: 1px solid {accent}25; }}
.cproj {{ padding: 8px 12px; border-radius: 4px; margin-bottom: 6px; }}
.cproj-name {{ font-weight: 700; font-size: 9.5pt; color: {accent}; }}
.cproj-desc {{ font-size: 8.5pt; color: #555; margin-top: 1px; }}
.cproj-tech {{ font-size: 7.5pt; color: #888; margin-top: 3px; font-style: italic; }}
.two-col {{ display: flex; gap: 20px; }}
.two-col > div {{ flex: 1; }}
.edu {{ font-size: 9pt; color: #333; }}
.lang {{ font-size: 9pt; color: #555; }}
</style></head><body>
<div class="header">
  <div class="name">{_esc(data['name'])}</div>
  <div class="role">{_esc(data['role'])}</div>
  <div class="contact">{_esc(data['email'])} &middot; {_esc(data['phone'])} &middot; {_esc(data['location'])}</div>
  <div class="links">{links_html}</div>
</div>
<div class="section">
  <div class="section-title">About Me</div>
  <div class="summary">{_esc(data['summary'])}</div>
</div>
<div class="section">
  <div class="section-title">Skills</div>
  {skills_html}
</div>
<div class="section">
  <div class="section-title">Featured Work</div>
  {projects_html}
</div>
<div class="two-col">
  <div class="section">
    <div class="section-title">Education</div>
    <div class="edu">{_esc(data.get('education', ''))}</div>
  </div>
  <div class="section">
    <div class="section-title">Languages</div>
    <div class="lang">{_esc(', '.join(data.get('languages', [])))}</div>
  </div>
</div>
</body></html>"""


TEMPLATES = {
    "modern": modern,
    "professional": professional,
    "technical": technical,
    "creative": creative,
}
