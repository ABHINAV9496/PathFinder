from django.urls import path

from apps.jobs.views import (
    JobList, JobDetail,
    ApplicationList,
    OverviewStats, SkillStats, CompanyStats, LocationStats,
    WebApplyList, MissingEmailsList, UserProfile,
    ApplyQueueList, ApplyToJob, BatchApply,
    ProfileResume, ProfileSecurity, ProfileAI,
    GenerateCoverLetter,
    GenerateTemplateCoverLetter,
)
from apps.jobs.views.jobs import JobFiltersOptions
from apps.jobs.views.fetcher import run_fetcher, fetcher_status
from apps.jobs.views.apply_queue import apply_progress
from apps.jobs.views.generate_cv import GenerateCV
from apps.jobs.views.ats_score import ATSScoreView
from apps.jobs.views.tailored_apply import TailoredApply

api_urlpatterns = [
    # Jobs
    path("jobs/", JobList.as_view(), name="api_job_list"),
    path("jobs/filters/", JobFiltersOptions.as_view(), name="api_job_filters"),
    path("jobs/<int:job_id>/", JobDetail.as_view(), name="api_job_detail"),

    # Applications
    path("applications/", ApplicationList.as_view(), name="api_application_list"),

    # Apply Queue
    path("apply-queue/", ApplyQueueList.as_view(), name="api_apply_queue"),
    path("apply-queue/batch/", BatchApply.as_view(), name="api_batch_apply"),
    path("apply-queue/progress/", apply_progress, name="api_apply_progress"),
    path("jobs/<int:job_id>/apply/", ApplyToJob.as_view(), name="api_apply_to_job"),
    path("jobs/<int:job_id>/tailored-apply/", TailoredApply.as_view(), name="api_tailored_apply"),
    path("jobs/<int:job_id>/generate-cv/", GenerateCV.as_view(), name="api_generate_cv"),
    path("jobs/<int:job_id>/ats-score/", ATSScoreView.as_view(), name="api_ats_score"),
    path("jobs/<int:job_id>/generate-cover-letter/", GenerateCoverLetter.as_view(), name="api_generate_cover_letter"),
    path("jobs/<int:job_id>/generate-template-cover-letter/", GenerateTemplateCoverLetter.as_view(), name="api_generate_template_cover_letter"),

    # Stats
    path("stats/overview/", OverviewStats.as_view(), name="api_overview"),
    path("stats/skills/", SkillStats.as_view(), name="api_skill_stats"),
    path("stats/companies/", CompanyStats.as_view(), name="api_company_stats"),
    path("stats/locations/", LocationStats.as_view(), name="api_location_stats"),

    # Profile
    path("profile/", UserProfile.as_view(), name="api_profile"),
    path("profile/resume/", ProfileResume.as_view(), name="api_profile_resume"),
    path("profile/security/", ProfileSecurity.as_view(), name="api_profile_security"),
    path("profile/ai/", ProfileAI.as_view(), name="api_profile_ai"),

    # Other
    path("web-apply/", WebApplyList.as_view(), name="api_web_apply"),
    path("missing-emails/", MissingEmailsList.as_view(), name="api_missing_emails"),

    # Actions
    path("fetcher/run/", run_fetcher, name="api_run_fetcher"),
    path("fetcher/status/", fetcher_status, name="api_fetcher_status"),
]
