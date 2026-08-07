# JobbLoot: New Job Sources + Local Data Lake & Warehouse — Design

**Date:** 2026-08-07
**Status:** Approved (subject to spec review)
**Scope:** Task 2 of the "any profession" rollout — expand job sources (world + India), harden cross-source dedup, and add a local-only data lake + data warehouse for retention and analytics.

## Context

JobbLoot currently fetches from four source groups:

- **rss** — dynamic RSS feeds from `rssjobs.app` (aggregates LinkedIn / Glassdoor / Indeed for a keyword + location).
- **cutshort** — India startup board, HTML/`__NEXT_DATA__` scraping.
- **jobdrop** — `jobdrop` library scraping six HTTP sources (adzuna, jooble, findwork, the_muse, remoteok, weworkremotely) per profile query.
- **technopark** — Kerala-specific; only enabled when the profile is Kerala-based.

Two pre-existing problems drive this work:

1. **The RSS source is dead.** `apps/jobs/fetchers/__init__.py:172` references the undefined name `SEARCH_QUERIES`, so `fetch_rss_jobs()` raises `NameError` every cycle. `_safe_fetch()` swallows it and the source silently contributes 0 jobs. Since `rssjobs.app` is the primary *India* feed (verified live, returning fresh Kerala/India postings from LinkedIn + Glassdoor), reviving it is the highest-value India fix.
2. **Cross-source dedup is weak.** `fetch_all_jobs()` dedups by an exact `uid` hash (`make_uid(title, company, location)`), but sources compute it inconsistently (rss/cutshort/technopark omit location; jobdrop includes it with board-specific strings). The same remote job seen from two boards can survive as two rows. The fuzzy `deduplicate_jobs()`/`jobs_are_same()` helpers already exist in `common/utils.py` but are unused.

New requirements from the user:

- Add new **free, no-login** job sources with **equal-or-faster** fetching.
- More coverage **from around the world** and **more India** jobs.
- **No duplicates** across sources.
- Organize fetched data in a **data lake + data warehouse**.
- **Local-only; no hosting of any kind.**

## Decisions

| Topic | Decision |
|---|---|
| World/remote sources | Add RemoteOK, Remotive, Jobicy — all verified live 2026-08-07, free, no auth, single-request JSON. |
| India sources | Fix the RSS `NameError` bug (revives `rssjobs.app`) and widen its India location coverage to metro cities. Direct Indeed RSS returns 403; Naukri was previously pruned from jobdrop (Windows/CAPTCHA) — both skipped. Adzuna India skipped (needs a free API key; user chose login/key-free). |
| Dedup | Remove `remoteok` from jobdrop sub-sources; normalize remote-board locations before `make_uid`; run the existing fuzzy `deduplicate_jobs()` as a company-bucketed second pass reporting `dups_removed`. |
| Data lake | Append-only JSONL files on disk (gitignored), partitioned by source + month. |
| Data warehouse | Embedded DuckDB file (gitignored) with a star schema, built by SQL over the lake's JSONL. Local-only. |
| New dependency | `duckdb` (only new dep). |

## Architecture

### 1. New fetchers (world/remote)

Three new modules under `apps/jobs/fetchers/`, mirroring the `cutshort.py` pattern (httpx client + pure parse function + `fetch_<source>_jobs()`). Each is a single GET; they register in `fetch_all_jobs()`'s existing `ThreadPoolExecutor(max_workers=8)` so they run in parallel and **do not increase wall time**.

| Source | Module | Endpoint | Source string | Parse notes |
|---|---|---|---|---|
| RemoteOK | `remoteok.py` | `https://remoteok.com/api` | `remoteok` | JSON array; skip element 0 (legal notice); requires a `User-Agent` header. Fields: `id`, `date`, `company`, `position`, `tags`, `description` (HTML), `location`, `apply_url`, `salary_min`, `salary_max`. Empty/missing location → `Remote`. Salary from `salary_min`/`salary_max` (annual, USD). |
| Remotive | `remotive.py` | `https://remotive.com/api/remote-jobs` | `remotive` | JSON object `{ "job-count": N, "jobs": [...] }`. Fields: `id`, `url`, `title`, `company_name`, `category`, `tags`, `job_type`, `publication_date`, `candidate_required_location`, `salary` (free text), `description` (HTML). Location mapping: `Worldwide`/`Anywhere` → `Remote`; else the candidate-required location. Salary via `_extract_salary_from_text` on title+description (feed salary is prose). |
| Jobicy | `jobicy.py` | `https://jobicy.com/api/v2/remote-jobs?count=100` | `jobicy` | JSON object `{ "jobs": [...] }`. Fields: `id`, `url`, `jobTitle`, `companyName`, `jobIndustry`, `jobType`, `jobGeo`, `jobLevel`, `jobExcerpt`, `jobDescription` (HTML), `pubDate`, `salaryMin`, `salaryMax`, `salaryCurrency`, `salaryPeriod`. **Structured salary** → build `salary` + `salary_display` (period `yearly` default; convert `hourly`/`monthly` to annual). Location = `jobGeo`. |

