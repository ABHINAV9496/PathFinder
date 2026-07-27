import pytest


@pytest.mark.django_db
class TestOverviewView:
    def test_overview_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_overview_template(self, client):
        response = client.get("/")
        assert "overview.html" in [t.name for t in response.templates]


@pytest.mark.django_db
class TestJobListView:
    def test_job_list_returns_200(self, client):
        response = client.get("/jobs/")
        assert response.status_code == 200

    def test_job_list_with_status_filter(self, client, sample_job):
        response = client.get("/jobs/?status=new")
        assert response.status_code == 200

    def test_job_list_with_location_filter(self, client, sample_job):
        response = client.get("/jobs/?location=kerala")
        assert response.status_code == 200


@pytest.mark.django_db
class TestJobDetailView:
    def test_job_detail_returns_200(self, client, sample_job):
        response = client.get(f"/jobs/{sample_job.id}/")
        assert response.status_code == 200

    def test_job_detail_404(self, client):
        response = client.get("/jobs/99999/")
        assert response.status_code == 404


@pytest.mark.django_db
class TestApplicationListView:
    def test_application_list_returns_200(self, client):
        response = client.get("/applications/")
        assert response.status_code == 200


@pytest.mark.django_db
class TestSkillStatsView:
    def test_skill_stats_returns_200(self, client):
        response = client.get("/stats/skills/")
        assert response.status_code == 200


@pytest.mark.django_db
class TestCompanyStatsView:
    def test_company_stats_returns_200(self, client):
        response = client.get("/stats/companies/")
        assert response.status_code == 200


@pytest.mark.django_db
class TestRunFetcherView:
    def test_post_starts_fetcher(self, client):
        response = client.post("/api/fetcher/run/")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_not_allowed(self, client):
        response = client.get("/api/fetcher/run/")
        assert response.status_code == 405

    def test_rejects_when_already_running(self, client):
        import apps.dashboard.views as views
        views._fetcher_running = True
        try:
            response = client.post("/api/fetcher/run/")
            assert response.status_code == 409
        finally:
            views._fetcher_running = False
