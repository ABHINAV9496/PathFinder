"""Local-only DuckDB data warehouse built from the JSONL data lake.

A small star schema is rebuilt idempotently each run: dimension tables are
``CREATE OR REPLACE``-ed from the lake, and ``fact_jobs`` keeps the latest
observation per ``job_uid`` (matching the fetch pipeline's dedup intent).
"""

import logging
from pathlib import Path

import duckdb
from django.conf import settings

logger = logging.getLogger(__name__)

_FACT_TABLES = (
    "dim_source",
    "dim_date",
    "dim_location",
    "dim_company",
    "fact_jobs",
    "fact_fetch_runs",
)

_LOCATION_SQL = """
SELECT location, country, work_type FROM (
    SELECT DISTINCT location,
           CASE WHEN location IS NULL OR lower(location) = '' THEN NULL
                WHEN contains(lower(location), 'remote') THEN 'remote'
                WHEN contains(lower(location), 'hybrid') THEN 'hybrid'
                ELSE 'onsite' END AS work_type,
           CASE
                WHEN lower(location) LIKE '%india%' THEN 'India'
                WHEN lower(location) LIKE '%united states%'
                     OR lower(location) LIKE '% usa%' THEN 'United States'
                WHEN lower(location) LIKE '%germany%' THEN 'Germany'
                WHEN lower(location) LIKE '%united kingdom%'
                     OR lower(location) LIKE '% uk%' THEN 'United Kingdom'
                ELSE NULL END AS country
    FROM staging_jobs
) WHERE location IS NOT NULL AND location <> ''
"""


def _schema_statements(lake_glob: str) -> list[str]:
    jobs = f"{lake_glob}/jobs/**/*.jsonl"
    manifests = f"{lake_glob}/manifests/**/*.json"
    return [
        f"""
        CREATE OR REPLACE TEMP TABLE staging_jobs AS
        SELECT uid AS job_uid, title, company, location, description, source,
               posted_date, salary, salary_display,
               TRY_CAST(posted_date AS TIMESTAMP) AS posted_ts,
               TRY_CAST(fetched_at AS TIMESTAMP) AS fetched_ts, batch_id
        FROM read_json_auto('{jobs}', format='newline_delimited', union_by_name=true)
        """,
        """
        CREATE OR REPLACE TABLE dim_source AS
        SELECT row_number() OVER (ORDER BY source_name) AS source_key, source_name
        FROM (SELECT DISTINCT source AS source_name FROM staging_jobs
              WHERE source IS NOT NULL AND source <> '')
        """,
        """
        CREATE OR REPLACE TABLE dim_company AS
        SELECT row_number() OVER (ORDER BY company) AS company_key, company
        FROM (SELECT DISTINCT company FROM staging_jobs
              WHERE company IS NOT NULL AND company <> '')
        """,
        f"""
        CREATE OR REPLACE TABLE dim_location AS
        SELECT row_number() OVER (ORDER BY location) AS location_key, location, country, work_type
        FROM ({_LOCATION_SQL})
        """,
        """
        CREATE OR REPLACE TABLE dim_date AS
        SELECT DISTINCT CAST(strftime(posted_ts, '%Y%m%d') AS INTEGER) AS date_key,
               CAST(posted_ts AS DATE) AS full_date,
               YEAR(posted_ts) AS year, MONTH(posted_ts) AS month, DAY(posted_ts) AS day
        FROM staging_jobs WHERE posted_ts IS NOT NULL
        """,
        """
        CREATE OR REPLACE TABLE fact_jobs AS
        SELECT s.job_uid, s.title,
               ds.source_key, dd.date_key, dl.location_key, dc.company_key,
               s.salary, s.salary_display, LENGTH(s.description) AS description_len,
               s.posted_date, s.fetched_ts AS fetched_at, s.batch_id
        FROM (SELECT *, row_number() OVER (PARTITION BY job_uid ORDER BY fetched_ts DESC) AS rn
              FROM staging_jobs) s
        LEFT JOIN dim_source ds ON ds.source_name = s.source
        LEFT JOIN dim_company dc ON dc.company = s.company
        LEFT JOIN dim_date dd ON dd.date_key = CAST(strftime(s.posted_ts, '%Y%m%d') AS INTEGER)
        LEFT JOIN dim_location dl ON dl.location = s.location
        WHERE s.rn = 1
        """,
        f"""
        CREATE OR REPLACE TABLE fact_fetch_runs AS
        SELECT m.batch_id, TRY_CAST(m.fetched_at AS TIMESTAMP) AS run_at,
               e.unnest.key AS source, CAST(e.unnest.value AS INTEGER) AS job_count
        FROM read_json_auto('{manifests}') m,
             LATERAL UNNEST(map_entries(CAST(m.by_source AS MAP(VARCHAR, INTEGER)))) AS e
        """,
    ]


def warehouse_path() -> Path:
    """Absolute path to the DuckDB warehouse file."""
    configured = getattr(settings, "WAREHOUSE_DB_PATH", None)
    if configured:
        return Path(configured)
    return Path(settings.BASE_DIR) / "warehouse" / "jobbloot.duckdb"


def build_warehouse() -> dict:
    """Rebuild the warehouse from the lake. Returns a summary dict, or
    ``{"error": ...}`` when the lake is disabled. Never raises."""
    lake = getattr(settings, "DATA_LAKE_DIR", None)
    if not lake:
        return {"error": "data lake disabled"}
    path = warehouse_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        lake_glob = Path(lake).as_posix()
        con = duckdb.connect(str(path))
        try:
            for statement in _schema_statements(lake_glob):
                con.execute(statement)
            counts = {
                table: con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                for table in _FACT_TABLES
            }
        finally:
            con.close()
        logger.info(f"Warehouse rebuilt: {path} ({counts})")
        return {"db_path": str(path), "counts": counts}
    except Exception as e:
        logger.error(f"Warehouse build failed: {e}")
        return {"error": str(e)}
