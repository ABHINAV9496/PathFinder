# Design: Any-Profession Dynamic JobbLoot — profession packs, neutral output, one-command onboarding

Date: 2026-08-07
Status: Approved (design presented to user; user approved with output-parity requirement)

## Goal

Any person from any field who clones JobbLoot gets the **same richness of output**
as the current Python developer does, with zero code edits:

- Profile is fully dynamic (skill categories, profession, country/currency/salary,
  experience, projects, resume).
- Cover letters are profession-aware (auto-detected), always grounded in the
  candidate's own data, full-length, ATS-friendly.
- Resumes/CVs stay section-complete and profession-neutral.
- Matcher/skill-gap/salary logic works for any field and any country.
- Setup is guided: `python setup.py` interactive wizard **and** an in-app
  onboarding wizard; legacy `config/profile.py` data is honored.

## Hard constraint: output parity

Whatever detail/grounding a Python dev gets today, every profession gets the same
or better. Enforced by a parity test suite (see Testing).

## 1. Unified profile (data sources)

- `apps/jobs/profile_manager.load_profile()` merges sources in order:
  `config/profile.py` `PROFILE` (legacy, if present) **then** `profile.json`
  (wins). Fixes the current gap where editing `config/profile.py` does not
  affect matching/letters. `save_profile()` still writes `profile.json`.
- De-tech `DEFAULT_PROFILE`: neutral starter skill categories (generic labels),
  no `+91`/INR/Kerala defaults, new optional `timezone` field.
- Neutral `DEFAULT_CATEGORY_WEIGHTS`/`DEFAULT_CATEGORY_GROUPS`: unknown
  categories get a neutral weight and default to `must_have` group.
- `config/profile.example.py` rewritten with a non-tech example profile.

## 2. First-run onboarding (both)

- **CLI wizard in `setup.py`**: interactive prompts build `profile.json`
  (pre-filled from `config/profile.py` if present) via `profile_manager` —
  no browser needed.
- **In-app wizard** (React): `/onboarding` route shown when profile is empty;
  steps: personal info → profession/location/country/currency/salary →
  dynamic skill categories (add/remove) → experience → projects → resume
  upload → looking-for/languages. Saves through existing profile API.
- Profile page gains: country/currency/min-salary/timezone fields, add/remove
  skill category, generic labels (drop GitHub/Tech-stack-specific placeholders).

## 3. Profession detection engine

- Root `profession_packs/*.json` (data files; no code to add a profession).
  Loader duplicated small in each service (resolves root via module parents).
- Detection scores profile role + `looking_for` + skills against each pack's
  `detect_keywords`; returns best pack id or `neutral`.

## 4. Cover letters

- `cover-letter-engine`: `classify.py` gains profession dimension; selector
  prefers profession pack templates when detected, else neutral pack.
- **Neutral pack** (rewritten `templates.py`): full-length letters framed on the
  candidate's own skills/projects/experience — no "API/backend/deployment"
  assumptions. Same seniority × tone breadth.
- **Profession packs**: `profession_packs/<field>.json` with detect keywords +
  fresher/mid/senior (and direct/story/formal) templates using `{placeholders}`.
  Shipped for major fields (healthcare, education, finance/accounting,
  IT/software, engineering, marketing/sales, hospitality, trades/construction,
  design, legal, admin/operations, science, retail, customer service).
- Context builder in `generator.py` unchanged in depth (matched skills, best
  project, resume evidence, emphasis lines, need hook, signature) — this is the
  machinery that guarantees parity.
- **AI path**: passes detected profession into the prompt; validation layer
  unchanged (salutation/signature/forbidden-skill/ungrounded-claim checks).
- **De-hardcode Django fallbacks**: `apps/jobs/cv_engine/cover_templates.py`
  becomes a neutral generator mirror (no Python prose); `applicant.py` legacy
  Python-only generator replaced by the neutral path; remove BACKEND/FRONTEND/
  DEVOPS/AI hardcoded sets.

## 5. Resume/CV polish

- `cv-engine/app/core/resume_pipeline.py`: generic section/category labels
  (title-case the category, no tech map); header links show only present
  Website/LinkedIn/GitHub; summary prose made profession-neutral (or
  profession-aware via pack) while keeping structure: header, summary, skills
  (reordered), experience, projects w/ links, education.

## 6. Matcher & skill gaps

- Skill-gap detection vocabulary = profile skills ∪ profession-pack keywords ∪
  small generic JD set (drop reliance on tech-only `COMMON_JD_SKILLS`).
- Salary comparisons in the profile's currency via a small static FX table
  (rough conversion), thresholds from profile/`.env` (not hardcoded INR).
- Role rejection driven by profile `excluded_roles` only; `REJECT_ROLE_KEYWORDS`
  no longer a universal blocker; `NORTH_INDIA_STATES` gate stays profile-flagged.

## 7. Setup on any system

- `setup.py`: venv resolution (done) + CLI profile wizard + `.env` with generic
  defaults. `TIME_ZONE`, `MIN_SALARY`, `MAX_SALARY`, SMTP host/port from `.env`.
- `.env.example` documents the new vars. README refreshed (stale
  `config/profile.py`-is-truth text corrected).

## 8. Testing (incl. output-parity guards)

- New: profession detection; pack load/render for a non-tech profession
  (e.g. nurse) with full-length structural assertions (paragraph count,
  project evidence, grounded resume lines when available, signature intact,
  no forbidden-skill claims); neutral-template regression; profile merge from
  `config/profile.py`; non-tech skill gaps; currency salary logic; onboarding
  wizard profile writes.
- Existing 158 tests stay green; cover-letter tests updated where template
  wording changed.

## Order of implementation

1. Unified profile loader (+ de-tech defaults, example file)
2. Profession detection engine + packs
3. Cover letters (neutral templates, packs, selector, Django fallbacks)
4. CV polish
5. Matcher/gaps/salary
6. Setup wizard + env/README
7. Frontend onboarding + profile fields
8. Tests + full-suite verification

## Files touched (planned)

- `apps/jobs/profile_manager.py`, `config/profile.example.py`,
  `apps/jobs/matcher.py`, `apps/jobs/applicant.py`,
  `apps/jobs/cv_engine/cover_templates.py`, `apps/jobs/profession_packs.py` (new)
- `profession_packs/*.json` (new), `cover-letter-engine/coverletter/core/`
  `templates.py`, `classify.py`, `generator.py`, `packs.py` (new),
  `cv-engine/app/core/resume_pipeline.py`
- `setup.py`, `config/settings/base.py`, `config/constants.py`, `.env.example`,
  `README.md`
- `frontend/src/pages/Profile.tsx`, `Onboarding.tsx` (new),
  `frontend/src/App.tsx`, routing
- Tests in `tests/`, `apps/jobs/tests/`, `cv-engine/tests/`,
  `cover-letter-engine/tests/`
