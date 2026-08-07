"""Onboarding wizard profile writes (Phase 8/9).

The React onboarding wizard saves through the existing profile API
(``POST /api/v1/profile/``). These tests lock in the profile-view behavior
the wizard depends on: new neutral fields persisted, ``experience_years=0``
allowed for fresh grads, and string-typed lists normalized.
"""

import json

import pytest


@pytest.mark.django_db
def _post_profile(client, payload):
    return client.post(
        "/api/v1/profile/",
        data=json.dumps({"profile": payload}),
        content_type="application/json",
    )


@pytest.mark.django_db
class TestOnboardingProfileWrites:
    def test_saves_new_neutral_fields(self, client, monkeypatch, tmp_path):
        import apps.jobs.profile_manager as pm

        monkeypatch.setattr(pm, "PROFILE_JSON", tmp_path / "profile.json")
        monkeypatch.setattr(pm, "_legacy_profile_py", lambda: {})

        payload = {
            "name": "Maya Nurse",
            "email": "maya@example.com",
            "phone": "555-0100",
            "role": "Registered Nurse",
            "profession": "Healthcare",
            "experience_years": 6,
            "location": "Kochi",
            "country": "India",
            "currency": "INR",
            "min_salary": 35000,
            "timezone": "Asia/Kolkata",
            "skills": {
                "patient_care": ["wound care", "medication administration"],
                "qualifications": ["BSc Nursing"],
            },
            "looking_for": ["staff nurse", "charge nurse"],
            "languages": ["English", "Malayalam"],
            "projects": [
                {"name": "City General ER", "description": "Reduced triage wait by 20%"}
            ],
        }
        response = _post_profile(client, payload)
        assert response.status_code == 200

        saved = pm.load_profile()
        assert saved["name"] == "Maya Nurse"
        assert saved["profession"] == "Healthcare"
        assert saved["country"] == "India"
        assert saved["currency"] == "INR"
        assert saved["min_salary"] == 35000
        assert saved["timezone"] == "Asia/Kolkata"
        assert saved["experience_years"] == 6
        assert saved["skills"]["patient_care"] == ["wound care", "medication administration"]
        assert saved["looking_for"] == ["staff nurse", "charge nurse"]
        assert saved["languages"] == ["English", "Malayalam"]
        assert saved["projects"][0]["name"] == "City General ER"

    def test_allows_zero_experience_years(self, client, monkeypatch, tmp_path):
        import apps.jobs.profile_manager as pm

        monkeypatch.setattr(pm, "PROFILE_JSON", tmp_path / "profile.json")
        monkeypatch.setattr(pm, "_legacy_profile_py", lambda: {})

        payload = {
            "name": "Aya Freshgrad",
            "email": "aya@example.com",
            "role": "Junior Accountant",
            "experience_years": 0,
            "location": "Cochin",
        }
        response = _post_profile(client, payload)
        assert response.status_code == 200
        assert pm.load_profile()["experience_years"] == 0

    def test_normalizes_string_skills_and_lists(self, client, monkeypatch, tmp_path):
        import apps.jobs.profile_manager as pm

        monkeypatch.setattr(pm, "PROFILE_JSON", tmp_path / "profile.json")
        monkeypatch.setattr(pm, "_legacy_profile_py", lambda: {})

        payload = {
            "name": "Leo Teacher",
            "email": "leo@example.com",
            "role": "High School Teacher",
            "experience_years": 4,
            "location": "Trivandrum",
            "skills": {"teaching": "lesson planning, classroom management"},
            "looking_for": "teacher, lecturer",
            "languages": "English, Malayalam",
        }
        response = _post_profile(client, payload)
        assert response.status_code == 200

        saved = pm.load_profile()
        assert saved["skills"]["teaching"] == ["lesson planning", "classroom management"]
        assert saved["looking_for"] == ["teacher", "lecturer"]
        assert saved["languages"] == ["English", "Malayalam"]

    def test_missing_name_returns_400(self, client, monkeypatch, tmp_path):
        import apps.jobs.profile_manager as pm

        monkeypatch.setattr(pm, "PROFILE_JSON", tmp_path / "profile.json")
        monkeypatch.setattr(pm, "_legacy_profile_py", lambda: {})

        response = _post_profile(client, {"email": "no-name@example.com"})
        assert response.status_code == 400