Common parse contract (each returned job dict):

```
uid, title, company, location, description, posted_date, source,
apply_email (""), apply_url, job_url, search_query, salary, salary_display, full_text
```

- `uid` for remote boards is built via `make_uid(title, company, normalized_location)` where `normalized_location` collapses `worldwide`/`anywhere`/empty/emoji-remote to `remote` (see §3).
- `description` converted with `html_to_markdown` (already used by cutshort).
- `posted_date` preserved as the board's ISO/RFC string (matches existing fetchers' string field).

### 2. India coverage

**Fix the RSS bug.** In `apps/jobs/fetchers/__init__.py`, replace the undefined `SEARCH_QUERIES` at line 172 with the local `queries` variable already computed by `fetch_rss_jobs()`. This revives all `rssjobs.app` queries — including the profile-driven `kerala`/`india`/`remote` feeds.

**Widen India locations.** In `apps/jobs/query_builder.py`:

- Add `INDIAN_METROS = ["bangalore", "chennai", "hyderabad", "pune", "mumbai", "delhi", "kochi", "trivandrum", "kozhikode"]`.
- In `get_search_queries()`, when the profile is India-based (country contains `india` or location tokens include an Indian city/state), append the metro cities to `locations` before generating role×location queries, capped so `len(locations) * len(roles) <= MAX_RSS_QUERIES` (existing cap logic). Remote boards are unaffected.
- If the profile is not India-based, do not add metros (existing behavior preserved).

### 3. Dedup hardening

1. **Remove `remoteok` from jobdrop.** In `apps/jobs/query_builder.py`, delete `"remoteok"` from `BROWSER_FREE_JOBDROP_SOURCES`. The direct RemoteOK API returns the same board fresher, eliminating the largest cross-source overlap. `weworkremotely` stays (no dedicated fetcher; distinct board).
2. **Normalized remote locations for `uid`.** Add a shared helper (e.g. in `apps/jobs/fetchers/common.py` or `common/utils.py`) `normalize_remote_location(loc) -> str` that maps remote synonyms (`worldwide`, `anywhere`, `remote`, emoji flags/globe, empty) to `remote`. New remote-board fetchers use it when computing `uid`; location string kept as the board provided for display.
3. **Fuzzy second pass.** In `fetch_all_jobs()`, after exact-uid dedup, run the existing `deduplicate_jobs()` from `common.utils` **bucketed by normalized company** (to avoid O(n²) across the whole list; ~thousands of jobs from Remotive). Record `stats["dups_removed"] = before - after` (the count of duplicates merged). `run_fetcher.py` already prints `dups_removed` when present (lines 38–39).

### 4. Data lake (local-only)

New module `apps/jobs/data_lake.py`:

- `land_source_jobs(source: str, jobs: list[dict], batch_id: str) -> Path | None` — appends each job dict as one JSON line to `data_lake/jobs/<source>/<YYYY-MM>/<batch_id>.jsonl`, creating dirs as needed.
- `write_manifest(stats: dict, batch_id: str) -> Path | None` — writes `data_lake/manifests/<YYYY-MM>/<batch_id>.json` with batch metadata (timestamp, `by_source`, `failed`, `final`, `dups_removed`).
- Both are no-ops when `settings.DATA_LAKE_DIR` is `None`.

Landing happens **inside `fetch_all_jobs()`** so every fetch is captured regardless of which command drives it:

- Per source, immediately after a future completes, land that source's jobs (pre-global-dedup — the lake is the raw layer).
- After all sources, write the manifest.

Settings (`config/settings/base.py`):

- `DATA_LAKE_DIR = os.path.join(BASE_DIR, "data_lake")` (production/dev default).
- `config/settings/test.py`: `DATA_LAKE_DIR = None` (lake off in the default test run; warehouse/lake tests override to a tmp dir).

`.gitignore`: add `data_lake/` and `warehouse/`.

### 5. Data warehouse (local-only, DuckDB)

New module `apps/jobs/warehouse.py`:

- `build_warehouse() -> dict` — opens (or creates) `settings.WAREHOUSE_DB_PATH` (default `BASE_DIR/warehouse/jobbloot.duckdb`), creates the star schema, and upserts from the lake.

Star schema (built with DuckDB SQL over `read_json_auto('data_lake/jobs/**/*.jsonl')` and `read_json_auto('data_lake/manifests/**/*.json')`):

