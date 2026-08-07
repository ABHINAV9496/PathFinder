"""Profession pack loading + detection.

The implementation lives in the shared ``common.profession_packs`` module
(pure stdlib) so the Django app and the cover-letter engine use a single
source of truth for the block-pool composer. This module re-exports the
public API that Django code imports.
"""

from common.profession_packs import (  # noqa: F401
    KNOWN_PROFESSIONS,
    PACKS_ROOT,
    compose_cover_letter,
    detect_profession,
    features_for,
    get_pack,
    list_packs,
    pack_for_job,
    pack_vocabulary,
)

__all__ = [
    "KNOWN_PROFESSIONS",
    "PACKS_ROOT",
    "compose_cover_letter",
    "detect_profession",
    "features_for",
    "get_pack",
    "list_packs",
    "pack_for_job",
    "pack_vocabulary",
]
