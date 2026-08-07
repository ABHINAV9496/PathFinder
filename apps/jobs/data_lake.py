"""Local-only append-only data lake.

Raw fetched job dicts are landed as JSONL, partitioned by source + month;
batch manifests hold per-run statistics. Every write is a no-op when
``settings.DATA_LAKE_DIR`` is ``None`` (the test default).
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)


def _lake_root() -> Path | None:
    lake = getattr(settings, "DATA_LAKE_DIR", None)
    if not lake:
        return None
    return Path(lake)


def land_source_jobs(source: str, jobs: list[dict], batch_id: str) -> Path | None:
    """Append one batch's jobs for ``source`` under the month partition.

    Path: ``<lake>/jobs/<source>/<YYYY-MM>/<batch_id>.jsonl``.
    Returns the file path, or ``None`` when the lake is disabled or there are
    no jobs.
    """
    root = _lake_root()
    if root is None or not jobs:
        return None
    try:
        month = datetime.now().strftime("%Y-%m")
        out_dir = root / "jobs" / source / month
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{batch_id}.jsonl"
        fetched_at = datetime.now(timezone.utc).isoformat()
        with open(path, "w", encoding="utf-8") as fh:
            for job in jobs:
                line = dict(job)
                line["fetched_at"] = fetched_at
                line["batch_id"] = batch_id
                fh.write(json.dumps(line, ensure_ascii=False) + "\n")
        logger.debug(f"Lake: landed {len(jobs)} {source} jobs -> {path}")
        return path
    except Exception as e:
        logger.error(f"Lake: failed to land {source} batch {batch_id}: {e}")
        return None


def write_manifest(stats: dict, batch_id: str) -> Path | None:
    """Write one JSON manifest for a fetch run to ``<lake>/manifests/<YYYY-MM>/<batch_id>.json``."""
    root = _lake_root()
    if root is None:
        return None
    try:
        month = datetime.now().strftime("%Y-%m")
        out_dir = root / "manifests" / month
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{batch_id}.json"
        payload = {
            "batch_id": batch_id,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            **stats,
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        logger.debug(f"Lake: wrote manifest -> {path}")
        return path
    except Exception as e:
        logger.error(f"Lake: failed to write manifest {batch_id}: {e}")
        return None
