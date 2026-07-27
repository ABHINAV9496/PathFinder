from rest_framework import status

from apps.jobs.models import CredStore
from apps.jobs.views.base import BaseAPIView


class ProfileSecurity(BaseAPIView):
    def get(self, request):
        cred = CredStore.load()
        return self.success({
            "sender_email": cred.sender_email,
            "has_password": bool(cred.encrypted_password),
            "has_credentials": cred.has_credentials,
        })

    def post(self, request):
        email = request.data.get("sender_email", "").strip()
        password = request.data.get("password", "")

        if not email:
            return self.error("Sender email is required", status.HTTP_400_BAD_REQUEST)

        if not password:
            return self.error("App password is required", status.HTTP_400_BAD_REQUEST)

        cred = CredStore.load()
        cred.sender_email = email
        cred.set_password(password)
        cred.save(update_fields=["sender_email", "encrypted_password"])

        return self.success({"message": "Credentials saved securely", "has_credentials": True})

    def delete(self, request):
        cred = CredStore.load()
        cred.sender_email = ""
        cred.encrypted_password = ""
        cred.save(update_fields=["sender_email", "encrypted_password"])
        return self.success({"message": "Credentials removed", "has_credentials": False})
