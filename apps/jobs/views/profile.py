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
            if not profile.get(field):
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

        for field, default in [("experience_years", 1), ("experience_min", 0), ("experience_max", 3)]:
            try:
                profile[field] = int(profile.get(field, default))
            except (ValueError, TypeError):
                profile[field] = default

        if save_profile(profile):
            return self.success({"success": True, "message": "Profile saved successfully"})
        return self.error("Failed to save profile", status.HTTP_500_INTERNAL_SERVER_ERROR)
