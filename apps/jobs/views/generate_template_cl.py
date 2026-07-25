import logging

from django.shortcuts import get_object_or_404
from rest_framework import status

from apps.jobs.cv_engine.cover_templates import generate_cover_letter_template
from apps.jobs.models import Application, Job
from apps.jobs.views.base import BaseAPIView

logger = logging.getLogger(__name__)


class GenerateTemplateCoverLetter(BaseAPIView):
    def post(self, request, job_id):
        job_obj = get_object_or_404(Job.objects.select_related(), id=job_id)

        job_dict = {
            "id": job_obj.id,
            "company": job_obj.company,
            "title": job_obj.title,
            "location": job_obj.location or "",
            "description": job_obj.description or "",
            "matched_skills": job_obj.matched_skills or [],
            "skill_gaps": job_obj.skill_gaps or [],
        }

        cover_letter, template_used = generate_cover_letter_template(job_dict)

        app, _ = Application.objects.get_or_create(job=job_obj)
        app.cover_letter_text = cover_letter
        app.save(update_fields=["cover_letter_text"])

        return self.success({
            "cover_letter": cover_letter,
            "template": template_used,
        })
