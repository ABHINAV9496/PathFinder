import re
from config.profile import PROFILE


def _classify_company(job: dict) -> str:
    company = (job.get("company") or "").lower()
    desc = (job.get("description") or "").lower()
    title = (job.get("title") or "").lower()
    text = f"{company} {desc} {title}"

    ai_signals = ["machine learning", "artificial intelligence", " ai ", " ml ", "deep learning", "nlp", "llm", "genai", "generative ai"]
    if any(s in text for s in ai_signals):
        return "ai"

    fintech_signals = ["fintech", "banking", "finance", "payment", "insurance", "lending", "neobank", "trading"]
    if any(s in text for s in fintech_signals):
        return "fintech"

    startup_signals = ["startup", "series a", "series b", "series c", "seed", "early stage", "fast-paced", "move fast", "bias for action", "scrappy"]
    if any(s in text for s in startup_signals):
        return "startup"

    enterprise_signals = ["enterprise", "fortune", "multinational", "global", "consulting", "services", "fortune 500", "mnc"]
    if any(s in text for s in enterprise_signals):
        return "enterprise"

    tech_signals = ["saas", "platform", "cloud", "api", "microservice", "infrastructure", "devops", "developer tools", "devtools"]
    if any(s in text for s in tech_signals):
        return "tech"

    return "general"


def _best_project(job: dict) -> tuple[dict, dict]:
    desc = (job.get("description") or "").lower()
    matched = [s.lower() for s in (job.get("matched_skills") or [])]

    scored = []
    for p in PROFILE["projects"]:
        p_tech = {t.lower() for t in p["tech"]}
        overlap = len(set(matched) & p_tech)
        desc_bonus = sum(1 for t in p_tech if t in desc)
        scored.append((overlap + desc_bonus, p))
    scored.sort(key=lambda x: x[0], reverse=True)

    primary = scored[0][1] if scored else PROFILE["projects"][0]
    secondary = scored[1][1] if len(scored) > 1 else None
    return primary, secondary


def _skill_match_text(job: dict) -> str:
    matched = job.get("matched_skills") or []
    if not matched:
        return "Python, Django, and React"
    top = matched[:6]
    if len(top) <= 2:
        return " and ".join(top)
    return ", ".join(top[:-1]) + f", and {top[-1]}"


def _pick_relevant_skills(job: dict, category: str) -> str:
    desc = (job.get("description") or "").lower()
    skills = PROFILE.get("skills", {}).get(category, [])
    relevant = [s for s in skills if s.lower() in desc or s.lower() in " ".join(job.get("matched_skills", [])).lower()]
    if not relevant:
        relevant = skills[:3]
    return ", ".join(relevant[:4])


def _company_ref(company: str, style: str = "normal") -> str:
    name = company.strip()
    if not name:
        return "your team"
    if style == "possessive":
        if name.endswith("s"):
            return f"{name}'"
        return f"{name}'s"
    return name


def _has_devops(job: dict) -> bool:
    desc = (job.get("description") or "").lower()
    return any(w in desc for w in ["docker", "aws", "ci/cd", "devops", "kubernetes", "deploy", "terraform", "cloud", "ec2", "gcp"])


def _has_ai(job: dict) -> bool:
    desc = (job.get("description") or "").lower()
    return any(w in desc for w in ["ai", "ml", "llm", "machine learning", "deep learning", "nlp", "genai", "generative", "rag"])


def _has_frontend(job: dict) -> bool:
    desc = (job.get("description") or "").lower()
    return any(w in desc for w in ["react", "frontend", "front-end", "vue", "angular", "typescript", "javascript", "ui", "ux"])


def _devops_line(template: str) -> str:
    lines = {
        "startup": "I also own the deployment side -- Docker, AWS EC2/S3, GitHub Actions CI/CD -- because at a startup, shipping is your job, not someone else's.",
        "enterprise": "I bring production DevOps experience with Docker, AWS EC2/RDS/S3, and GitHub Actions CI/CD -- the same stack I used to deploy and maintain production workloads at scale.",
        "tech": "I also work across the deployment layer -- Docker Compose, GitHub Actions CI/CD, and AWS EC2/RDS/S3/CloudFront -- because building only matters if it ships reliably.",
        "fintech": "I also bring hands-on DevOps experience with Docker, AWS, and GitHub Actions CI/CD -- I understand the deployment rigor that production financial systems require.",
        "ai": "On the infrastructure side, I have deployed Docker-based services on AWS with GitHub Actions CI/CD -- I understand the operational side of running AI workloads in production.",
        "general": "I also handle deployment infrastructure -- Docker, AWS, GitHub Actions CI/CD -- because I like owning the full lifecycle from code to production.",
    }
    return lines.get(template, lines["general"])


