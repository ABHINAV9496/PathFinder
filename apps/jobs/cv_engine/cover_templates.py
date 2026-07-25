import re
import random
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

    enterprise_signals = ["enterprise", "fortune", "multinational", "global", "consulting", "services", " Fortune 500", "mnc"]
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
        "startup": "I also handle the DevOps side -- Docker, AWS, GitHub Actions CI/CD -- because at this stage you need people who can own the full loop.",
        "enterprise": "On the infrastructure side, I have hands-on experience with Docker, AWS EC2/RDS/S3, and GitHub Actions CI/CD pipelines, which I've used to deploy and maintain production workloads.",
        "tech": "I also work across deployment infrastructure -- Docker Compose, GitHub Actions for CI/CD, and AWS EC2, RDS, S3, and CloudFront for hosting -- because shipping is part of building.",
        "fintech": "I also bring hands-on DevOps experience with Docker, AWS, and GitHub Actions CI/CD -- I understand the deployment rigor that production systems require.",
        "ai": "On the infrastructure side, I have worked with Docker, AWS, and GitHub Actions for CI/CD -- I've deployed ML-adjacent services and understand the operational side of running models in production.",
        "general": "I've also picked up the DevOps side -- Docker, AWS, GitHub Actions CI/CD -- because I like owning the full lifecycle from code to production.",
    }
    return lines.get(template, lines["general"])


def _ai_line(template: str) -> str:
    lines = {
        "startup": "I have hands-on experience with LLM integration through Groq and prompt engineering -- building systems that use language models as a core part of the product, not a bolt-on.",
        "enterprise": "I also have practical experience with AI and LLM tooling -- prompt engineering, structured outputs, and reliability patterns around model APIs.",
        "tech": "I have worked with LLMs and AI tooling in production -- prompt engineering, structured outputs, and graceful degradation when models are unreliable.",
        "fintech": "I have experience with AI and LLM integration -- prompt engineering, structured outputs, and building guardrails around model APIs for production use.",
        "ai": "I have worked extensively with LLMs through Groq, building systems that integrate language models into production workflows with proper prompt engineering, structured output parsing, and fallback logic.",
        "general": "I have hands-on LLM experience through Groq -- prompt engineering, structured outputs, and building reliable integrations that handle model failures gracefully.",
    }
    return lines.get(template, lines["general"])


# ─── TEMPLATES ───────────────────────────────────────────────────────────────
# Each template is a function that returns the full cover letter body.
# They are designed to feel like real letters from strong candidates,
# not generic fill-in-the-blank templates.

def _tpl_startup(company: str, title: str, project: dict, secondary: dict | None, job: dict) -> str:
    p2 = f" I also built {secondary['name']} -- {secondary['description'].lower()} -- which taught me how to ship fast without cutting corners on the backend." if secondary else ""

    return f"""I saw the {title} opening at {company} and it lines up directly with what I've been building. I recently shipped {project['name']} -- {project['description'].lower()} -- and the stack ({', '.join(project['tech'][:6])}) maps closely to what you're looking for.

At {_company_ref(company, 'possessive')} stage, you need someone who can take a feature from idea to production without waiting for a DevOps team or a frontend specialist. That's how I work. With {project['name']}, I owned the full stack -- backend in Django and DRF, frontend in React and TypeScript, PostgreSQL for data, Redis and Celery for async tasks, and Docker plus GitHub Actions for deployment. I've done the schema design, the API contracts, the background jobs, and the CI pipeline.{p2}

{_devops_line('startup')}

{_ai_line('startup') if _has_ai(job) else ''}

I'm looking for a place where speed and ownership matter more than process overhead, and that's what I see at {company}. I'd like to discuss how I can start contributing quickly."""


def _tpl_enterprise(company: str, title: str, project: dict, secondary: dict | None, job: dict) -> str:
    p2 = f" Additionally, {secondary['name']} -- {secondary['description'].lower()} -- gave me experience building systems with role-based access control and admin workflows, which I understand are common requirements in enterprise environments." if secondary else ""

    return f"""I'm writing to express my interest in the {title} position at {company}. My background in full-stack Python development, combined with hands-on experience shipping production systems, makes me a strong candidate for this role.

In my current work, I've built and deployed {project['name']} -- {project['description'].lower()} -- using {', '.join(project['tech'][:6])}. This involved designing the backend architecture, implementing RESTful APIs with proper authentication and authorization, building the frontend interface, and setting up the deployment pipeline. I'm comfortable working across the stack and taking ownership of deliverables from design through to production.{p2}

{_devops_line('enterprise')}

{_ai_line('enterprise') if _has_ai(job) else ''}

I'm drawn to {company} because of the scale and complexity of the problems you solve. I'd welcome the opportunity to discuss how my experience aligns with your team's needs."""


