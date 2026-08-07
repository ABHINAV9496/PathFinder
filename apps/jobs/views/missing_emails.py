from apps.jobs.models import Job
from apps.jobs.serializers import JobSerializer
from apps.jobs.views.base import BaseAPIView
from apps.jobs.views.list_filters import apply_job_filters


class MissingEmailsList(BaseAPIView):
    def get(self, request):
        jobs = (
            Job.objects
            .filter(status="matched", apply_email="")
            .order_by("-match_score")
        )
        jobs = apply_job_filters(jobs, request.query_params)
        serializer = JobSerializer(jobs, many=True)
        return self.success({
            "jobs": serializer.data,
            "total_count": jobs.count(),
        })
