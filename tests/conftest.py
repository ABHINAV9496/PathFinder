import os
import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")


@pytest.fixture(autouse=True)
def _override_settings(settings):
    settings.DEBUG = True
    settings.SECURE_SSL_REDIRECT = False
    settings.CSRF_COOKIE_SECURE = False
    settings.SESSION_COOKIE_SECURE = False


@pytest.fixture
def job_data():
    return {
        "title": "Python Developer",
        "company": "TechCorp",
        "location": "Kerala, India",
        "description": "Looking for Python developer with Django experience",
        "source": "test",
        "uid": "test-uid-123",
        "apply_email": "hr@techcorp.com",
        "apply_url": "https://techcorp.com/careers",
        "job_url": "https://example.com/job/123",
    }


@pytest.fixture
def sample_job(db, job_data):
    from apps.jobs.models import Job
    return Job.objects.create(**job_data)


@pytest.fixture
def sample_application(db, sample_job):
    from apps.jobs.models import Application
    return Application.objects.create(
        job=sample_job,
        email_subject="Application for Python Developer - Test",
        cover_letter_text="I am a Python developer with 3 years of experience.",
        status="sent",
    )
