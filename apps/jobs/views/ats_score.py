import logging

from rest_framework import status

from apps.jobs.models import Job
from apps.jobs.profile_manager import load_profile
from apps.jobs.views.base import BaseAPIView
from apps.jobs.views.generate_cv import _extract_resume_text

logger = logging.getLogger(__name__)


class ATSScoreView(BaseAPIView):
    def get(self, request, job_id):
        try:
            job = Job.objects.get(pk=job_id)
        except Job.DoesNotExist:
            return self.error("Job not found", status.HTTP_404_NOT_FOUND)

        profile = load_profile()
        profile["resume_text"] = _extract_resume_text()

        job_dict = {
            "title": job.title,
            "company": job.company,
            "location": job.location or "",
            "description": job.description or "",
            "matched_skills": job.matched_skills or [],
            "skill_gaps": job.skill_gaps or [],
            "skill_score_breakdown": job.skill_score_breakdown or {},
            "match_score": job.match_score or 0,
        }

        ai_config = None
        try:
            from apps.jobs.models import AIConfig
            ai = AIConfig.load()
            if ai.has_ai_config and ai.get_api_key():
                ai_config = {
                    "api_key": ai.get_api_key(),
                    "api_base_url": ai.api_base_url,
                    "model": ai.model_name,
                    "provider": ai.provider,
                }
        except Exception as e:
            logger.debug(f"AI config unavailable for ATS score: {e}")

        try:
            from apps.jobs.services.cv_engine_client import get_ats_score
            result = get_ats_score(job_dict, profile, ai_config=ai_config)
            return self.success(result)
        except Exception as e:
            logger.error(f"ATS score failed: {e}")
            return self.success({"score": None, "reason": "cv_engine_unavailable"})
