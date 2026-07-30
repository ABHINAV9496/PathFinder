import logging
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date, timedelta
from pathlib import Path

from config.settings import EMAIL_USER, EMAIL_PASS, EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, RESUME_PATH
from apps.jobs.profile_manager import load_profile
from apps.jobs.models import Job, Application, DailyStats

logger = logging.getLogger(__name__)

_PROFILE_CACHE = None

def _get_profile():
    global _PROFILE_CACHE
    if _PROFILE_CACHE is None:
        _PROFILE_CACHE = load_profile()
    return _PROFILE_CACHE


def send_daily_summary():
    today = date.today()
    yesterday = today - timedelta(days=1)

    new_jobs = Job.objects.filter(fetched_date__date=today).count()
    matched_today = Job.objects.filter(fetched_date__date=today, status="matched").count()
    applied_today = Application.objects.filter(sent_at__date=today).count()
    failed_today = Application.objects.filter(sent_at__date=today, status="failed").count()

    recent_apps = (
        Application.objects
        .filter(sent_at__date=today)
        .select_related("job")
        .order_by("-sent_at")[:15]
    )

    top_matched = (
        Job.objects
        .filter(status="matched")
        .order_by("-match_score")[:10]
    )

    resume_name = Path(RESUME_PATH).name

    body_lines = [
        f"Daily Job Portal Summary - {today.strftime('%B %d, %Y')}",
        "=" * 50,
        "",
        f"Jobs Fetched Today:  {new_jobs}",
        f"Matched:             {matched_today}",
        f"Applied:             {applied_today}",
        f"Failed:              {failed_today}",
        "",
    ]

    if recent_apps:
        body_lines.append("--- Applications Sent Today ---")
        for app in recent_apps:
            status_icon = "OK" if app.status == "sent" else "FAIL"
            body_lines.append(
                f"  [{status_icon}] {app.job.title} at {app.job.company} "
                f"(Score: {app.job.match_score}%)"
            )
        body_lines.append("")

    if top_matched:
        body_lines.append("--- Top Matched Jobs (Not Yet Applied) ---")
        for job in top_matched:
            if job.status == "matched":
                body_lines.append(
                    f"  {job.match_score}% - {job.title} at {job.company} "
                    f"({job.location}) [{', '.join(job.matched_skills[:3])}]"
                )
        body_lines.append("")

    body_lines.extend([
        "--- Your Profile ---",
        f"Name:     {_get_profile()['name']}",
        f"Email:    {_get_profile()['email']}",
        f"Resume:   {'Found' if os.path.exists(RESUME_PATH) else 'NOT FOUND - place resume.pdf in resume/ folder'}",
        "",
        f"Dashboard: http://localhost:8000",
    ])

    body = "\n".join(body_lines)

    if not EMAIL_PASS:
        logger.warning("EMAIL_PASS not set. Skipping summary email.")
        return False

    msg = MIMEMultipart()
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_USER
    msg["Subject"] = f"[Job Portal] Daily Summary - {new_jobs} fetched, {applied_today} applied"
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL(EMAIL_SMTP_HOST, EMAIL_SMTP_PORT) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        logger.info("Daily summary email sent.")
        return True
    except Exception as e:
        logger.error(f"Failed to send summary: {e}")
        return False
