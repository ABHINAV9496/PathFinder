"""Shared display filters (source / location / work type) for job listing views.

These filters are applied at display time only -- fetching still pulls jobs
from everywhere. Every listing endpoint accepts the same query params:

  ?source=cutshort,technopark          multi-select job board
  ?location=Remote,Kochi               multi-select location substring (OR'd)
  ?work_type=remote|hybrid|onsite      classified from the location text
"""

from django.db.models import Q

from apps.jobs.models import Job

WORK_TYPES = ("remote", "hybrid", "onsite")

_REMOTE_BOARD_HINTS = ("remoteok", "weworkremotely")


def split_multi(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _remote_q(*prefix: str) -> Q:
    """Location-OR-source 'remote' predicate, optionally on related fields."""
    location = "".join(prefix) + "location__icontains"
    source = "".join(prefix) + "source__icontains"
    return Q(**{location: "remote"}) | Q(**{source: "remoteok"}) | Q(**{source: "weworkremotely"})


def _hybrid_q(*prefix: str) -> Q:
    return Q(**{"".join(prefix) + "location__icontains": "hybrid"})


def _apply_work_type(qs, work_type: str, prefix: str = "") -> Q:
    if work_type == "remote":
        return qs.filter(_remote_q(prefix)).exclude(_hybrid_q(prefix))
    if work_type == "hybrid":
        return qs.filter(_hybrid_q(prefix))
    if work_type == "onsite":
        return qs.exclude(_remote_q(prefix)).exclude(_hybrid_q(prefix))
    return qs


def apply_job_filters(qs, params) -> Q:
    """Filter a Job-like queryset (needs ``source`` + ``location`` fields)."""
    sources = split_multi(params.get("source"))
    if sources:
        qs = qs.filter(source__in=sources)

    locations = split_multi(params.get("location"))
    if locations:
        location_q = Q()
        for loc in locations:
            location_q |= Q(location__icontains=loc)
        qs = qs.filter(location_q)

    work_type = params.get("work_type", "all")
    if work_type in WORK_TYPES:
        qs = _apply_work_type(qs, work_type)
    return qs


def apply_application_filters(qs, params) -> Q:
    """Filter an Application queryset via its related job."""
    sources = split_multi(params.get("source"))
    if sources:
        qs = qs.filter(job__source__in=sources)

    locations = split_multi(params.get("location"))
    if locations:
        location_q = Q()
        for loc in locations:
            location_q |= Q(job__location__icontains=loc)
        qs = qs.filter(location_q)

    work_type = params.get("work_type", "all")
    if work_type in WORK_TYPES:
        qs = _apply_work_type(qs, work_type, prefix="job__")
    return qs


def filter_options() -> dict:
    """Distinct sources/locations available in the DB, for filter dropdowns."""
    sources = list(
        Job.objects.exclude(source="")
        .values_list("source", flat=True)
        .distinct()
        .order_by("source")
    )
    locations = list(
        Job.objects.exclude(location="")
        .exclude(location__iexact="not specified")
        .values_list("location", flat=True)
        .distinct()
        .order_by("location")
    )
    return {
        "sources": sources,
        "locations": locations,
        "work_types": list(WORK_TYPES),
    }
