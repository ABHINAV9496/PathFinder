import logging

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status

from apps.jobs.cv_engine.renderer import render_cv_pdf
from apps.jobs.models import Job
from apps.jobs.views.base import BaseAPIView

logger = logging.getLogger(__name__)


class GenerateCV(BaseAPIView):
    def post(self, request, job_id):
        job_obj = get_object_or_404(Job.objects.select_related(), id=job_id)

        job_dict = {
            "id": job_obj.id,
            "company": job_obj.company,
            "title": job_obj.title,
            "location": job_obj.location or "",
            "description": job_obj.description or "",
            "salary_text": job_obj.salary_text or "",
            "skills_required": job_obj.skills_required or [],
            "matched_skills": job_obj.matched_skills or [],
        }

        template_override = request.data.get("template")

        try:
            pdf_bytes, filename = render_cv_pdf(job_dict, template_override=template_override)
        except Exception as e:
            logger.error("CV generation failed for job %d: %s", job_id, e)
            return self.error(
                f"CV generation failed: {e}",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
