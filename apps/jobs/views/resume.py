import os

from rest_framework import status

from apps.jobs.models import CredStore
from apps.jobs.views.base import BaseAPIView


class ProfileResume(BaseAPIView):
    def post(self, request):
        file = request.FILES.get("resume")
        if not file:
            return self.error("No file uploaded", status.HTTP_400_BAD_REQUEST)

        if not file.name.lower().endswith(".pdf"):
            return self.error("Only PDF files are accepted", status.HTTP_400_BAD_REQUEST)

        if file.size > 5 * 1024 * 1024:
            return self.error("File too large. Maximum size is 5MB", status.HTTP_400_BAD_REQUEST)

        cred = CredStore.load()

        if cred.resume_file:
            old_path = cred.resume_file.path
            cred.resume_file = ""
            cred.save(update_fields=["resume_file"])
            if os.path.exists(old_path):
                os.remove(old_path)

        cred.resume_file = file
        cred.resume_original_name = file.name
        cred.save(update_fields=["resume_file", "resume_original_name"])

        return self.success({
            "message": "Resume uploaded successfully",
            "filename": file.name,
            "size_kb": cred.resume_size_kb,
        })

    def delete(self, request):
        cred = CredStore.load()
        if not cred.resume_file:
            return self.error("No resume to delete", status.HTTP_404_NOT_FOUND)

        old_path = cred.resume_file.path
        cred.resume_file = ""
        cred.resume_original_name = ""
        cred.save(update_fields=["resume_file", "resume_original_name"])

        if os.path.exists(old_path):
            os.remove(old_path)

        return self.success({"message": "Resume deleted"})

    def get(self, request):
        cred = CredStore.load()
        if not cred.resume_file:
            return self.success({"has_resume": False})

        return self.success({
            "has_resume": True,
            "filename": cred.resume_original_name,
            "size_kb": cred.resume_size_kb,
        })