- `dim_source(source_key INTEGER PK, source_name TEXT UNIQUE)`
- `dim_date(date_key INTEGER PK, full_date DATE, year INTEGER, month INTEGER, day INTEGER)` — derived from `fetched_at`/`posted_date`
- `dim_location(location_key INTEGER PK, location TEXT, country TEXT, work_type TEXT)` — `work_type` derived from location text (remote → `remote`, hybrid → `hybrid`, else `onsite`), mirroring the display-time filter logic
- `dim_company(company_key INTEGER PK, company TEXT)`
- `fact_jobs(job_uid TEXT PRIMARY KEY, title TEXT, source_key, date_key, location_key, company_key, salary INTEGER, salary_display TEXT, description_len INTEGER, posted_date TEXT, apply_url TEXT, fetched_at TIMESTAMP, batch_id TEXT)` — `INSERT OR REPLACE` so the latest observation of a job wins (idempotent rebuilds).
- `fact_fetch_runs(batch_id TEXT PRIMARY KEY, run_at TIMESTAMP, source TEXT, count INTEGER)` — one row per (batch, source) from the manifests.

Management commands (`apps/jobs/management/commands/`):

- `build_warehouse` — calls `build_warehouse()`, prints table row counts.
- `warehouse_report` — preset analytics queries: top sources by job count, monthly job volume, salary distribution by work type, top companies, matched-jobs trend. Prints to stdout.

`run_fetcher.py`: after `bulk_save_jobs()` and stats update, call `build_warehouse()` (guarded so a warehouse failure never fails the fetch cycle) and print its summary.

Dependency: add `"duckdb"` to `pyproject.toml` `[project].dependencies` and install into the project venv. DuckDB reads the JSONL lake directly — no extra ETL service.

### 6. Files touched

| File | Change |
|---|---|
| `apps/jobs/fetchers/__init__.py` | Fix `SEARCH_QUERIES`→`queries`; register 3 new fetchers; land lake per source + manifest; fuzzy dedup pass + `dups_removed` stat |
| `apps/jobs/fetchers/remoteok.py` | New |
| `apps/jobs/fetchers/remotive.py` | New |
| `apps/jobs/fetchers/jobicy.py` | New |
| `apps/jobs/query_builder.py` | Remove `remoteok` from jobdrop sources; add `INDIAN_METROS` + metro expansion in `get_search_queries()` |
| `apps/jobs/data_lake.py` | New |
| `apps/jobs/warehouse.py` | New |
| `apps/jobs/management/commands/build_warehouse.py` | New |
| `apps/jobs/management/commands/warehouse_report.py` | New |
| `apps/jobs/management/commands/run_fetcher.py` | Auto-build warehouse after cycle |
| `config/settings/base.py` | `DATA_LAKE_DIR`, `WAREHOUSE_DB_PATH` |
| `config/settings/test.py` | `DATA_LAKE_DIR = None` |
| `pyproject.toml` | `duckdb` dependency |
| `.gitignore` | `data_lake/`, `warehouse/` |
| `tests/test_new_sources.py` (force-added; `tests/` is gitignored) | Parser + registration tests |
| `tests/test_dedup.py` (force-added) | Dedup tests |
| `tests/test_lake_warehouse.py` (force-added) | Lake + warehouse tests |

## Error handling

- Every new fetcher returns `[]` on any exception (wrapped by the existing `_safe_fetch` at registration). Per-request `httpx` timeout 20s (matches cutshort).
- Lake landing failures are logged and never raise into the fetch cycle (worst case: batch not captured; warehouse rebuild from older batches still works).
- Warehouse build failures are logged; `run_fetcher` continues regardless.
- DuckDB upserts are idempotent (`INSERT OR REPLACE`), so a partial/rerun build converges.

## Testing

- **Parser tests:** each new fetcher parses an inline sample payload (small realistic JSON) into the expected job-dict shape; salary/location/uid-norm edge cases.
- **RSS fix:** `fetch_rss_jobs()` no longer raises `NameError` (monkeypatched `get_search_queries` + httpx GET returning a small rssjobs-style RSS sample); India metro expansion returns expected queries.
- **Dedup:** same job from RemoteOK + Remotive with different location strings produces one row; `remoteok` no longer in jobdrop sources; `dups_removed` stat populated; fuzzy pass merges a near-duplicate (title/company variant).
- **Lake:** `land_source_jobs`/`write_manifest` write valid JSONL + manifest under a tmp `DATA_LAKE_DIR`; no-op when `DATA_LAKE_DIR=None`.
- **Warehouse:** `build_warehouse()` over a tmp lake creates the star schema and the analytics queries return the expected rows; rebuild is idempotent.
- Full suite remains green (currently 191 passing).

## Verification

1. `.venv\Scripts\python.exe -m pytest -q` — all tests pass.
2. `.venv\Scripts\python.exe -m ruff check <changed files>` — clean for files authored in this task.
3. `.venv\Scripts\python.exe manage.py run_fetcher` — confirm new sources contribute, RSS contributes again, `dups_removed` prints, wall time does not regress, and the warehouse builds.
4. `.venv\Scripts\python.exe manage.py warehouse_report` — shows non-empty analytics.
