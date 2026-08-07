from types import SimpleNamespace

import pytest


class TestSalaryCurrencyVariety:
    def test_inr_lpa(self):
        from apps.jobs.services.core import _extract_salary_from_text
        salary, display = _extract_salary_from_text("Salary: \u20b912 LPA plus equity")
        assert salary == 1200000
        assert display == "\u20b912L PA"

    def test_usd_annual(self):
        from apps.jobs.services.core import _extract_salary_from_text
        salary, display = _extract_salary_from_text("Compensation: $80,000/yr DOE")
        assert salary == 80000
        assert display == "$80K"

    def test_eur_per_annum(self):
        from apps.jobs.services.core import _extract_salary_from_text
        salary, display = _extract_salary_from_text("\u20ac60,000 per annum")
        assert salary == 60000
        assert display == "\u20ac60K"

    def test_gbp_per_year(self):
        from apps.jobs.services.core import _extract_salary_from_text
        salary, display = _extract_salary_from_text("\u00a350,000 per year")
        assert salary == 50000
        assert display == "\u00a350K"

    def test_usd_monthly_annualized(self):
        from apps.jobs.services.core import _extract_salary_from_text
        salary, display = _extract_salary_from_text("Salary: $5,000 per month")
        assert salary == 60000
        assert display == "$60K"

    def test_competitive_salary_is_unknown(self):
        from apps.jobs.services.core import _extract_salary_from_text
        salary, display = _extract_salary_from_text("Competitive salary based on experience")
        assert salary == 0
        assert display == ""

    def test_training_fee_ignored(self):
        from apps.jobs.services.core import _extract_salary_from_text
        salary, display = _extract_salary_from_text("Training fee of \u20b915000 must be paid")
        assert salary == 0
        assert display == ""


class TestCutshortParserRobustness:
    def test_missing_company_returns_none(self):
        from apps.jobs.fetchers.cutshort import _parse_job
        assert _parse_job({"headline": "Data Analyst"}) is None

    def test_missing_salary_range(self):
        from apps.jobs.fetchers.cutshort import _parse_job
        job = _parse_job({
            "headline": "Backend Engineer",
            "companyDetails": {"name": "Acme"},
        })
        assert job is not None
        assert job["salary"] == 0
        assert job["salary_display"] == ""

    def test_missing_locations_defaults(self):
        from apps.jobs.fetchers.cutshort import _parse_job
        job = _parse_job({
            "headline": "Backend Engineer",
            "companyDetails": {"name": "Acme"},
        })
        assert job["location"] == "Not specified"

    def test_missing_skills_defaults_empty(self):
        from apps.jobs.fetchers.cutshort import _parse_job
        job = _parse_job({
            "headline": "Backend Engineer",
            "companyDetails": {"name": "Acme"},
        })
        assert job["skills"] == []

    def test_full_job_parsed(self):
        from apps.jobs.fetchers.cutshort import _parse_job
        job = _parse_job({
            "headline": "Data Analyst",
            "companyDetails": {"name": "Analytics Co"},
            "locations": ["Bangalore", "Remote"],
            "salaryRange": {"min": 800000, "max": 1200000},
            "expRange": {"min": 2, "max": 5},
            "allSkills": ["SQL", "Power BI"],
            "remoteType": "remote_okay",
        })
        assert job["title"] == "Data Analyst"
        assert job["salary"] == 1200000
        assert job["salary_display"] == "8L-12L PA"
        assert job["remote"] is True
        assert "SQL" in job["skills"]

    def test_next_data_missing(self):
        from apps.jobs.fetchers.cutshort import _extract_next_data
        assert _extract_next_data("<html><body>No data</body></html>") is None


class TestJobdropSalaryMapping:
    def test_yearly_range(self):
        from apps.jobs.fetchers.jobdrop_fetcher import _map_salary
        row = SimpleNamespace(
            min_amount=100000, max_amount=120000, interval="yearly", currency="USD"
        )
        annual, display = _map_salary(row)
        assert annual == 120000
        assert display == "USD 100,000-120,000/yr"

    def test_monthly_annualized(self):
        from apps.jobs.fetchers.jobdrop_fetcher import _map_salary
        row = SimpleNamespace(min_amount=5000, max_amount=7000, interval="monthly", currency="USD")
        annual, display = _map_salary(row)
        assert annual == 84000
        assert display == "USD 5,000-7,000/mo"

    def test_hourly_single_value(self):
        from apps.jobs.fetchers.jobdrop_fetcher import _map_salary
        row = SimpleNamespace(min_amount=30, max_amount=None, interval="hourly", currency="USD")
        annual, display = _map_salary(row)
        assert annual == 62400
        assert display == "USD 62,400/yr"

    def test_no_amounts(self):
        from apps.jobs.fetchers.jobdrop_fetcher import _map_salary
        row = SimpleNamespace(min_amount=None, max_amount=None, interval="yearly", currency="USD")
        assert _map_salary(row) == (0, "")

    def test_inr_currency_display(self):
        from apps.jobs.fetchers.jobdrop_fetcher import _map_salary
        row = SimpleNamespace(
            min_amount=500000, max_amount=800000, interval="yearly", currency="INR"
        )
        annual, display = _map_salary(row)
        assert annual == 800000
        assert "INR" in display


