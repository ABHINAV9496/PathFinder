import re
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path

from config.settings import EMAIL_USER, EMAIL_PASS, EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, RESUME_PATH
from apps.jobs.profile_manager import load_profile

logger = logging.getLogger(__name__)

_PROFILE_CACHE = None

def _get_profile():
    global _PROFILE_CACHE
    if _PROFILE_CACHE is None:
        _PROFILE_CACHE = load_profile()
    return _PROFILE_CACHE

BACKEND_SKILLS = {
    "python", "django", "drf", "django rest framework", "rest api",
    "postgresql", "postgres", "celery", "redis", "fastapi", "flask",
    "sql", "orm", "sqlalchemy", "jwt", "oauth", "authentication",
}
FRONTEND_SKILLS = {
    "react", "react.js", "vue", "vue.js", "angular", "javascript",
    "typescript", "html", "css", "tailwind", "bootstrap",
}
DEVOPS_SKILLS = {
    "docker", "kubernetes", "aws", "ec2", "s3", "rds", "lambda",
    "ci/cd", "github actions", "jenkins", "linux", "nginx", "gunicorn", "cloud",
}
AI_SKILLS = {"machine learning", "ml", "ai", "deep learning", "nlp", "llm"}


def _extract_jd_keywords(description: str) -> dict:
    text = description.lower()

    tech_map = {
        "python": "Python", "django": "Django", "drf": "Django REST Framework",
        "django rest framework": "Django REST Framework", "rest api": "REST APIs",
        "restful": "REST APIs", "postgresql": "PostgreSQL", "postgres": "PostgreSQL",
        "mysql": "MySQL", "sql": "SQL", "react": "React", "react.js": "React",
        "typescript": "TypeScript", "javascript": "JavaScript",
        "docker": "Docker", "kubernetes": "Kubernetes", "k8s": "Kubernetes",
        "aws": "AWS", "ec2": "AWS EC2", "s3": "AWS S3", "rds": "AWS RDS",
        "lambda": "AWS Lambda", "cloud": "cloud infrastructure",
        "celery": "Celery", "redis": "Redis", "rabbitmq": "RabbitMQ",
        "git": "Git", "github": "GitHub", "ci/cd": "CI/CD",
        "github actions": "GitHub Actions", "jenkins": "Jenkins",
        "fastapi": "FastAPI", "flask": "Flask",
        "pytest": "pytest", "testing": "testing", "tdd": "TDD",
        "jwt": "JWT authentication", "oauth": "OAuth",
        "authentication": "authentication", "authorization": "authorization",
        "microservices": "microservices", "api": "APIs",
        "agile": "Agile", "scrum": "Scrum",
        "linux": "Linux", "nginx": "Nginx", "gunicorn": "Gunicorn",
        "machine learning": "machine learning", "ml": "ML",
        "ai": "AI", "deep learning": "deep learning", "nlp": "NLP",
        "llm": "LLM", "data": "data engineering",
        "sqlalchemy": "SQLAlchemy", "orm": "ORM",
        "swagger": "Swagger", "openapi": "OpenAPI", "postman": "Postman",
        "tailwind": "Tailwind CSS", "bootstrap": "Bootstrap",
        "html": "HTML", "css": "CSS", "vue": "Vue.js", "angular": "Angular",
        "mongodb": "MongoDB", "firebase": "Firebase",
        "graphql": "GraphQL", "websocket": "WebSocket",
        "bash": "bash", "shell": "shell scripting",
        "selenium": "Selenium", "automation": "automation",
        "documentation": "documentation",
    }

    found = {}
    for keyword, display in tech_map.items():
        if keyword in text:
            found[keyword] = display

    experience_match = re.search(r"(\d+)\+?\s*(?:-\s*(\d+))?\s*years?", text)
    min_years = int(experience_match.group(1)) if experience_match else None

    role_level = "mid"
    if any(w in text for w in ["senior", "lead", "principal", "staff", "architect", "head", "sr."]):
        role_level = "senior"
    elif any(w in text for w in ["junior", "entry", "fresher", "intern", "trainee", "associate"]):
        role_level = "junior"

    return {"tech": found, "min_years": min_years, "role_level": role_level, "full_text": text}


