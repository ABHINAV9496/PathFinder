from apps.jobs.models import Application
from apps.jobs.serializers import ApplicationSerializer
from apps.jobs.views.base import BaseAPIView
from apps.jobs.views.list_filters import apply_application_filters


class ApplicationList(BaseAPIView):
    def get(self, request):
        apps = Application.objects.select_related("job").order_by("-sent_at")

        status_filter = request.query_params.get("status", "all")
        if status_filter != "all":
            apps = apps.filter(status=status_filter)
        apps = apply_application_filters(apps, request.query_params)

        page, paginator = self.paginate(apps, request)
        serializer = ApplicationSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