class TestJobdropLocationMapping:
    def test_dict_location(self):
        from apps.jobs.fetchers.jobdrop_fetcher import _map_location
        row = SimpleNamespace(
            location={"city": "Bangalore", "state": "Karnataka", "country": "India"}
        )
        assert _map_location(row) == "Bangalore, Karnataka, India"

    def test_string_location(self):
        from apps.jobs.fetchers.jobdrop_fetcher import _map_location
        assert _map_location(SimpleNamespace(location="Remote")) == "Remote"

    def test_missing_location(self):
        from apps.jobs.fetchers.jobdrop_fetcher import _map_location
        assert _map_location(SimpleNamespace(location=None)) == "Not specified"

    def test_empty_dict_location(self):
        from apps.jobs.fetchers.jobdrop_fetcher import _map_location
        assert _map_location(SimpleNamespace(location={})) == "Not specified"


class TestJobdropPruning:
    def _make_jobs(self):
        return [
            {
                "uid": "uid-a",
                "title": "Data Analyst",
                "company": "Acme",
                "location": "Remote",
                "description": "",
                "posted_date": "",
                "source": "jobdrop",
                "apply_email": "",
                "apply_url": "",
                "search_query": "jobdrop: analyst",
                "job_url": "",
                "salary": 0,
                "salary_display": "",
                "full_text": "Data Analyst Acme Remote",
            },
            {
                "uid": "uid-b",
                "title": "Backend Engineer",
                "company": "Beta",
                "location": "Remote",
                "description": "",
                "posted_date": "",
                "source": "jobdrop",
                "apply_email": "",
                "apply_url": "",
                "search_query": "jobdrop: backend",
                "job_url": "",
                "salary": 0,
                "salary_display": "",
                "full_text": "Backend Engineer Beta Remote",
            },
        ]

    def test_deduplicates_overlapping_queries(self, monkeypatch):
        import apps.jobs.fetchers.jobdrop_fetcher as jf
        jobs = self._make_jobs()
        queries = [{"search_term": "a"}, {"search_term": "b"}]
        monkeypatch.setattr(jf, "get_jobdrop_queries", lambda: queries)
        monkeypatch.setattr(jf, "_fetch_single_jobdrop_query", lambda q: jobs)
        result = jf.fetch_jobdrop_jobs()
        assert len(result) == 2

    def test_empty_queries_return_empty(self, monkeypatch):
        import apps.jobs.fetchers.jobdrop_fetcher as jf
        monkeypatch.setattr(jf, "get_jobdrop_queries", lambda: [])
        assert jf.fetch_jobdrop_jobs() == []

    def test_site_name_from_enum(self):
        from apps.jobs.fetchers.jobdrop_fetcher import _site_name
        assert _site_name(SimpleNamespace(value="linkedin")) == "linkedin"

    def test_site_name_none(self):
        from apps.jobs.fetchers.jobdrop_fetcher import _site_name
        assert _site_name(None) == ""


