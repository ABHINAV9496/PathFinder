import logging
import re
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from apps.jobs.profile_manager import load_profile
from config.settings import EMAIL_PASS, EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, EMAIL_USER, RESUME_PATH

logger = logging.getLogger(__name__)

_PROFILE_CACHE = None

def _get_profile():
    global _PROFILE_CACHE
    if _PROFILE_CACHE is None:
        _PROFILE_CACHE = load_profile()
    return _PROFILE_CACHE

def _best_project(job: dict) -> dict:
    """Pick the profile project most relevant to this job (profession-neutral)."""
    profile = _get_profile()
    matched = {s.lower() for s in (job.get("matched_skills") or [])}
    desc = (job.get("description") or "").lower()
    projects = profile.get("projects", []) or []
    if not projects:
        return {}

    scored = []
    for p in projects:
        p_tech = {t.lower() for t in p.get("tech", [])}
        overlap = len(matched & p_tech)
        desc_bonus = sum(1 for t in p_tech if t in desc)
        scored.append((overlap + desc_bonus, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]


def _role_level_and_min_years(job: dict) -> tuple[str, int | None]:
    """Neutral role level + min-years estimate from the JD text."""
    text = f"{job.get('title', '')} {job.get('description', '')}".lower()
    if any(w in text for w in ["senior", "lead", "principal", "staff", "architect", "head", "sr."]):
        level = "senior"
    elif any(w in text for w in ["junior", "entry", "fresher", "intern", "trainee", "associate"]):
        level = "junior"
    else:
        level = "mid"

    match = re.search(r"(\d+)\+?\s*(?:-\s*(\d+))?\s*years?", text)
    min_years = int(match.group(1)) if match else None
    return level, min_years


def send_application(
    job: dict,
    cover_letter: str,
    email_user: str = None,
    email_pass: str = None,
    resume_path: str = None,
    tailored_resume_bytes: bytes = None,
    tailored_filename: str = None,
) -> tuple[bool, str]:
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
    msg["Subject"] = f"Application for {job.get('title', 'Position')} - {_get_profile()['name']}"

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


def apply_to_job(
    job: dict,
    email_user: str = None,
    email_pass: str = None,
    resume_path: str = None,
    cover_letter_text: str = None,
) -> dict:
    if cover_letter_text:
        cover_letter = cover_letter_text
        logger.info(f"Using existing cover letter for {job.get('company')}")
    else:
        from apps.jobs.cv_engine.cover_templates import generate_cover_letter_template
        cover_letter, template_used = generate_cover_letter_template(job)
        logger.info(f"Cover letter ({template_used}) generated for {job.get('company')}")

    success, message = send_application(
        job, cover_letter, email_user=email_user, email_pass=email_pass, resume_path=resume_path
    )

    matched_skills = job.get("matched_skills") or []
    skills_highlighted = [s for s in matched_skills if s.lower() in cover_letter.lower()]
    project = _best_project(job)
    role_level, min_years = _role_level_and_min_years(job)

    return {
        "success": success,
        "message": message,
        "cover_letter": cover_letter,
        "email_subject": (
            f"Application for {job.get('title', 'Position')} - {_get_profile()['name']}"
        ),
        "skills_in_jd": matched_skills,
        "skills_highlighted": skills_highlighted,
        "sections_included": [],
        "project_mentioned": project.get("name", "") if project else "",
        "role_level": role_level,
        "min_years_required": min_years,
    }
