from django.contrib.auth import get_user_model
from django.db import models


class UserProfile(models.Model):
    """Per-user profile driving cover-letter (and CV) generation.

    Mirrors the structure of ``profile.json`` / ``PROFILE`` so downstream
    generation code can consume a ``UserProfile`` as a plain dict via
    ``to_dict()``. The ``user`` link is optional so single-user dev mode can
    keep using the file-based profile instead.
    """

    user = models.OneToOneField(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="user_profile",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255, default="")
    phone = models.CharField(max_length=40, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    portfolio = models.URLField(blank=True, default="")
    github = models.CharField(max_length=255, blank=True, default="")
    linkedin = models.CharField(max_length=255, blank=True, default="")
    location = models.CharField(max_length=255, blank=True, default="")
    role = models.CharField(max_length=255, blank=True, default="")
    experience_years = models.IntegerField(default=0)
    open_to_relocation = models.BooleanField(default=False)
    availability = models.CharField(max_length=255, blank=True, default="")
    skills = models.JSONField(default=dict, blank=True)
    projects = models.JSONField(default=list, blank=True)
    experience = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        if self.name:
            return self.name
        if self.user_id:
            return self.user.username
        return f"UserProfile #{self.pk}"

    def to_dict(self) -> dict:
        """Return a plain dict shaped like the file-based PROFILE structure."""
        return {
            "name": self.name,
            "phone": self.phone,
            "email": self.email,
            "portfolio": self.portfolio,
            "github": self.github,
            "linkedin": self.linkedin,
            "location": self.location,
            "role": self.role,
            "experience_years": self.experience_years,
            "open_to_relocation": self.open_to_relocation,
            "availability": self.availability,
            "skills": self.skills,
            "projects": self.projects,
            "experience": self.experience,
        }
