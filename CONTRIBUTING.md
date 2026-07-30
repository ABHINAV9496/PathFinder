# Contributing to JobbLoot

Thanks for your interest in contributing! Here's how to get started.

## Getting Started

1. Fork the repository
2. Clone your fork
3. Create a feature branch: `git checkout -b feature/your-feature`
4. Make your changes
5. Test your changes (see below)
6. Commit and push
7. Open a Pull Request

## Setup

```bash
git clone https://github.com/YOUR_USERNAME/jobbloot.git
cd jobbloot
python setup.py
```

This installs all Python and frontend dependencies, creates `.env` and `config/profile.py` from templates, and runs migrations. Then edit `.env` and `config/profile.py` with your own values.

## Development

### Running the project

```bash
python manage.py run_all        # dashboard + scheduler
python manage.py runserver      # dashboard only
python manage.py run_fetcher    # single fetch cycle
```

### Code style

- Python 3.10+ (use `match` statements, type hints, f-strings)
- Follow existing patterns in the codebase
- No external dependencies beyond what's in `pyproject.toml`
- Use Django ORM — no raw SQL
- Keep templates clean — use `{% url %}` tags, never hardcode paths

### Testing

Before submitting a PR:

1. Run `python manage.py run_fetcher` — verify it fetches and matches without errors
2. Run `python manage.py runserver` — verify all dashboard pages load
3. Check the terminal output for any tracebacks or warnings

## Project Structure

```
config/        — User configuration (profile, queries, constants)
core/          — Business logic (fetch, match, apply, track)
dashboard/     — Django app (models, views, templates, management commands)
job_portal/    — Django project settings
static/        — CSS
```

## Adding a New Job Source

1. Create `core/new_source_fetcher.py`
2. Add a function that returns a list of dicts with these fields:
   ```python
   {
       "uid": "unique-id",
       "title": "Job Title",
       "company": "Company Name",
       "location": "City, State",
       "description": "HTML or plain text",
       "salary": "₹ X,00,000 - Y,00,000" or "",
       "apply_url": "https://...",
       "apply_email": "",  # leave empty, email_extractor fills it
       "source": "new_source",
       "posted": "2025-01-15",  # YYYY-MM-DD or ""
       "experience": "2-5 years",
   }
   ```
3. Import and call it from `core/fetcher.py`
4. Add queries to `config/queries.py` if needed

## Adding a New Skill Weight

Edit `config/profile.py`:

```python
SKILL_WEIGHTS = {
    "python": 20,
    "django": 20,
    "your_skill": 10,  # add here
    ...
}
```

## Reporting Issues

Open an issue on GitHub with:

- What you expected to happen
- What actually happened
- Steps to reproduce
- Your Python version and OS

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

**You must mention Dennis Joseph as the original author when using or forking this project.**
