from apps.jobs.matcher import classify_jd_keywords, match_all_jobs, match_job


class TestMatchJob:
    def test_match_python_job(self):
        job = {
            "title": "Python Developer",
            "company": "TechCorp",
            "location": "Kerala, India",
            "description": "Looking for Python developer with Django experience",
            "uid": "test-uid-001",
        }
        result = match_job(job)
        assert "match_score" in result
        assert result["match_score"] > 0

    def test_match_non_python_job(self):
        job = {
            "title": "Java Developer",
            "company": "BigCorp",
            "location": "Bangalore",
            "description": "Looking for Java developer with Spring Boot",
            "uid": "test-uid-002",
        }
        result = match_job(job)
        assert result["match_score"] == 0

    def test_match_empty_description(self):
        job = {
            "title": "Python Developer",
            "company": "TechCorp",
            "location": "Remote",
            "description": "",
            "uid": "test-uid-003",
        }
        result = match_job(job)
        assert "match_score" in result

    def test_tier_gate_rejects_when_required_skills_unmet(self):
        job = {
            "title": "Go Engineer",
            "company": "BigCorp",
            "location": "Remote India",
            "description": (
                "We require strong Go experience. Must have Go and gRPC. "
                "Go and gRPC are mandatory."
            ),
            "uid": "test-uid-004",
        }
        result = match_job(job)
        assert result["match_score"] == 0
        assert result["status"] == "ignored"
        assert "Missing required skills" in result.get("filter_reason", "")


class TestClassifyJdKeywords:
    def test_classifies_must_have_as_tier0(self):
        tiers = classify_jd_keywords("We require Python and Django. Django is mandatory.")
        assert "python" in tiers["tier0"] or "django" in tiers["tier0"]

    def test_classifies_nice_to_have_as_tier5(self):
        tiers = classify_jd_keywords("Docker is a nice to have. Git preferred.")
        assert "docker" in tiers["tier5"] or "git" in tiers["tier5"]

    def test_classifies_profile_skills_as_tier1(self):
        tiers = classify_jd_keywords("Looking for a developer with Django and FastAPI.")
        assert any(t in tiers["tier1"] for t in ("django", "fastapi"))


class TestMatchAllJobs:
    def test_match_multiple_jobs(self):
        jobs = [
            {
                "title": "Python Developer",
                "company": "TechCorp",
                "location": "Kerala",
                "description": "Python Django developer",
                "uid": "test-uid-010",
            },
            {
                "title": "Python Backend Engineer",
                "company": "StartupCo",
                "location": "Remote India",
                "description": "Python FastAPI developer",
                "uid": "test-uid-011",
            },
        ]
        results = match_all_jobs(jobs)
        assert len(results) == 2
        assert all(r["match_score"] > 0 for r in results)

    def test_match_empty_list(self):
        results = match_all_jobs([])
        assert results == []
