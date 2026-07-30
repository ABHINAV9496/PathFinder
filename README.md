<p align="center">
  <img src="frontend/public/favicon.svg" alt="JobbLoot" width="80" />
</p>

<h1 align="center">JobbLoot</h1>

<p align="center">
  <strong>AI-powered job portal that fetches, matches, and applies to jobs — all on autopilot.</strong>
</p>

<p align="center">
  <a href="#-features">Features</a> ·
  <a href="#-tech-stack">Tech Stack</a> ·
  <a href="#-quick-start">Quick Start</a> ·
  <a href="#-full-setup-guide">Full Setup</a> ·
  <a href="#-ai-setup">AI Setup</a> ·
  <a href="#-usage">Usage</a> ·
  <a href="#-api-reference">API</a> ·
  <a href="#-contributing">Contributing</a> ·
  <a href="#-contributors">Contributors</a> ·
  <a href="#-legal--educational-disclaimer">Disclaimer</a> ·
  <a href="#-license">License</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Django-5.0+-092E20?style=flat-square&logo=django&logoColor=white" alt="Django" />
  <img src="https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black" alt="React" />
  <img src="https://img.shields.io/badge/TypeScript-6-3178C6?style=flat-square&logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="License" />
  <img src="https://img.shields.io/badge/PRs-Welcome-orange?style=flat-square" alt="PRs Welcome" />
</p>

---

JobbLoot is an automated job portal that scrapes Python developer jobs from **RSS feeds**, **Technopark**, and **Cutshort**, matches them against your profile using a weighted scoring engine, generates **AI-powered cover letters**, and sends applications via Gmail — all displayed on a modern React dashboard.

---

## Features

- **Multi-source job fetching** — RSS (3000+ jobs), Technopark (130+ jobs), Cutshort (300+ jobs) with parallel fetching (10/6 workers)
- **Smart matching engine** — weighted scoring: skills (60%), project relevance (20%), experience (15%), title (5%)
- **Template cover letters** — market-validated Problem-Solution format with 6 company-type templates (startup, enterprise, tech, fintech, AI, general)
- **AI cover letters** — provider-agnostic LLM integration (OpenAI, Groq, DeepSeek, Gemini, OpenRouter) with hallucination-proof validation
- **Auto-apply** — one-click apply from Job Detail page with generated cover letter + uploaded resume
- **Batch apply** — send applications to multiple jobs with one click via Gmail SMTP
- **Parallel enrichment** — email/salary enrichment runs with 8 workers for faster processing
- **Real-time progress** — fetcher progress bar with resume polling on mount
- **Profile management** — editable from the dashboard, takes effect on next fetch cycle
- **Skill gap analysis** — filters out jobs requiring >40% unknown skills
- **Experience + salary + location filtering** — respects your preferences
- **Coverage warnings** — shows which job requirements your cover letter misses
- **Modern SPA** — React 19 + TypeScript 6 + Vite 8 dashboard with Flat Design 2.0

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Django 5, Django REST Framework 3.17, Django Channels 4.3 |
| **Frontend** | React 19, TypeScript 6, Vite 8, React Router 7, Axios |
| **Charts** | Chart.js 4 |
| **AI / LLM** | OpenAI-compatible API (OpenAI, Groq, DeepSeek, Gemini, OpenRouter) |
| **HTTP Client** | httpx (HTTP/2) for scraping, Axios for frontend |
| **HTML Parsing** | BeautifulSoup 4, lxml |
| **Database** | SQLite3 (dev), PostgreSQL (prod) |
| **WebSocket** | Django Channels + Daphne (ASGI) |
| **Encryption** | Fernet (cryptography) for credential storage |
| **Package Manager** | uv (Python), npm (frontend) |
| **Linter** | Ruff (Python), Oxlint (TypeScript) |
| **Testing** | Pytest + pytest-django |

---

## Quick Start