def _ai_line(template: str) -> str:
    lines = {
        "startup": "I also have hands-on LLM integration experience through Groq -- prompt engineering, structured output parsing, and fallback logic for when models are unreliable.",
        "enterprise": "I also have practical AI and LLM experience -- prompt engineering, structured outputs, and reliability patterns around model APIs for production use.",
        "tech": "I have worked with LLMs and AI tooling in production -- prompt engineering, structured outputs, and graceful degradation when models fail.",
        "fintech": "I have AI and LLM integration experience -- prompt engineering, structured outputs, and building guardrails around model APIs for production reliability.",
        "ai": "I have extensive LLM experience through Groq -- prompt engineering, structured output parsing, and fallback logic for production systems that depend on model reliability.",
        "general": "I have hands-on LLM experience through Groq -- prompt engineering, structured outputs, and building reliable integrations that handle model failures gracefully.",
    }
    return lines.get(template, lines["general"])


def _jd_need_hook(job: dict, company: str) -> str:
    desc = (job.get("description") or "").lower()
    title = (job.get("title") or "")
    hooks = []
    if any(w in desc for w in ["scalable", "scale", "high traffic", "millions"]):
        hooks.append(f"scalable systems that handle real traffic at {company}")
    if any(w in desc for w in ["api", "rest", "microservice"]):
        hooks.append(f"clean, well-designed APIs at {company}")
    if any(w in desc for w in ["saas", "platform", "product"]):
        hooks.append(f"production SaaS products at {company}")
    if any(w in desc for w in ["fast-paced", "move fast", "ship"]):
        hooks.append(f"moving fast and shipping at {company}")
    if any(w in desc for w in ["security", "auth", "rbac", "compliance"]):
        hooks.append(f"secure, production-grade systems at {company}")
    if any(w in desc for w in ["ai", "ml", "llm", "machine learning"]):
        hooks.append(f"AI-powered products at {company}")
    if hooks:
        return hooks[0]
    return f"the work your team is doing at {company}"


# ─── TEMPLATES ───────────────────────────────────────────────────────────────
# Market-validated format: Problem-Solution structure.
# Opening: Hook with a specific connection to the company's work/challenge.
# Body: Quantified achievements showing you've solved similar problems.
# Close: Confident statement of value, not a plea.

def _tpl_startup(company: str, title: str, project: dict, secondary: dict | None, job: dict) -> str:
    p2 = f" On {secondary['name']}, I {secondary['description'].lower()} -- another project where I owned the full stack end to end." if secondary else ""
    need = _jd_need_hook(job, company)

    return f"""Shipping fast without breaking things is what {company} needs from a {title}, and that's exactly what I do. I recently built {project['name']} -- {project['description'].lower()} -- handling everything from database design through API development to frontend and deployment. The stack ({', '.join(project['tech'][:6])}) maps directly to what you're looking for.

At {_company_ref(company, 'possessive')} stage, you need someone who owns the full loop. With {project['name']}, I built the backend in Django and DRF, the frontend in React and TypeScript, set up PostgreSQL with Redis and Celery for async processing, and deployed the whole thing with Docker and GitHub Actions. No handoffs, no waiting -- just features shipping.{p2}

{_devops_line('startup')}
{_ai_line('startup') if _has_ai(job) else ''}

I'm excited about {need} and I'm ready to hit the ground running. Let's talk."""


def _tpl_enterprise(company: str, title: str, project: dict, secondary: dict | None, job: dict) -> str:
    p2 = f" {secondary['name']} -- {secondary['description'].lower()} -- gave me hands-on experience with role-based access control and admin workflows, patterns I know enterprise environments rely on." if secondary else ""
    need = _jd_need_hook(job, company)

    return f"""Your {title} listing at {company} calls for someone who can build production systems that scale -- I've been doing exactly that. I recently shipped {project['name']} -- {project['description'].lower()} -- a full-stack application built on {', '.join(project['tech'][:6])} that handles authentication, role-based access, and API design from the ground up.

I'm comfortable working across the stack and taking ownership of deliverables from architecture through deployment. I've designed backend APIs with Django and DRF, implemented JWT auth with role-based access control, built the frontend in React, and set up CI/CD pipelines with Docker and GitHub Actions. I understand that enterprise systems need to be reliable, secure, and maintainable -- not just functional.{p2}

{_devops_line('enterprise')}
{_ai_line('enterprise') if _has_ai(job) else ''}

I'm drawn to {company} because of {need}. I'd welcome the opportunity to discuss how my experience aligns with your team's needs."""


def _tpl_tech(company: str, title: str, project: dict, secondary: dict | None, job: dict) -> str:
    p2 = f" I also built {secondary['name']} -- {secondary['description'].lower()} -- which deepened my experience with {', '.join(secondary['tech'][:3])} in production." if secondary else ""
    need = _jd_need_hook(job, company)

    return f"""The {title} role at {company} stands out because it's solving the kind of technical problems I enjoy most. I spent the past year building {project['name']} -- {project['description'].lower()} -- and the requirements in your job description align directly with the work I've been doing.

My core stack is {', '.join(PROFILE['skills']['backend'][:6])}. With {project['name']}, I designed the API layer in Django REST Framework, built background processing with Celery and Redis, and created the frontend in React and TypeScript. I care about API design, data modeling, and making sure systems hold up under real load -- not just that they work, but that they stay working.{p2}

{_devops_line('tech')}
{_ai_line('tech') if _has_ai(job) else ''}

I'm excited about {need} and confident I can contribute from day one. Let me know if there's a good time to connect."""