def _pick_project(jd_req: dict) -> dict:
    jd_keywords = set(jd_req["tech"].keys())

    best = None
    best_score = 0
    for p in _get_profile()["projects"]:
        p_tech = set(t.lower() for t in p["tech"])
        overlap = len(jd_keywords & p_tech)
        if overlap > best_score:
            best_score = overlap
            best = p

    return best or _get_profile()["projects"][0]


def _skill_list(jd_req: dict, max_count: int = 5) -> str:
    seen = set()
    items = []
    for kw, display in jd_req["tech"].items():
        if display.lower() not in seen:
            seen.add(display.lower())
            items.append(display)
        if len(items) >= max_count:
            break
    return ", ".join(items)


def generate_cover_letter(job: dict) -> str:
    matched_skills = job.get("matched_skills", [])
    description = job.get("description", "") + " " + job.get("full_text", "")
    jd_req = _extract_jd_keywords(description)
    company = job.get("company", "your organization")
    title = job.get("title", "the advertised position")
    project = _pick_project(jd_req)

    has_backend = bool(set(jd_req["tech"].keys()) & BACKEND_SKILLS)
    has_frontend = bool(set(jd_req["tech"].keys()) & FRONTEND_SKILLS)
    has_devops = bool(set(jd_req["tech"].keys()) & DEVOPS_SKILLS)
    has_ai = bool(set(jd_req["tech"].keys()) & AI_SKILLS)

    skills_sentence = _skill_list(jd_req)

    if has_backend:
        backend_line = (
            f"I have production-grade Python and Django backend experience, "
            f"having built and deployed {project['name']} -- "
            f"{project['description'].lower()} -- with {', '.join(project['tech'][:5])}."
        )
    else:
        backend_line = (
            f"I have hands-on Python and Django experience from building and deploying "
            f"{project['name']} -- {project['description'].lower()} -- "
            f"using {', '.join(project['tech'][:5])}."
        )

    devops_line = ""
    if has_devops:
        devops_items = []
        if any(k in jd_req["tech"] for k in ["docker", "kubernetes"]):
            devops_items.append("Docker Compose for dev and prod environments")
        if any(k in jd_req["tech"] for k in ["aws", "ec2", "s3", "rds", "cloud"]):
            devops_items.append("AWS EC2, RDS, ElastiCache, S3, and CloudFront")
        if any(k in jd_req["tech"] for k in ["ci/cd", "github actions"]):
            devops_items.append("GitHub Actions CI/CD pipelines")
        if not devops_items:
            devops_items = ["Docker", "AWS (EC2, RDS, S3)", "GitHub Actions CI/CD"]
        devops_line = f"\nOn the DevOps side I have hands-on experience with {', '.join(devops_items)}."

    ai_line = ""
    if has_ai:
        ai_line = (
            "\nOn the AI side I have hands-on LLM integration experience "
            "with prompt engineering, structured outputs, and graceful degradation logic."
        )

    location = job.get("location", "").lower()
    if "remote" in location:
        location_line = f"I am based in {_get_profile()['location']} and available for remote positions."
    elif "india" in location:
        location_line = f"I am based in {_get_profile()['location']} and open to opportunities across India."
    else:
        location_line = f"I am based in {_get_profile()['location']} and open to relocation for the right opportunity."

    second_project = None
    for p in _get_profile()["projects"]:
        if p["name"] != project["name"]:
            second_project = p
            break

    second_line = ""
    if second_project and has_backend:
        second_line = (
            f" I have also shipped {second_project['name']} -- "
            f"{second_project['description'].lower()} -- "
            f"with JWT authentication, role-based access control, and admin analytics, "
            f"all running live in production."
        )

    phone_line = f" | {_get_profile()['phone']}" if _get_profile().get("phone") else ""
    letter = f"""Dear Hiring Manager,

I am applying for the {title} position at {company}. {backend_line}{second_line}{devops_line}{ai_line}

{location_line}

I am genuinely interested in contributing to {company} and happy to discuss how I can add value from day one.

Sincerely,
{_get_profile()['name']}{phone_line} | {_get_profile()['email']}
{_get_profile()['portfolio']}
GitHub: {_get_profile()['github']}
LinkedIn: {_get_profile()['linkedin']}
"""

    return letter.strip()


