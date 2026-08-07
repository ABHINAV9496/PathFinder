from apps.jobs.models import Application
from apps.jobs.serializers import ApplicationSerializer
from apps.jobs.views.base import BaseAPIView
from apps.jobs.views.list_filters import apply_application_filters


class WebApplyList(BaseAPIView):
    def get(self, request):
        apps = (
            Application.objects
            .select_related("job")
            .filter(status="web_apply")
            .order_by("-sent_at")
        )
        apps = apply_application_filters(apps, request.query_params)
        serializer = ApplicationSerializer(apps, many=True)
        return self.success({
            "applications": serializer.data,
            "total_count": apps.count(),
        })
