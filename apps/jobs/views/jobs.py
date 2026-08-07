from django.db.models import Q

from apps.jobs.models import Job
from apps.jobs.serializers import JobSerializer, JobDetailSerializer
from apps.jobs.views.base import BaseAPIView
from apps.jobs.views.list_filters import apply_job_filters, filter_options


class JobFiltersOptions(BaseAPIView):
    def get(self, request):
        return self.success(filter_options())


class JobList(BaseAPIView):
    def get(self, request):
        jobs = Job.objects.all()

        status_filter = request.query_params.get("status", "all")
        salary_filter = request.query_params.get("salary", "all")
        sort = request.query_params.get("sort", "-match_score")
        search = request.query_params.get("search", "")

        if status_filter != "all":
            jobs = jobs.filter(status=status_filter)
        else:
            jobs = jobs.exclude(status="ignored")

        jobs = apply_job_filters(jobs, request.query_params)

        if salary_filter == "has":
            jobs = jobs.filter(salary__gt=0)
        elif salary_filter == "3l":
            jobs = jobs.filter(salary__gte=300000)
        elif salary_filter == "6l":
            jobs = jobs.filter(salary__gte=600000)
        elif salary_filter == "10l":
            jobs = jobs.filter(salary__gte=1000000)

        valid_sorts = ["-match_score", "match_score", "-fetched_date", "company", "title", "-salary", "salary"]
        if sort in valid_sorts:
            jobs = jobs.order_by(sort)

        if search:
            jobs = jobs.filter(
                Q(title__icontains=search) |
                Q(company__icontains=search) |
                Q(matched_skills__icontains=search)
            )

        page, paginator = self.paginate(jobs, request)
        serializer = JobSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class JobDetail(BaseAPIView):
    def get(self, request, job_id):
        from django.shortcuts import get_object_or_404

        job = get_object_or_404(Job.objects.select_related(), id=job_id)
        serializer = JobDetailSerializer(job)
        return self.success(serializer.data)
