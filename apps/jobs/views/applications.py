from apps.jobs.models import Application
from apps.jobs.serializers import ApplicationSerializer
from apps.jobs.views.base import BaseAPIView
from apps.jobs.views.list_filters import apply_application_filters


class ApplicationList(BaseAPIView):
    def get(self, request):
        apps = Application.objects.select_related("job").order_by("-sent_at")
        apps = apply_application_filters(apps, request.query_params)

        counts = {
            "all": apps.count(),
            "sent": apps.filter(status="sent").count(),
            "failed": apps.filter(status="failed").count(),
        }

        status_filter = request.query_params.get("status", "all")
        if status_filter != "all":
            apps = apps.filter(status=status_filter)

        page, paginator = self.paginate(apps, request)
        serializer = ApplicationSerializer(page, many=True)
        response = paginator.get_paginated_response(serializer.data)
        response.data["counts"] = counts
        return response