def send_application(job: dict, cover_letter: str, email_user: str = None, email_pass: str = None, resume_path: str = None, tailored_resume_bytes: bytes = None, tailored_filename: str = None) -> tuple[bool, str]:
    apply_email = job.get("apply_email", "")
    if not apply_email:
        return False, "No email address found for this job"

    sender = email_user or EMAIL_USER
    password = email_pass or EMAIL_PASS
    if not password:
        return False, "Email password not configured. Set credentials in Profile > Security."

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = apply_email
    msg["Subject"] = f"Application for {job.get('title', 'Python Developer')} - {_get_profile()['name']}"

    msg.attach(MIMEText(cover_letter, "plain"))

    if tailored_resume_bytes:
        attachment = MIMEApplication(tailored_resume_bytes, _subtype="pdf")
        filename = tailored_filename or f"{_get_profile()['name'].replace(' ', '_')}_Resume.pdf"
        attachment.add_header("Content-Disposition", "attachment", filename=filename)
        msg.attach(attachment)
        logger.info(f"Tailored resume attached: {filename}")
    else:
        res_path = Path(resume_path) if resume_path else Path(RESUME_PATH)
        if res_path.exists():
            with open(res_path, "rb") as f:
                attachment = MIMEApplication(f.read(), _subtype="pdf")
                attachment.add_header(
                    "Content-Disposition", "attachment",
                    filename=f"{_get_profile()['name'].replace(' ', '_')}_Resume.pdf"
                )
                msg.attach(attachment)
            logger.info(f"Resume attached: {res_path}")
        else:
            logger.warning(f"Resume not found at {res_path}")

    try:
        with smtplib.SMTP_SSL(EMAIL_SMTP_HOST, EMAIL_SMTP_PORT) as server:
            server.login(sender, password)
            server.send_message(msg)
        logger.info(f"Application sent to {apply_email} for {job.get('title')}")
        return True, "Sent"
    except smtplib.SMTPAuthenticationError:
        return False, "Gmail authentication failed. Check your App Password in Profile > Security."
    except smtplib.SMTPRecipientsRefused:
        return False, f"Recipient refused: {apply_email}"
    except Exception as e:
        return False, str(e)


def apply_to_job(job: dict, email_user: str = None, email_pass: str = None, resume_path: str = None, cover_letter_text: str = None) -> dict:
    if cover_letter_text:
        cover_letter = cover_letter_text
        logger.info(f"Using existing cover letter for {job.get('company')}")
    else:
        try:
            from apps.jobs.cv_engine.cover_templates import generate_cover_letter_template
            cover_letter, template_used = generate_cover_letter_template(job)
            logger.info(f"Template cover letter ({template_used}) generated for {job.get('company')}")
        except Exception as e:
            logger.warning(f"Template cover letter failed, falling back to old generator: {e}")
            cover_letter = generate_cover_letter(job)

    success, message = send_application(job, cover_letter, email_user=email_user, email_pass=email_pass, resume_path=resume_path)

    description = job.get("description", "") + " " + job.get("full_text", "")
    jd_req = _extract_jd_keywords(description)
    project = _pick_project(jd_req)

    jd_tech_set = set(jd_req["tech"].keys())

    sections_included = []
    if jd_tech_set & BACKEND_SKILLS:
        sections_included.append("backend")
    if jd_tech_set & FRONTEND_SKILLS:
        sections_included.append("frontend")
    if jd_tech_set & DEVOPS_SKILLS:
        sections_included.append("devops")
    if jd_tech_set & AI_SKILLS:
        sections_included.append("ai")

    skills_in_jd = list(set(display for kw, display in jd_req["tech"].items()))
    skills_highlighted = [s for s in job.get("matched_skills", []) if s.lower() in cover_letter.lower()]

    return {
        "success": success,
        "message": message,
        "cover_letter": cover_letter,
        "email_subject": f"Application for {job.get('title', 'Python Developer')} - {_get_profile()['name']}",
        "skills_in_jd": skills_in_jd,
        "skills_highlighted": skills_highlighted,
        "sections_included": sections_included,
        "project_mentioned": project["name"] if project else "",
        "role_level": jd_req["role_level"],
        "min_years_required": jd_req["min_years"],
    }
