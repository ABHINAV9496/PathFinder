import re
from config.profile import PROFILE


def _classify_company(job: dict) -> str:
    company = (job.get("company") or "").lower()
    desc = (job.get("description") or "").lower()
    title = (job.get("title") or "").lower()
    text = f"{company} {desc} {title}"

    startup_signals = ["startup", "series a", "series b", "seed", "early stage", "fast-paced", "move fast"]
    if any(s in text for s in startup_signals):
        return "startup"

    enterprise_signals = ["enterprise", "fortune", "multinational", "global", "consulting", "services"]
    if any(s in text for s in enterprise_signals):
        return "enterprise"

    tech_signals = ["saas", "platform", "cloud", "api", "microservice", "infrastructure", "devops"]
    if any(s in text for s in tech_signals):
        return "tech"

    fintech_signals = ["fintech", "banking", "finance", "payment", "insurance", "lending"]
    if any(s in text for s in fintech_signals):
        return "fintech"

    ai_signals = ["machine learning", "artificial intelligence", "ai", "ml", "deep learning", "nlp", "llm"]
    if any(s in text for s in ai_signals):
        return "ai"

    return "general"


def _best_project(job: dict) -> dict:
    desc = (job.get("description") or "").lower()
    matched = [s.lower() for s in (job.get("matched_skills") or [])]

    best = None
    best_score = 0
    for p in PROFILE["projects"]:
        p_tech = {t.lower() for t in p["tech"]}
        overlap = len(set(matched) & p_tech)
        desc_bonus = sum(1 for t in p_tech if t in desc)
        score = overlap + desc_bonus
        if score > best_score:
            best_score = score
            best = p

    return best or PROFILE["projects"][0]


def _skill_match_text(job: dict) -> str:
    matched = job.get("matched_skills") or []
    if not matched:
        return ""
    top = matched[:5]
    if len(top) <= 2:
        return " and ".join(top)
    return ", ".join(top[:-1]) + f", and {top[-1]}"


def _company_line(company: str) -> str:
    name = company.strip()
    if not name:
        return "your team"
    if name.lower().startswith(("a ", "an ", "the ")):
        return name
    lower = name.lower()
    vowels = "aeiou"
    if lower[0] in vowels:
        return f"an {name}"
    return f"a {name}"


def _opening(template: str, company: str, title: str, project: dict) -> str:
    co = _company_line(company)
    role = title or "the open position"

    openings = {
        "direct": (
            f"I'm writing to apply for the {role} at {company}. "
            f"With production experience shipping {project['name']} -- "
            f"{project['description'].lower()} -- I'm ready to contribute from day one."
        ),
        "story": (
            f"Building {project['name']} taught me what it takes to ship production systems "
            f"under real constraints. That same drive to build things that actually work is "
            f"what drew me to the {role} opening at {company}."
        ),
        "technical": (
            f"The {role} at {company} caught my attention because it sits at the intersection "
            f"of the stack I work with daily. I've spent the past year building "
            f"{project['name']} end-to-end -- {project['description'].lower()} -- "
            f"and the technical challenges in your JD align directly with that work."
        ),
        "confident": (
            f"I'd be a strong fit for the {role} at {company}. "
            f"I've shipped {project['name']} -- {project['description'].lower()} -- "
            f"and I'm looking for {co} where I can take on similar ownership."
        ),
        "warm": (
            f"I've been following {company}'s work and the {role} opening "
            f"feels like a natural fit. I recently built {project['name']} -- "
            f"{project['description'].lower()} -- "
            f"and the overlap with what you're building is hard to ignore."
        ),
        "bold": (
            f"The {role} at {company} is the kind of problem I wake up wanting to solve. "
            f"I built {project['name']} from scratch -- {project['description'].lower()} -- "
            f"and I'm looking for {co} where that same intensity matters."
        ),
    }
    return openings.get(template, openings["direct"])


def _body_skills(template: str, skills_text: str, project: dict) -> str:
    if template == "story":
        return (
            f"Working across {skills_text}, I've learned to write code that holds up "
            f"under production load. {project['name']} runs on "
            f"{', '.join(project['tech'][:5])}, handling real users and real data. "
            f"That experience shaped how I approach every system I build."
        )
    if template == "technical":
        return (
            f"On the technical side, my day-to-day stack covers {skills_text}. "
            f"With {project['name']}, I designed the backend using "
            f"{', '.join(project['tech'][:4])}, "
            f"built the frontend in React and TypeScript, and deployed the whole thing "
            f"on AWS with Docker and GitHub Actions. I'm comfortable owning a system "
            f"from the database layer to the deploy pipeline."
        )
    if template == "confident":
        return (
            f"My core stack is {skills_text}. "
            f"I've built and deployed {project['name']} -- "
            f"{', '.join(project['tech'][:5])} -- "
            f"and I work across the full stack without needing a handoff between frontend and backend."
        )
    if template == "warm":
        return (
            f"Most of my hands-on work is in {skills_text}. "
            f"With {project['name']}, I shipped "
            f"{', '.join(project['tech'][:4])} and handled everything "
            f"from schema design to deployment. I like being close to the whole process."
        )
    if template == "bold":
        return (
            f"I work primarily with {skills_text}. "
            f"{project['name']} is a production system I built from zero to deployed -- "
            f"{', '.join(project['tech'][:5])} -- "
            f"and I'm looking for work that demands the same kind of full ownership."
        )
    return (
        f"Across my work with {skills_text}, I've focused on writing "
        f"clean, maintainable code that ships. {project['name']} uses "
        f"{', '.join(project['tech'][:4])}, "
        f"and I've taken it from initial design through to a live production system."
    )


