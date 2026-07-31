import pytest

from apps.jobs.models import Job
from apps.jobs.services.cover_letter_client import CoverLetterEngineUnavailableError


def _make_job(**overrides):
    data = {
        "title": "Senior Data Analyst",
        "company": "TechCorp",
        "location": "Remote",
        "description": "We need a data analyst with strong SQL and Power BI experience.",
        "source": "test",
        "uid": "cl-test-uid-1",
        "apply_email": "hr@techcorp.com",
        "apply_url": "https://techcorp.com/careers",
        "job_url": "https://example.com/job/1",
    }
    data.update(overrides)
    return Job.objects.create(**data)


@pytest.mark.django_db
class TestGenerateTemplateCoverLetter:
    def test_falls_back_to_legacy_template_when_engine_down(self, client):
        job = _make_job()
        from apps.jobs.views import generate_template_cl

        def raise_unavailable(*args, **kwargs):
            raise CoverLetterEngineUnavailableError("down")

        generate_template_cl.generate_cover_letter = raise_unavailable
        response = client.post(f"/api/v1/jobs/{job.id}/generate-template-cover-letter/")
        assert response.status_code == 200
        assert response.json()["cover_letter"]

    def test_uses_engine_when_up(self, client):
        job = _make_job()
        from apps.jobs.views import generate_template_cl

        def fake_engine(job_dict, profile, mode="template"):
            return {
                "cover_letter": "Dear Hiring Manager,\n\nEngine letter.\n\nRegards,\nTest",
                "template_used": "deterministic",
                "tailored": True,
                "mode": "template",
                "issues": [],
            }

        generate_template_cl.generate_cover_letter = fake_engine
        response = client.post(f"/api/v1/jobs/{job.id}/generate-template-cover-letter/")
        assert response.status_code == 200
        assert "Engine letter" in response.json()["cover_letter"]
        assert response.json()["template"] == "deterministic"


@pytest.mark.django_db
class TestGenerateCoverLetter:
    def test_no_ai_config_with_engine_down_returns_400(self, client):
        job = _make_job()
        response = client.post(f"/api/v1/jobs/{job.id}/generate-cover-letter/")
        assert response.status_code == 400

    def test_no_ai_config_returns_template_from_engine(self, client):
        job = _make_job()
        from apps.jobs.views import cover_letter

        original = cover_letter.GenerateCoverLetter._generate_template

        def fake_template(self, job):
            from rest_framework.response import Response
            return Response({"cover_letter": "Dear Hiring Manager,\n\nTemplate letter."})

        cover_letter.GenerateCoverLetter._generate_template = fake_template
        try:
            response = client.post(f"/api/v1/jobs/{job.id}/generate-cover-letter/")
        finally:
            cover_letter.GenerateCoverLetter._generate_template = original
        assert response.status_code == 200
        assert "Template letter" in response.json()["cover_letter"]


@pytest.mark.django_db
class TestCoverLetterClient:
    def test_connect_error_raises_unavailable(self, monkeypatch):
        import httpx

        from apps.jobs.services import cover_letter_client

        def raise_connect(*args, **kwargs):
            raise httpx.ConnectError("conn refused")

        monkeypatch.setattr(cover_letter_client, "_get_client", raise_connect)
        with pytest.raises(CoverLetterEngineUnavailableError):
            cover_letter_client.generate_cover_letter({}, {})