def _tpl_tech(company: str, title: str, project: dict, secondary: dict | None, job: dict) -> str:
    p2 = f" On a separate project, {secondary['name']} ({secondary['description'].lower()}) gave me experience with {', '.join(secondary['tech'][:3])}, which further strengthened my understanding of building reliable backend systems." if secondary else ""

    return f"""The {title} role at {company} stands out to me because it sits at the intersection of the technical problems I enjoy most. I've spent the past year building {project['name']} -- {project['description'].lower()} -- and the technical requirements in your job description align directly with the work I've been doing.

The core of my experience is in {', '.join(PROFILE['skills']['backend'][:6])}. With {project['name']}, I designed the API layer in Django REST Framework, set up background processing with Celery and Redis, and built the frontend in React and TypeScript. I care about API design, data modeling, and making sure the system holds up under real load -- not just that it works, but that it stays working.{p2}

{_devops_line('tech')}

{_ai_line('tech') if _has_ai(job) else ''}

I'd enjoy walking through my approach to any of the technical challenges your team is working on. Let me know if there's a good time to connect."""


def _tpl_fintech(company: str, title: str, project: dict, secondary: dict | None, job: dict) -> str:
    p2 = f" I've also built {secondary['name']} -- {secondary['description'].lower()} -- which gave me experience with {', '.join(secondary['tech'][:4])}, skills that translate well to building reliable financial systems." if secondary else ""

    return f"""I'm applying for the {title} position at {company}. Financial systems demand reliability, clean data handling, and security -- areas where my backend development experience directly applies.

I've shipped {project['name']} -- {project['description'].lower()} -- built on {', '.join(project['tech'][:6])}. I designed the backend with Django and DRF, implemented JWT authentication with role-based access control, and set up the data layer in PostgreSQL with proper migrations and indexing. I understand that in fintech, every API endpoint and database query needs to be intentional.{p2}

{_devops_line('fintech')}

{_ai_line('fintech') if _has_ai(job) else ''}

I'm interested in {company} because of the technical challenges that come with building financial products. I'd be happy to discuss how my experience with secure, production-grade systems can contribute to your team."""


def _tpl_ai(company: str, title: str, project: dict, secondary: dict | None, job: dict) -> str:
    p2 = f" I've also worked on {secondary['name']} -- {secondary['description'].lower()} -- which gave me additional experience with {', '.join(secondary['tech'][:4])} in a production environment." if secondary else ""

    return f"""The {title} opening at {company} caught my attention because it combines two things I work with daily: production backend systems and AI integration. I've been building exactly this kind of hybrid work through {project['name']} -- {project['description'].lower()}.

My technical foundation is in {', '.join(PROFILE['skills']['backend'][:5])}, and I've applied that to building systems that integrate LLMs into real products. With {project['name']}, I used Groq for inference, built prompt engineering pipelines, implemented structured output parsing, and designed fallback logic for when model APIs are unreliable. I've learned that the hard part of AI engineering isn't calling the API -- it's making the system dependable when the model isn't.{p2}

{_devops_line('ai')}

{_ai_line('ai') if _has_ai(job) else ''}

I'd like to learn more about how {company} is approaching the AI engineering challenges you're working on. I'm confident I can contribute meaningfully from the start."""


def _tpl_general(company: str, title: str, project: dict, secondary: dict | None, job: dict) -> str:
    p2 = f" I also built {secondary['name']} -- {secondary['description'].lower()} -- using {', '.join(secondary['tech'][:4])}, which broadened my experience across different types of applications." if secondary else ""

    return f"""I'm interested in the {title} position at {company}. I'm a full-stack Python developer with production experience, and the requirements for this role match closely with what I've been building.

My strongest work is in {', '.join(PROFILE['skills']['backend'][:5])}. I recently shipped {project['name']} -- {project['description'].lower()} -- where I handled everything from database design and API development to frontend implementation and deployment. The project uses {', '.join(project['tech'][:6])}, and I've taken it from initial concept through to a live production system.{p2}

{_devops_line('general')}

{_ai_line('general') if _has_ai(job) else ''}

I'd welcome the chance to discuss how I can contribute at {company}. I'm available for a conversation at your convenience."""


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