class TestProfileFreshClone:
    def test_load_profile_when_missing_returns_defaults(self, monkeypatch, tmp_path):
        import apps.jobs.profile_manager as pm
        monkeypatch.setattr(pm, "PROFILE_JSON", tmp_path / "profile.json")
        monkeypatch.setattr(pm, "_legacy_profile_py", lambda: {})
        profile = pm.load_profile()
        assert profile["name"] == ""
        assert profile["skills"] == {}
        assert profile["currency"] == "USD"
        assert profile["timezone"] == ""

    def test_ensure_default_profile_creates_file(self, monkeypatch, tmp_path):
        import apps.jobs.profile_manager as pm
        monkeypatch.setattr(pm, "PROFILE_JSON", tmp_path / "profile.json")
        assert pm.ensure_default_profile() is True
        assert (tmp_path / "profile.json").exists()
        assert pm.ensure_default_profile() is False

    def test_loaded_profile_merges_defaults(self, monkeypatch, tmp_path):
        import apps.jobs.profile_manager as pm
        monkeypatch.setattr(pm, "PROFILE_JSON", tmp_path / "profile.json")
        monkeypatch.setattr(pm, "_legacy_profile_py", lambda: {})
        pm.save_profile({"name": "Ada"})
        profile = pm.load_profile()
        assert profile["name"] == "Ada"
        assert profile["skills"] == {}
        assert profile["languages"] == []

    def test_legacy_profile_py_merges_as_bootstrap(self, monkeypatch, tmp_path):
        import apps.jobs.profile_manager as pm
        monkeypatch.setattr(pm, "PROFILE_JSON", tmp_path / "profile.json")
        monkeypatch.setattr(pm, "_legacy_profile_py", lambda: {"name": "Legacy", "currency": "EUR"})
        profile = pm.load_profile()
        assert profile["name"] == "Legacy"
        assert profile["currency"] == "EUR"

    def test_profile_json_overrides_legacy_profile_py(self, monkeypatch, tmp_path):
        import apps.jobs.profile_manager as pm
        monkeypatch.setattr(pm, "PROFILE_JSON", tmp_path / "profile.json")
        monkeypatch.setattr(pm, "_legacy_profile_py", lambda: {"name": "Legacy", "currency": "EUR"})
        pm.save_profile({"name": "Ada", "currency": "GBP"})
        profile = pm.load_profile()
        assert profile["name"] == "Ada"
        assert profile["currency"] == "GBP"

    def test_untouched_default_in_json_does_not_clobber_legacy(self, monkeypatch, tmp_path):
        import apps.jobs.profile_manager as pm
        monkeypatch.setattr(pm, "PROFILE_JSON", tmp_path / "profile.json")
        monkeypatch.setattr(pm, "_legacy_profile_py", lambda: {"name": "Legacy"})
        pm.save_profile(dict(pm.DEFAULT_PROFILE))
        profile = pm.load_profile()
        assert profile["name"] == "Legacy"

    def test_build_skill_weights_from_profile(self):
        from apps.jobs.profile_manager import build_skill_weights
        profile = {"skills": {"backend": ["Python", "Django"], "mystery": ["Foo"]}}
        weights = build_skill_weights(profile)
        assert weights["python"] == 20
        assert weights["django"] == 20
        assert weights["foo"] == 5


class TestGenerateCVDelegation:
    def _engine_response(self, **overrides):
        base = {
            "tailored_resume": "TAILORED VIA ENGINE",
            "ats_report": {
                "score": 82,
                "breakdown": {"keyword_coverage": 80},
                "summary": "engine summary",
                "source": "deterministic",
            },
            "gap_report": {"confirmed_gaps": [], "research_flagged_gaps": []},
            "source_trace": [{"claim": "x", "source": "original_resume", "confirmed": True}],
            "suggested_keywords": ["sql"],
            "pdf_base64": "",
            "filename": "Resume.pdf",
        }
        base.update(overrides)
        return base

    @pytest.mark.django_db
    def test_engine_result_passed_through(self, client, sample_job, monkeypatch):
        import apps.jobs.services.cv_engine_client as client_mod

        calls = {}
        def fake_generate_cv(job, profile, company_context=None):
            calls["job"] = job
            calls["profile"] = profile
            return self._engine_response()

        monkeypatch.setattr(client_mod, "generate_cv", fake_generate_cv)
        response = client.post(f"/api/v1/jobs/{sample_job.id}/generate-cv/")
        assert response.status_code == 200
        data = response.json()
        assert data["tailored_resume"] == "TAILORED VIA ENGINE"
        assert data["ats_score_estimate"]["score"] == 82
        assert data["filename"] == "Resume.pdf"
        assert calls["job"]["title"] == sample_job.title
        assert "resume_text" in calls["profile"]

    @pytest.mark.django_db
    def test_fallback_when_engine_unavailable(self, client, sample_job, monkeypatch):
        import apps.jobs.services.cv_engine_client as client_mod
        from apps.jobs.services.cv_engine_client import CVEngineUnavailableError

        def fake_generate_cv(job, profile, company_context=None):
            raise CVEngineUnavailableError("service down")

        monkeypatch.setattr(client_mod, "generate_cv", fake_generate_cv)
        response = client.post(f"/api/v1/jobs/{sample_job.id}/generate-cv/")
        assert response.status_code == 200
        data = response.json()
        assert data["tailored_resume"]
        assert "PROFESSIONAL SUMMARY" in data["tailored_resume"]
        assert data["ats_score_estimate"]["score"] is not None