> **Requirements:** Python 3.10+, Node.js 18+ ([uv](https://docs.astral.sh/uv/) auto-installed if missing)

```bash
# 1. Clone
git clone https://github.com/dennisjoseph2025/JobbLoot.git
cd JobbLoot

# 2. One-command setup (installs everything)
python setup.py

# 3. Edit your config files (required before first run)
#    .env                  — set EMAIL_USER, EMAIL_PASS, DJANGO_SECRET_KEY
#    config/profile.py    — fill in your real profile data

# 4. Run (development)
python manage.py runserver       # Terminal 1 — Django on :8000
cd frontend && npm run dev       # Terminal 2 — Vite on :5173
```

Open **http://localhost:5173** — the Vite dev server proxies API calls to Django automatically.

### What `setup.py` does

| Step | Action |
|------|--------|
| 1 | Checks Python >= 3.10 and Node.js >= 18 |
| 2 | Installs [uv](https://docs.astral.sh/uv/) if missing |
| 3 | Installs Python dependencies (`uv sync`) |
| 4 | Copies `.env.example` → `.env` (skips if exists) |
| 5 | Copies `config/profile.example.py` → `config/profile.py` (skips if exists) |
| 6 | Runs database migrations |
| 7 | Installs frontend dependencies (`npm install`) |

---

## Full Setup Guide

### 1. Clone the repository

```bash
git clone https://github.com/dennisjoseph2025/JobbLoot.git
cd JobbLoot
```

### 2. Install Python dependencies

Using **uv** (recommended):

```bash
uv sync
```

Or with **pip**:

```bash
python -m venv .venv
.venv\Scripts\activate           # Windows
# source .venv/bin/activate      # macOS/Linux
pip install -e ".[dev]"
```

### 3. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

### 4. Create environment file

```bash
copy .env.example .env           # Windows
# cp .env.example .env           # macOS/Linux
```

Edit `.env` with your values:

```env
# Required
DJANGO_SECRET_KEY=your-random-secret-key
EMAIL_USER=your-email@gmail.com
EMAIL_PASS=your-gmail-app-password

# Optional — resume (legacy, upload via dashboard instead)
# RESUME_PATH=resume/Your_Resume.pdf

# Optional — AI cover letter generation (configure via dashboard > Profile > AI)
# AI_PROVIDER=openai
# AI_API_BASE_URL=https://api.openai.com/v1
# AI_API_KEY=sk-your-api-key
# AI_MODEL=gpt-4o-mini

# Optional — Production database
# DB_ENGINE=django.db.backends.postgresql
# DB_NAME=jobbloot
# DB_USER=postgres
# DB_PASSWORD=your-db-password
# DB_HOST=localhost
# DB_PORT=5432
```

<details>
<summary><strong>Full environment variable reference</strong></summary>

| Variable | Default | Description |
|----------|---------|-------------|
| `DJANGO_SECRET_KEY` | `dev-insecure-key` | Django secret key — generate a real one for production |
| `EMAIL_USER` | — | Gmail address for sending applications |
| `EMAIL_PASS` | — | Gmail [App Password](https://myaccount.google.com/apppasswords) (16 chars, no spaces) |
| `RESUME_PATH` | `resume/Your_Resume.pdf` | **Legacy** — resume path fallback (prefer uploading via dashboard) |
| `AI_PROVIDER` | `openai` | LLM provider: `openai`, `groq`, `deepseek`, `gemini`, `openrouter` |
| `AI_API_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible API base URL |
| `AI_API_KEY` | — | API key for the LLM provider |
| `AI_MODEL` | `gpt-4o-mini` | Model to use for cover letter generation |
| `FETCH_INTERVAL_MINUTES` | `60` | How often the scheduler fetches new jobs |
| `EMAIL_SMTP_HOST` | `smtp.gmail.com` | SMTP server |
| `EMAIL_SMTP_PORT` | `465` | SMTP port |
| `DB_ENGINE` | `sqlite3` | Database backend (use `postgresql` for prod) |
| `DB_NAME` | `db.sqlite3` | Database name |
| `DB_USER` | — | Database user |
| `DB_PASSWORD` | — | Database password |
| `DB_HOST` | `localhost` | Database host |
| `DB_PORT` | `5432` | Database port |

</details>

### 5. Create your candidate profile

```bash
copy config\profile.example.py config\profile.py    # Windows
# cp config/profile.example.py config/profile.py    # macOS/Linux
```

Edit `config/profile.py` with your real info:

```python
CANDIDATE_PROFILE = {
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+91-9876543210",
    "experience_min": 2,
    "experience_max": 5,
    "skills": {
        "backend": ["python", "django", "fastapi", "postgresql"],
        "frontend": ["react", "javascript", "typescript"],
        "ai_llm": ["langchain", "openai api"],
        "cloud": ["aws", "docker"],
        "devops": ["github actions", "nginx"],
        "tools": ["git", "linux", "redis"],
    },
    "projects": [
        {
            "name": "ProjectX",
            "description": "Real-time analytics dashboard",
            "tech": ["django", "channels", "react", "postgresql"],
        }
    ],
    "looking_for": ["python developer", "django developer", "full stack developer"],
}
```

You can also edit your profile from the dashboard at **http://localhost:8000/profile/** — changes take effect on the next fetch cycle without restarting.

### 6. Upload your resume

Resumes are uploaded through the **dashboard** (not placed on disk manually):

1. Start the server (`python manage.py runserver`)
2. Open **http://localhost:8000/profile/**
3. Click the resume upload area and select your PDF
4. Max **5MB**, PDF only — old resume is automatically replaced on new upload

Uploaded resumes are stored in `media/resumes/` (Django `FileField`).

> **Legacy fallback:** The `RESUME_PATH` env var (`resume/Your_Resume.pdf`) is still used by the SMTP applicant as a fallback if no resume is uploaded via the dashboard. You can safely ignore it if you upload through the UI.

### 7. Run database migrations

```bash
python manage.py migrate
```

### 8. Start the application

**Development (two terminals):**

```bash
# Terminal 1 — Django backend
python manage.py runserver

# Terminal 2 — Vite frontend (with hot reload)
cd frontend
npm run dev
```

Then open **http://localhost:5173**.

**Production:**

```bash
# Build frontend
cd frontend
npm run build                    # Outputs to ../static/

# Run with Daphne (ASGI — supports WebSocket)
python manage.py runserver       # or use daphne directly
```

In production, Django serves the built frontend from `static/` directly — no separate Vite server needed.

---

## AI Setup

JobbLoot generates AI-powered cover letters using any **OpenAI-compatible** LLM provider. Configure it from the dashboard — no env vars needed.

### Dashboard configuration (recommended)

1. Open **http://localhost:8000/profile/**
2. Switch to the **AI** tab
3. Select your **provider** from the dropdown (presets auto-fill the base URL and model)
4. Enter your **API key** — encrypted with Fernet before saving to the database
5. Click **Save**

That's it. Open any job in the **Apply Queue** or **Jobs** page and click **Generate Cover Letter**.

### Provider presets

| Provider | Base URL | Default Model | Notes |
|----------|----------|---------------|-------|
| **OpenAI** | `api.openai.com/v1` | `gpt-4o-mini` | Best balance of quality and cost |
| **Groq** | `api.groq.com/openai/v1` | `llama-3.3-70b-versatile` | Fastest inference, free tier available |
| **DeepSeek** | `api.deepseek.com/v1` | `deepseek-chat` | Cheapest, great for batch jobs |
| **Gemini** | `generativelanguage.googleapis.com/v1beta/openai/` | `gemini-2.5-flash` | Google's free tier is generous |
| **OpenRouter** | `openrouter.ai/api/v1` | `auto` | Access to 100+ models via one key |

### How cover letter generation works

```
User clicks "Generate" on Job Detail page
  ↓
Backend sends system + user prompts to configured LLM
  ↓
Response parsed — think tags stripped (DeepSeek R1, QwQ, o1, o3, o4-mini)
  ↓
Deterministic validation layer:
  ├── Checks salutation ("Dear Hiring Manager" / "Dear [Company]")
  ├── Checks signature (candidate name, phone, email)
  ├── Blocks forbidden skills (skills NOT in your profile)
  ├── Blocks ungrounded claims (vague testing/monitoring/security claims)
  ├── Blocks project misattribution (projects only mentioned in YOUR profile)
  ├── Blocks acronym expansion ("REST" → "Representational State Transfer")
  └── Coverage warning if >30% of job requirements are unaddressed
  ↓
Letter saved to Application.cover_letter_text
  ↓
User reviews, edits if needed, then clicks "Apply" to send via Gmail
```

### Environment variable overrides

If you prefer env vars over the dashboard, add these to `.env`:

```env
AI_PROVIDER=openai
AI_API_BASE_URL=https://api.openai.com/v1
AI_API_KEY=sk-your-api-key
AI_MODEL=gpt-4o-mini
```

> **Note:** Dashboard settings take priority over env vars. If you've saved a config in the dashboard, the env vars are ignored.

### Model recommendations

| Use case | Recommended model | Why |
|----------|------------------|-----|
| **Daily batch (many jobs)** | `deepseek-chat` | ~$0.14/M tokens — cheapest option |
| **Quality over cost** | `gpt-4o-mini` | Best instruction following |
| **Free tier** | `gemini-2.5-flash` | 15 RPM free, good quality |
| **Fast iteration** | `llama-3.3-70b-versatile` (Groq) | Sub-second inference |

### Reasoning models

JobbLoot automatically detects reasoning models (DeepSeek R1, QwQ, o1, o3, o4-mini) and:
- Disables extended reasoning in the API payload
- Strips `` tags from the response
- Falls back to a stricter retry prompt if output is malformed

---

## Usage

### Run everything (recommended)

```bash
python manage.py run_all
```

Starts the Django server on `http://localhost:8000` and runs the fetch-match cycle every 60 minutes.

### Run components separately

```bash
# Fetch jobs once (no server)
python manage.py run_fetcher

# Run scheduler only (fetches every N minutes, no dashboard)
python manage.py run_scheduler

# Run dashboard only (no auto-fetching)
python manage.py runserver
```

### Frontend commands

```bash
cd frontend

npm run dev       # Start Vite dev server (hot reload)
npm run build     # Build for production
npm run lint      # Run Oxlint
npm run preview   # Preview production build
```

### How It Works

```
Fetch (RSS / Technopark / Cutshort — parallel fetching)
  ↓
RawJob (Data Lake — deduplicated by source + uid)
  ↓
Matcher (weighted scoring: skills 60%, projects 20%, experience 15%, title 5%)
  ↓
Job (Data Warehouse — matched jobs with scores)
  ↓
JobEvent (CDC — lifecycle events for every state change)
  ↓
DailyStats (Data Mart — aggregated daily metrics)

Auto-Apply → Template Cover Letter (Problem-Solution format) + Static Resume → Gmail SMTP → Application
Batch Apply → User selects jobs → Cover Letter (AI or template) → Gmail SMTP → Applications
```

---

## API Reference

All endpoints are under `/api/v1/`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/jobs/` | GET | List jobs (paginated, filterable by status/location/salary/search) |
| `/api/v1/jobs/<id>/` | GET | Job detail with match breakdown, skill gaps, cover letter |
| `/api/v1/jobs/<id>/apply/` | POST | Apply to a single job |
| `/api/v1/jobs/<id>/generate-cover-letter/` | POST | Generate AI cover letter |
| `/api/v1/jobs/<id>/generate-template-cover-letter/` | POST | Generate template cover letter (Problem-Solution format) |
| `/api/v1/applications/` | GET | List all applications |
| `/api/v1/apply-queue/` | GET | Jobs ready to apply (have email, not yet applied) |
| `/api/v1/apply-queue/batch/` | POST | Batch apply to selected jobs |
| `/api/v1/apply-queue/progress/` | GET | Batch apply progress |
| `/api/v1/stats/overview/` | GET | Dashboard overview stats |
| `/api/v1/stats/skills/` | GET | Skill frequency across jobs |
| `/api/v1/stats/companies/` | GET | Company job counts |
| `/api/v1/stats/locations/` | GET | Location distribution |
| `/api/v1/profile/` | GET/PUT | User profile |
| `/api/v1/profile/resume/` | GET/PUT | Resume upload |
| `/api/v1/profile/security/` | GET/PUT | Email/password settings |
| `/api/v1/profile/ai/` | GET/PUT | AI/LLM configuration |
| `/api/v1/web-apply/` | GET | Jobs with apply links (no email found) |
| `/api/v1/missing-emails/` | GET | Jobs missing company emails |
| `/api/v1/fetcher/run/` | POST | Trigger a fetch cycle |
| `/api/v1/fetcher/status/` | GET | Current fetcher status |

**WebSocket:**
| Endpoint | Description |
|----------|-------------|
| `ws/fetcher/progress/` | Real-time fetcher progress updates |

---

## Project Structure

```
JobbLoot/
├── apps/                       # Django applications
│   ├── core/                   # Shared infrastructure (pagination)
│   ├── dashboard/              # Legacy template views (still functional)
│   └── jobs/                   # Main app — models, API, business logic
│       ├── models/             # Job, Application, SkillLog, DailyStats, RawJob, JobEvent, CredStore, AIConfig
│       ├── views/              # 15 view modules (DRF API views)
│       ├── urls/               # API URL patterns
│       ├── serializers/        # DRF serializers
│       ├── fetchers/           # Technopark, Cutshort scrapers (parallel fetching)
│       ├── cv_engine/          # Cover letter template engine
│       │   └── cover_templates.py  # 6 market-validated cover letter templates
│       ├── management/commands/ # run_all, run_fetcher, run_scheduler
│       ├── matcher.py          # Weighted scoring engine
│       ├── applicant.py        # Cover letter gen + Gmail SMTP + auto-apply
│       ├── llm_client.py       # OpenAI-compatible LLM client
│       ├── services.py         # CRUD, parallel enrichment, salary extraction
│       └── consumers.py        # WebSocket consumer
├── config/                     # Django project settings
│   ├── settings/               # base.py, dev.py, prod.py, test.py
│   ├── queries.py              # Search queries per source
│   ├── constants.py            # Role rejection keywords, filters
│   ├── profile.example.py      # Template profile
│   ├── urls.py                 # Root URL configuration
│   ├── asgi.py                 # ASGI application
│   └── wsgi.py                 # WSGI application
├── common/                     # Shared utilities
│   └── utils.py                # Email detection, UID generation, HTML cleaning
├── frontend/                   # React SPA
│   ├── src/
│   │   ├── pages/              # 11 page components (Overview, Jobs, JobDetail, etc.)
│   │   ├── components/         # Reusable UI components
│   │   ├── lib/                # API client, utilities
│   │   ├── types/              # TypeScript type definitions
│   │   ├── App.tsx             # Router + layout
│   │   └── style.css           # Flat Design 2.0 theme
│   ├── public/                 # Static assets (favicon, icons)
│   ├── package.json            # Frontend dependencies
│   ├── vite.config.ts          # Vite config (proxy to Django)
│   └── tsconfig.json           # TypeScript config
├── tests/                      # Test suite
├── static/                     # Built frontend output (from Vite)
├── media/                      # User uploads (resumes, etc.)
│   └── resumes/                # Uploaded resume PDFs (auto-created)
├── .env.example                # Environment template
├── pyproject.toml              # Python project config
├── manage.py                   # Django management
├── CONTRIBUTING.md             # Contribution guidelines
├── LICENSE                     # MIT License
└── README.md                   # This file
```

---

## Dashboard Pages

| Page | Route | Description |
|------|-------|-------------|
| Overview | `/` | Stats cards, jobs-over-time chart, top skills chart |
| Jobs | `/jobs` | All matched jobs with search, filters, pagination |
| Job Detail | `/jobs/:id` | Full breakdown: match score, skill gaps, auto-apply, generate CV, generate template CL |
| Applications | `/applications` | Sent applications with status tracking |
| Apply Queue | `/apply-queue` | Jobs ready to apply (with email), batch apply |
| Web Apply | `/web-apply` | Jobs with apply links (no email found) |
| Missing Emails | `/missing-emails` | Jobs needing manual application |
| Skill Stats | `/stats/skills` | Skill frequency across all jobs |
| Company Stats | `/stats/companies` | Company job counts |
| Location Stats | `/stats/locations` | Job distribution by location |
| Profile | `/profile` | Edit profile, resume, security, AI settings |

---

## Configuration

### Match thresholds

Edit `config/settings/base.py`:

```python
MATCH_THRESHOLD_TRACK = 50      # Minimum % to track a job
MATCH_THRESHOLD_APPLY = 65      # Minimum % to include in apply queue
MIN_SALARY = 18000              # Minimum salary filter
MAX_SKILL_GAP_PCT = 40          # Skip jobs needing >40% unknown skills
MAX_SALARY_GAP_PCT = 50         # Skip if salary gap exceeds 50%
```

### Search queries

Edit `config/queries.py`:

```python
SEARCH_QUERIES = [
    "python developer",
    "django developer",
    "python full stack developer",
    # add more...
]
```

### Role rejection keywords

Edit `config/constants.py`:

```python
REJECT_ROLE_KEYWORDS = [
    "data engineer", "devops", "java", ".net",
    # add more...
]
```

---

## Security

- `.env`, `config/profile.py`, `profile.json`, `media/`, `db.sqlite3` — all gitignored
- Credentials stored with **Fernet encryption** (cryptography library)
- Django CSRF, X-Frame-Options, Content-Type nosniff, HttpOnly cookies enabled
- No raw SQL, no `eval`/`exec` — Django ORM throughout
- Production settings: HSTS, SSL redirect, secure cookies, proxy headers

---

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## Contributors

Thanks to everyone who has contributed to JobbLoot!

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/dennisjoseph2025">
        <img src="https://github.com/dennisjoseph2025.png" width="100" style="border-radius:50%" alt="Dennis Joseph" />
        <br />
        <sub><b>Dennis Joseph</b></sub>
      </a>
      <br />
      <sub>Creator & Author</sub>
    </td>
    <td align="center">
      <a href="https://github.com/nkswalih">
        <img src="https://github.com/nkswalih.png" width="100" style="border-radius:50%" alt="Mohammed Swalih N K" />
        <br />
        <sub><b>Mohammed Swalih N K</b></sub>
      </a>
      <br />
      <sub>Contributor</sub>
    </td>
  </tr>
</table>

---

## Legal & Educational Disclaimer

This project is provided **as-is** for **educational and personal use** purposes.

- **No warranty.** This software is provided without warranty of any kind, express or implied. The authors and contributors are not responsible for any damages, data loss, or legal consequences arising from the use of this software.
- **User responsibility.** You are solely responsible for how you use this tool. By using JobbLoot, you acknowledge that:
  - Automated job applications may violate the Terms of Service of certain job platforms. **Use at your own risk** and always respect platform-specific rules.
  - Sending automated emails via Gmail is subject to [Google's automation policies](https://support.google.com/mail/answer/6579). Excessive sending may result in account suspension.
  - You must comply with all applicable laws and regulations, including data protection laws (GDPR, CCPA, etc.) when handling personal or third-party data.
- **AI-generated content.** Cover letters generated by LLMs may contain inaccuracies. Always review and edit before sending. The hallucination validation layer reduces but does not eliminate this risk.
- **No affiliation.** This project is not affiliated with, endorsed by, or connected to any job platform (Technopark, Cutshort, etc.), email provider (Google/Gmail), or AI service (OpenAI, Groq, etc.) referenced in this documentation.
- **Educational purpose.** This project demonstrates a full-stack architecture combining Django REST Framework, React, WebSockets, and LLM integration. It is intended as a learning resource and personal productivity tool, not a commercial service.

---

## License

MIT License — Copyright (c) 2025 Dennis Joseph

See [LICENSE](LICENSE) for full terms. If you use or distribute this software, you must mention the original author.

---

<p align="center">
  Built with Django + React + AI
  <br />
  <sub>Star this repo if you find it useful!</sub>
</p>