def _body_devops(template: str) -> str:
    parts = []
    if template == "technical":
        parts.append(
            "I also handle deployment and infrastructure. "
            "I've worked with Docker Compose, GitHub Actions for CI/CD, "
            "and AWS EC2, RDS, and S3 for hosting. "
            "I'm not precious about boundaries -- if it needs to ship, I'll figure it out."
        )
    elif template == "confident":
        parts.append(
            "I'm comfortable with the DevOps side too -- Docker, AWS, "
            "GitHub Actions CI/CD -- I've set up pipelines and deployed "
            "production workloads without needing a separate infra team."
        )
    elif template == "bold":
        parts.append(
            "On the infra side, I've deployed on AWS with Docker and CI/CD pipelines "
            "through GitHub Actions. I don't wait for someone else to handle deployment."
        )
    else:
        parts.append(
            "I've also picked up the DevOps side along the way -- "
            "Docker Compose for local dev, AWS for hosting, "
            "and GitHub Actions for CI/CD. "
            "I like owning the full lifecycle from code to production."
        )
    return " ".join(parts)


def _body_ai(template: str) -> str:
    if template == "bold":
        return (
            "I've worked with LLMs and AI tooling through Groq and prompt engineering, "
            "building systems that integrate language models into real products. "
            "I know this space is moving fast and I'm keeping up."
        )
    if template == "technical":
        return (
            "I also have hands-on experience with AI and LLM integration -- "
            "prompt engineering, structured outputs, and building reliable "
            "degradation logic around model APIs. "
            "It's a space I've been actively working in."
        )
    return (
        "I've also worked with LLMs and AI tooling in production, "
        "building integrations that handle prompt engineering "
        "and structured outputs reliably."
    )


def _closing(template: str, company: str, project: dict) -> str:
    co = _company_line(company)
    closings = {
        "direct": (
            f"I'd welcome the chance to discuss how I can contribute at {company}. "
            f"I'm available for a call or interview at your convenience."
        ),
        "story": (
            f"I'd enjoy talking through how I can add value at {company}. "
            f"The problems you're solving are the kind I want to be part of."
        ),
        "technical": (
            f"I'd be happy to walk through my approach to any of the technical "
            f"challenges you're working on. Let me know if there's a good time to connect."
        ),
        "confident": (
            f"I'm confident I can contribute meaningfully at {company}. "
            f"I'd love to discuss the role further when you have time."
        ),
        "warm": (
            f"I'd love to learn more about what you're building at {company} "
            f"and how I can help. Happy to connect whenever works."
        ),
        "bold": (
            f"If you're looking for someone who takes ownership and ships, "
            f"I'd like to be that person at {company}. Let's talk."
        ),
    }
    return closings.get(template, closings["direct"])


def _signature() -> str:
    name = PROFILE.get("name", "")
    phone = PROFILE.get("phone", "")
    email = PROFILE.get("email", "")
    portfolio = PROFILE.get("portfolio", "")
    github = PROFILE.get("github", "")
    linkedin = PROFILE.get("linkedin", "")

    lines = [name]
    if phone:
        lines.append(phone)
    if email:
        lines.append(email)
    if portfolio:
        lines.append(portfolio)
    if github:
        lines.append(f"GitHub: {github}")
    if linkedin:
        lines.append(f"LinkedIn: {linkedin}")
    return "\n".join(lines)


TEMPLATES = ["direct", "story", "technical", "confident", "warm", "bold"]


def generate_cover_letter_template(job: dict) -> tuple[str, str]:
    """Generate a cover letter from templates. Returns (cover_letter_text, template_name)."""
    company = job.get("company", "")
    title = job.get("title", "")
    template = _classify_company(job)
    project = _best_project(job)
    skills_text = _skill_match_text(job)

    opening = _opening(template, company, title, project)
    body_skills = _body_skills(template, skills_text, project)

    desc = (job.get("description") or "").lower()
    body_parts = [body_skills]

    has_devops = any(w in desc for w in ["docker", "aws", "ci/cd", "devops", "kubernetes", "deploy"])
    has_ai = any(w in desc for w in ["ai", "ml", "llm", "machine learning", "deep learning", "nlp"])

    if has_devops:
        body_parts.append(_body_devops(template))
    if has_ai:
        body_parts.append(_body_ai(template))

    closing = _closing(template, company, project)
    sig = _signature()

    body = " ".join(body_parts)

    letter = f"""{opening}

{body}

{closing}

{sig}"""

    return letter.strip(), template
