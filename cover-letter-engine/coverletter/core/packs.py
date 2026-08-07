"""Engine-side access to the shared profession-pack composer.

The profession packs and their block-pool composer live in
``common.profession_packs`` (pure stdlib, also used by the Django app) so the
engine does not duplicate the detection/scoring logic. This shim simply makes
the repo root importable from the standalone service and re-exports the pack
API the generator and AI prompt use.
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from common.profession_packs import (  # noqa: E402
    compose_cover_letter,
    detect_profession,
    features_for,
    get_pack,
    list_packs,
    pack_for_job,
)

__all__ = [
    "compose_cover_letter",
    "detect_profession",
    "features_for",
    "get_pack",
    "list_packs",
    "pack_for_job",
]
