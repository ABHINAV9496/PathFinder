from rest_framework import status

from apps.jobs.models import AIConfig
from apps.jobs.models.ai_config import PROVIDER_PRESETS
from apps.jobs.views.base import BaseAPIView


class ProfileAI(BaseAPIView):
    def get(self, request):
        ai = AIConfig.load()
        return self.success({
            "provider": ai.provider,
            "api_base_url": ai.api_base_url,
            "model_name": ai.model_name,
            "has_api_key": bool(ai.encrypted_api_key),
            "has_ai_config": ai.has_ai_config,
            "presets": {
                k: {"name": v[0], "api_base_url": v[1], "model": v[2]}
                for k, v in PROVIDER_PRESETS.items()
            },
        })

    def post(self, request):
        provider = request.data.get("provider", "").strip()
        api_base_url = request.data.get("api_base_url", "").strip()
        model_name = request.data.get("model_name", "").strip()
        api_key = request.data.get("api_key", "").strip()

        if not api_base_url:
            return self.error("API Base URL is required", status.HTTP_400_BAD_REQUEST)

        if not model_name:
            return self.error("Model name is required", status.HTTP_400_BAD_REQUEST)

        ai = AIConfig.load()
        ai.provider = provider or "custom"
        ai.api_base_url = api_base_url
        ai.model_name = model_name

        if api_key:
            ai.set_api_key(api_key)

        update_fields = ["provider", "api_base_url", "model_name", "updated_at"]
        if api_key:
            update_fields.append("encrypted_api_key")
        ai.save(update_fields=update_fields)

        return self.success({"message": "AI settings saved", "has_ai_config": ai.has_ai_config})

    def delete(self, request):
        ai = AIConfig.load()
        ai.provider = "openai"
        ai.api_base_url = ""
        ai.encrypted_api_key = ""
        ai.model_name = "gpt-4o-mini"
        ai.save(update_fields=["provider", "api_base_url", "encrypted_api_key", "model_name", "updated_at"])
        return self.success({"message": "AI settings removed", "has_ai_config": False})