def _tpl_fintech(company: str, title: str, project: dict, secondary: dict | None, job: dict) -> str:
    p2 = f" {secondary['name']} -- {secondary['description'].lower()} -- gave me experience with {', '.join(secondary['tech'][:4])}, skills that translate directly to building reliable financial systems." if secondary else ""
    need = _jd_need_hook(job, company)

    return f"""Financial systems demand reliability, security, and clean data handling -- that's where my backend experience directly applies. I built {project['name']} -- {project['description'].lower()} -- on {', '.join(project['tech'][:6])}, with Django and DRF handling the backend, JWT authentication with role-based access control for security, and PostgreSQL with proper migrations and indexing for the data layer. Every API endpoint and database query was built with production rigor.{p2}

{_devops_line('fintech')}
{_ai_line('fintech') if _has_ai(job) else ''}

I'm interested in {company} because of {need}. I'd be happy to discuss how my experience with secure, production-grade systems can contribute to your team."""


def _tpl_ai(company: str, title: str, project: dict, secondary: dict | None, job: dict) -> str:
    p2 = f" {secondary['name']} -- {secondary['description'].lower()} -- gave me additional production experience with {', '.join(secondary['tech'][:4])} in a real product environment." if secondary else ""
    need = _jd_need_hook(job, company)

    return f"""The {title} role at {company} caught my attention because it combines production backend systems with AI integration -- exactly what I've been building. Through {project['name']} -- {project['description'].lower()} -- I've learned that the hard part of AI engineering isn't calling the API, it's making the system dependable when the model isn't.

My technical foundation is in {', '.join(PROFILE['skills']['backend'][:5])}, and I've applied that to building systems that integrate LLMs into real products. With {project['name']}, I used Groq for inference, built prompt engineering pipelines, implemented structured output parsing, and designed fallback logic for when model APIs are unreliable. I've shipped this kind of work and I know what it takes to make AI features production-ready.{p2}

{_devops_line('ai')}
{_ai_line('ai') if _has_ai(job) else ''}

I'm excited about {need} and confident I can contribute meaningfully from the start. Let's connect."""


def _tpl_general(company: str, title: str, project: dict, secondary: dict | None, job: dict) -> str:
    p2 = f" I also built {secondary['name']} -- {secondary['description'].lower()} -- using {', '.join(secondary['tech'][:4])}, which broadened my experience across different application types." if secondary else ""
    need = _jd_need_hook(job, company)

    return f"""I'm a full-stack Python developer with production experience, and the {title} role at {company} matches closely with what I've been building. I recently shipped {project['name']} -- {project['description'].lower()} -- where I handled everything from database design and API development to frontend implementation and deployment. The project uses {', '.join(project['tech'][:6])}, and I've taken it from initial concept through to a live production system.

My strongest work is in {', '.join(PROFILE['skills']['backend'][:5])}. I design APIs that are clean and well-documented, build data layers that are reliable, and set up deployments that I can maintain without needing a separate DevOps team. I work the full stack because I like understanding how everything connects.{p2}

{_devops_line('general')}
{_ai_line('general') if _has_ai(job) else ''}

I'm excited about {need} and ready to contribute. Let me know when you'd like to connect."""


# ─── MAP ─────────────────────────────────────────────────────────────────────

_TEMPLATE_MAP = {
    "startup": _tpl_startup,
    "enterprise": _tpl_enterprise,
    "tech": _tpl_tech,
    "fintech": _tpl_fintech,
    "ai": _tpl_ai,
    "general": _tpl_general,
}


def _signature() -> str:
    name = PROFILE.get("name", "")
    phone = PROFILE.get("phone", "")
    email = PROFILE.get("email", "")
    portfolio = PROFILE.get("portfolio", "")
    github = PROFILE.get("github", "")
    linkedin = PROFILE.get("linkedin", "")

    lines = [f"Regards,\n{name}"]
    parts = []
    if phone:
        parts.append(phone)
    if email:
        parts.append(email)
    if parts:
        lines.append(" | ".join(parts))
    links = []
    if portfolio:
        links.append(portfolio)
    if github:
        links.append(f"GitHub: {github}")
    if linkedin:
        links.append(f"LinkedIn: {linkedin}")
    if links:
        lines.append(" | ".join(links))
    return "\n".join(lines)


TEMPLATES = list(_TEMPLATE_MAP.keys())


def generate_cover_letter_template(job: dict) -> tuple[str, str]:
    company = job.get("company", "the company")
    title = job.get("title", "the open position")
    template = _classify_company(job)
    primary, secondary = _best_project(job)

    tpl_fn = _TEMPLATE_MAP.get(template, _TEMPLATE_MAP["general"])
    body = tpl_fn(company, title, primary, secondary, job)

    body = re.sub(r'\n{3,}', '\n\n', body)
    body = body.strip()

    letter = f"{body}\n\n{_signature()}"

    return letter.strip(), template
