import json

from rest_framework import status

from apps.jobs.views.base import BaseAPIView


class UserProfile(BaseAPIView):
    def get(self, request):
        from apps.jobs.profile_manager import load_profile
        profile = load_profile()
        return self.success({"profile": profile})

    def post(self, request):
        from apps.jobs.profile_manager import save_profile

        try:
            data = json.loads(request.body)
        except Exception:
            return self.error("Invalid JSON", status.HTTP_400_BAD_REQUEST)

        profile = data.get("profile", {})
        required = ["name", "email", "role", "experience_years", "location"]
        for field in required:
            value = profile.get(field)
            if value in (None, ""):
                return self.error(f"Missing required field: {field}", status.HTTP_400_BAD_REQUEST)

        for cat in profile.get("skills", {}):
            raw = profile["skills"][cat]
            if isinstance(raw, str):
                profile["skills"][cat] = [s.strip() for s in raw.split(",") if s.strip()]

        projects_raw = profile.get("projects", "[]")
        if isinstance(projects_raw, str):
            try:
                profile["projects"] = json.loads(projects_raw)
            except json.JSONDecodeError:
                profile["projects"] = []

        looking_raw = profile.get("looking_for", "")
        if isinstance(looking_raw, str):
            profile["looking_for"] = [s.strip() for s in looking_raw.split(",") if s.strip()]

        lang_raw = profile.get("languages", "")
        if isinstance(lang_raw, str):
            profile["languages"] = [s.strip() for s in lang_raw.split(",") if s.strip()]

        int_fields = [("experience_years", 1), ("experience_min", 0), ("experience_max", 3)]
        for field, default in int_fields:
            try:
                profile[field] = int(profile.get(field, default))
            except (ValueError, TypeError):
                profile[field] = default

        try:
            profile["min_salary"] = int(profile.get("min_salary", 0))
        except (ValueError, TypeError):
            profile["min_salary"] = 0

        experience_raw = profile.get("experience", [])
        if isinstance(experience_raw, str):
            try:
                experience_raw = json.loads(experience_raw)
            except json.JSONDecodeError:
                experience_raw = []
        if not isinstance(experience_raw, list):
            experience_raw = []
        valid_types = {"full-time", "part-time", "internship", "freelance", "contract"}
        cleaned_exp = []
        for i, entry in enumerate(experience_raw[:5]):
            if not isinstance(entry, dict):
                continue
            exp_type = entry.get("type", "full-time")
            if exp_type not in valid_types:
                exp_type = "full-time"
            highlights = entry.get("highlights", [])
            if isinstance(highlights, str):
                highlights = [h.strip() for h in highlights.split("\n") if h.strip()]
            cleaned_exp.append({
                "id": entry.get("id", i),
                "role": entry.get("role", ""),
                "company": entry.get("company", ""),
                "location": entry.get("location", ""),
                "duration": entry.get("duration", ""),
                "type": exp_type,
                "highlights": highlights[:5],
                "tech": entry.get("tech", []),
            })
        profile["experience"] = cleaned_exp

        phone_raw = profile.get("phone", "")
        if isinstance(phone_raw, str):
            profile["phone"] = phone_raw.strip()

        for field in ["github", "linkedin", "portfolio", "website",
                      "profession", "country", "timezone", "currency"]:
            val = profile.get(field, "")
            if isinstance(val, str):
                profile[field] = val.strip()

        if save_profile(profile):
            return self.success({"success": True, "message": "Profile saved successfully"})
        return self.error("Failed to save profile", status.HTTP_500_INTERNAL_SERVER_ERROR)
