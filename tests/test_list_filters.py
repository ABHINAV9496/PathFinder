import pytest


def _job(**overrides):
    from apps.jobs.models import Job

    data = {
        "title": "Staff Nurse",
        "company": "City General",
        "location": "Kochi, Kerala, India",
        "description": "Patient care at our hospital.",
        "source": "cutshort",
        "uid": "lf-uid-1",
        "apply_email": "hr@citygeneral.com",
    }
    data.update(overrides)
    return Job.objects.create(**data)


@pytest.mark.django_db
class TestJobFiltersOptions:
    def test_returns_distinct_sources_and_locations(self, client):
        _job(uid="a", source="cutshort", location="Remote")
        _job(uid="b", source="technopark", location="Remote")
        _job(uid="c", source="cutshort", location="Trivandrum, Kerala, India")

        response = client.get("/api/v1/jobs/filters/")
        assert response.status_code == 200
        data = response.json()
        assert data["sources"] == ["cutshort", "technopark"]
        assert "Remote" in data["locations"]
        assert "Trivandrum, Kerala, India" in data["locations"]
        assert data["work_types"] == ["remote", "hybrid", "onsite"]


@pytest.mark.django_db
class TestJobListFilters:
    def test_source_filter(self, client):
        _job(uid="a", source="cutshort")
        _job(uid="b", source="technopark")

        response = client.get("/api/v1/jobs/?source=cutshort")
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["uid"] == "a"

    def test_multi_source_filter(self, client):
        _job(uid="a", source="cutshort")
        _job(uid="b", source="technopark")
        _job(uid="c", source="jobdrop:remoteok")

        response = client.get("/api/v1/jobs/?source=cutshort,technopark")
        data = response.json()
        assert data["count"] == 2

    def test_location_substring_filter(self, client):
        _job(uid="a", location="Remote")
        _job(uid="b", location="Kochi, Kerala, India")

        response = client.get("/api/v1/jobs/?location=Kochi")
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["uid"] == "b"

    def test_work_type_remote_by_keyword(self, client):
        _job(uid="a", location="Remote")
        _job(uid="b", location="Kochi, Kerala, India")

        response = client.get("/api/v1/jobs/?work_type=remote")
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["uid"] == "a"

    def test_work_type_remote_includes_remote_board(self, client):
        _job(uid="a", location="Worldwide", source="jobdrop:remoteok")
        _job(uid="b", location="Kochi, Kerala, India", source="cutshort")

        response = client.get("/api/v1/jobs/?work_type=remote")
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["uid"] == "a"

    def test_work_type_hybrid(self, client):
        _job(uid="a", location="Remote / Hybrid", source="cutshort")
        _job(uid="b", location="Kochi, Kerala, India", source="cutshort")

        response = client.get("/api/v1/jobs/?work_type=hybrid")
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["uid"] == "a"

    def test_work_type_onsite_excludes_remote_and_hybrid(self, client):
        _job(uid="a", location="Remote", source="jobdrop:remoteok")
        _job(uid="b", location="Hybrid", source="cutshort")
        _job(uid="c", location="Kochi, Kerala, India", source="cutshort")

        response = client.get("/api/v1/jobs/?work_type=onsite")
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["uid"] == "c"

    def test_combined_source_location_work_type(self, client):
        _job(uid="a", source="cutshort", location="Remote")
        _job(uid="b", source="cutshort", location="Kochi, Kerala, India")
        _job(uid="c", source="technopark", location="Remote")

        response = client.get("/api/v1/jobs/?source=cutshort&work_type=onsite")
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["uid"] == "b"


@pytest.mark.django_db
class TestApplicationFilters:
    def _make_app(self, uid, source, **job_overrides):
        from apps.jobs.models import Application

        job = _job(uid=uid, source=source, **job_overrides)
        return Application.objects.create(
            job=job, status="sent", email_subject="x", cover_letter_text="y"
        )

    def test_source_filter_via_job(self, client):
        self._make_app("a", "cutshort")
        self._make_app("b", "technopark")

        response = client.get("/api/v1/applications/?source=cutshort")
        data = response.json()
        assert data["count"] == 1

    def test_work_type_filter_via_job(self, client):
        self._make_app("a", "cutshort", location="Remote")
        self._make_app("b", "cutshort", location="Kochi, Kerala, India")

        response = client.get("/api/v1/applications/?work_type=remote")
        data = response.json()
        assert data["count"] == 1

    def test_counts_stable_across_status_tabs(self, client):
        from apps.jobs.models import Application

        self._make_app("a", "cutshort")
        self._make_app("b", "technopark")
        app_b = Application.objects.get(job__uid="b")
        app_b.status = "failed"
        app_b.save()

        response = client.get("/api/v1/applications/")
        data = response.json()
        assert data["counts"] == {"all": 2, "sent": 1, "failed": 1}

        response = client.get("/api/v1/applications/?status=sent")
        data = response.json()
        assert data["count"] == 1
        assert data["counts"] == {"all": 2, "sent": 1, "failed": 1}

        response = client.get("/api/v1/applications/?status=failed")
        data = response.json()
        assert data["count"] == 1
        assert data["counts"] == {"all": 2, "sent": 1, "failed": 1}


@pytest.mark.django_db
class TestOverviewFilters:
    def test_overview_respects_filters(self, client):
        _job(uid="a", source="cutshort", location="Remote")
        _job(uid="b", source="technopark", location="Kochi, Kerala, India")

        response = client.get("/api/v1/stats/overview/?source=cutshort")
        assert response.status_code == 200
        data = response.json()
        assert data["total_matched"] == 1
        assert len(data["recent_jobs"]) == 1
        assert data["recent_jobs"][0]["id"] == 1

    def test_overview_work_type_filter(self, client):
        _job(uid="a", source="cutshort", location="Remote")
        _job(uid="b", source="cutshort", location="Kochi, Kerala, India")

        response = client.get("/api/v1/stats/overview/?work_type=onsite")
        data = response.json()
        assert data["total_matched"] == 1
