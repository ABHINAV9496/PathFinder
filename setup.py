#!/usr/bin/env python3
"""
JobbLoot -- one-command setup script.

Run:  python setup.py

What it does:
  1. Checks Python >= 3.10 and Node >= 18
  2. Installs uv if missing (pip install uv)
  3. Installs Python dependencies  (uv sync)
  4. Copies .env.example -> .env   (if .env missing) + generates secret key
  5. Creates profile.json from built-in defaults (if missing)
  6. Runs the interactive profile wizard (first run only)
  7. Runs database migrations
  8. Installs frontend dependencies (npm install)
  9. Optionally starts both backend + frontend

Flags:
  python setup.py --profile      Always run the interactive profile wizard
  python setup.py --no-profile   Never run the wizard

profile.json is the single source of truth for the job matcher and the
CV Engine. It is created automatically with safe defaults, so the app
boots with zero configuration. The wizard (or the /profile page) fills it
in with your real info -- any profession, any country.
"""

from __future__ import annotations

import secrets
import shutil
import signal
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
IS_WIN = sys.platform == "win32"


# -- helpers ------------------------------------------------------------------

def banner(msg: str) -> None:
    line = "=" * 60
    print(f"\n{line}\n  {msg}\n{line}")


def ok(text: str) -> None:
    print(f"  [OK] {text}")


def fail(text: str) -> None:
    print(f"  [FAIL] {text}")


def info(text: str) -> None:
    print(f"  --> {text}")


def run(cmd: list[str], cwd: Path | None = None, *, check: bool = True) -> int:
    """Run a command, stream output live, return exit code."""
    print(f"  > {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd or ROOT, shell=IS_WIN)
    if check and result.returncode != 0:
        print(f"\n  [FAIL] Command failed (exit {result.returncode}): {' '.join(cmd)}")
        sys.exit(result.returncode)
    return result.returncode


def version_tuple(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.split(".")[:2])


def venv_python() -> str:
    """Return the project venv interpreter, falling back to the current one."""
    path = ROOT / ".venv" / ("Scripts" if IS_WIN else "bin") / "python.exe"
    return str(path) if path.exists() else sys.executable


# -- checks -------------------------------------------------------------------

def check_python() -> None:
    v = version_tuple(sys.version)
    if v < (3, 10):
        fail(f"Python 3.10+ required -- you have {sys.version}")
        sys.exit(1)
    ok(f"Python {sys.version.split()[0]}")


def check_node() -> None:
    try:
        out = subprocess.check_output(
            ["node", "--version"], text=True, shell=IS_WIN,
        ).strip()
        v = version_tuple(out.lstrip("v"))
        if v < (18, 0):
            fail(f"Node.js 18+ required -- you have {out}")
            sys.exit(1)
        ok(f"Node.js {out}")
    except FileNotFoundError:
        fail("Node.js not found -- install it from https://nodejs.org")
        sys.exit(1)


def ensure_uv() -> None:
    if shutil.which("uv"):
        ok("uv is installed")
        return
    info("Installing uv via pip ...")
    run([sys.executable, "-m", "pip", "install", "uv", "--quiet"])
    if not shutil.which("uv"):
        fail("uv installation failed -- install manually: pip install uv")
        sys.exit(1)
    ok("uv installed")


# -- setup steps ---------------------------------------------------------------

def install_python_deps() -> None:
    banner("Installing Python dependencies")
    run(["uv", "sync", "--no-install-project"])
    info("Installing cv-engine dependencies...")
    run(["uv", "pip", "install", "-r", "requirements.txt"], cwd=ROOT / "cv-engine")
    info("Installing cover-letter-engine dependencies...")
    run(["uv", "pip", "install", "-r", "requirements.txt"], cwd=ROOT / "cover-letter-engine")


def copy_env() -> None:
    banner("Environment file")
    dst = ROOT / ".env"
    if dst.exists():
        info(".env already exists -- skipping")
        return
    src = ROOT / ".env.example"
    content = src.read_text(encoding="utf-8")

    secret = secrets.token_urlsafe(50)
    content = content.replace("your-secret-key-here", secret)

    dst.write_text(content, encoding="utf-8")
    ok("Copied .env.example -> .env")
    ok("Generated DJANGO_SECRET_KEY automatically")
    info("Edit .env to set EMAIL_USER / EMAIL_PASS for auto-apply")


def ensure_profile_json() -> bool:
    """Create profile.json with safe defaults when missing.

    Returns True when the file was created (a fresh install).
    """
    banner("Candidate profile")
    try:
        from apps.jobs.profile_manager import ensure_default_profile
    except Exception as e:
        fail(f"Could not create profile.json: {e}")
        return False
    if ensure_default_profile():
        ok("Created profile.json with default values")
        return True
    info("profile.json already exists -- skipping")
    return False


# -- profile wizard -------------------------------------------------------------

def _ask(prompt: str, current: str = "") -> str:
    """Prompt the user, keeping ``current`` on blank input."""
    suffix = f" [{current}]" if current else ""
    value = input(f"  {prompt}{suffix}: ").strip()
    return value or current


def _ask_int(prompt: str, current: int) -> int:
    value = _ask(prompt, str(current) if current else "")
    try:
        return int(value)
    except ValueError:
        return current


def _ask_list(prompt: str, current: list[str]) -> list[str]:
    value = _ask(prompt, ", ".join(current))
    if not value:
        return current
    return [item.strip() for item in value.split(",") if item.strip()]


def profile_wizard(force: bool = False) -> None:
    """Interactively build profile.json, pre-filled from legacy config.

    Runs through ``apps.jobs.profile_manager`` so legacy ``config/profile.py``
    values (if present) are honored and the result is saved to profile.json.
    Set ``force`` to re-run even when a profile is already configured.
    """
    banner("Profile wizard")
    try:
        from apps.jobs.profile_manager import load_profile, save_profile
        from common.profession_packs import KNOWN_PROFESSIONS
    except Exception as e:
        fail(f"Could not load profile module: {e}")
        return

    profile = load_profile()

    if not force and profile.get("name"):
        ok(f"Profile already configured for {profile['name']} -- skipping wizard")
        return

    print("  Press Enter on any question to keep the current/default value.")
    print("  Leave 'Full name' blank to abort and keep defaults.\n")

    print("  -- Personal info")
    name = _ask("Full name", profile.get("name", ""))
    if not name:
        info("No name entered -- keeping defaults, skipping wizard")
        return
    profile["name"] = name
    profile["email"] = _ask("Email", profile.get("email", ""))
    profile["phone"] = _ask("Phone", profile.get("phone", ""))
    profile["location"] = _ask("Location (city)", profile.get("location", ""))
    profile["country"] = _ask("Country", profile.get("country", ""))

    print("\n  -- Profession (any field -- not just software)")
    print("  Known professions:")
    for label in sorted({v for v in KNOWN_PROFESSIONS.values()}):
        print(f"    - {label}")
    profile["profession"] = _ask(
        "Profession (or type your own)", profile.get("profession", "")
    )
    profile["role"] = _ask("Current job title / role", profile.get("role", ""))
    profile["experience_years"] = _ask_int(
        "Years of experience", profile.get("experience_years", 0) or 0
    )

    print("\n  -- Salary / currency")
    currency = _ask("Currency (INR / USD / EUR / GBP)", profile.get("currency", "USD"))
    profile["currency"] = currency.upper() if currency else "USD"
    profile["min_salary"] = _ask_int(
        f"Minimum monthly salary in {profile['currency']} (0 = no minimum)",
        profile.get("min_salary", 0) or 0,
    )

    print("\n  -- Skills (grouped by category)")
    print("  Enter one category per line as  name: skill1, skill2")
    print("  e.g.  patient_care: wound care, medication administration")
    print("  Leave blank to keep the current skills.\n")
    skills = dict(profile.get("skills") or {})
    for cat, items in skills.items():
        print(f"    {cat}: {', '.join(items)}")
    line = input("  Add a skill category (blank to keep): ").strip()
    if line:
        cat, _, rest = line.partition(":")
        cat = cat.strip()
        if cat:
            skills[cat] = [s.strip() for s in rest.split(",") if s.strip()]
    profile["skills"] = skills

    print("\n  -- What you are looking for")
    profile["looking_for"] = _ask_list(
        "Roles you are looking for (comma-separated)",
        profile.get("looking_for", []) or [],
    )
    profile["languages"] = _ask_list(
        "Languages you speak (comma-separated)",
        profile.get("languages", []) or [],
    )

    print("\n  -- Projects (used as evidence in cover letters)")
    projects = list(profile.get("projects") or [])
    while True:
        pname = input("  Project name (blank to finish): ").strip()
        if not pname:
            break
        desc = input("  One-line description: ").strip()
        projects.append({"name": pname, "description": desc, "tech": []})
    profile["projects"] = projects

    if save_profile(profile):
        ok(f"Saved profile.json for {name}")
    else:
        fail("Could not save profile.json")


def migrate() -> None:
    banner("Running database migrations")
    run([venv_python(), "manage.py", "migrate"])


def install_frontend_deps() -> None:
    banner("Installing frontend dependencies")
    run(["npm", "install"], cwd=ROOT / "frontend")


# -- main ---------------------------------------------------------------------

def main() -> None:
    banner("JobbLoot -- Setup")
    print("  This script installs everything you need in one go.\n")
    print("  Flags:")
    print("    --profile       run the interactive profile wizard")
    print("    --no-profile    skip the wizard (default: run on first install)\n")

    force_profile = "--profile" in sys.argv[1:]
    skip_profile = "--no-profile" in sys.argv[1:]

    check_python()
    check_node()
    ensure_uv()

    install_python_deps()
    copy_env()
    profile_created = ensure_profile_json()
    if not skip_profile and (force_profile or profile_created):
        profile_wizard(force=force_profile)
    migrate()
    install_frontend_deps()

    banner("Setup complete!")
    print("""
  +------------------------------------------------------------------+
  |  WHAT TO DO NEXT                                                  |
  +------------------------------------------------------------------+

  Step 1 -- Edit your environment file (.env)
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Open .env and set these REQUIRED values:

      EMAIL_USER          = your-email@gmail.com
      EMAIL_PASS          = your-gmail-app-password (16 chars, no spaces)

    DJANGO_SECRET_KEY is already set (auto-generated).

    Optional -- for AI cover letters:
      AI_PROVIDER         = openai / groq / deepseek / gemini / openrouter
      AI_API_KEY          = your-api-key

    How to get a Gmail App Password:
      > Go to https://myaccount.google.com/apppasswords
      > Create one for "Mail" > "Other (Custom name)" > name it "JobbLoot"

  Step 2 -- Your profile (profile.json)
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    If you skipped the profile wizard, run it anytime with:
      > python setup.py --profile

    Or edit profile.json directly, or use the /profile page. Fill in:

      Your name, email, phone number
      Your profession + country + currency (INR / USD / EUR / GBP)
      Your minimum expected salary (min_salary)
      Your skills (patient_care, core, teaching, etc.)
      Your projects (name, description)
      What jobs you are looking for (looking_for)
      Roles to exclude (excluded_roles) or locations to skip (excluded_locations)

    The matcher uses this to score jobs against your profile, for any
    profession -- not just software development.

    Legacy note: an old config/profile.py is still honored as a fallback,
    but profile.json is the single source of truth.

  Step 3 -- Start the app
  ~~~~~~~~~~~~~~~~~~~~~~~
    > python setup.py (and answer "y")
        OR
    > python manage.py run_all  (Django only, no CV Engine)

    Then open http://localhost:5173 in your browser.

  Step 4 -- Use the dashboard
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~
    1. Go to http://localhost:5173/profile
    2. Upload your resume (PDF, max 5 MB)
    3. Under the AI tab, enter your LLM API key (optional)
    4. Go to Apply Queue > click "Batch Apply" to send applications
    5. Or go to Jobs > click any job > "Generate Cover Letter" > "Apply"

  +------------------------------------------------------------------+
  |  TIP: Run "python setup.py" again anytime -- it's safe and       |
  |  skips steps already done.                                        |
  +------------------------------------------------------------------+
""")

    answer = input("  Start the app now? (y/n): ").strip().lower()
    if answer == "y":
        run_app()
    else:
        print("\n  To start later, run:  python manage.py run_all\n")


def run_app() -> None:
    """Start all services in parallel; Ctrl+C kills everything."""
    banner("Starting JobbLoot")
    print("  Backend            -> http://localhost:8000")
    print("  CV Engine          -> http://localhost:8001")
    print("  Cover Letter Eng   -> http://localhost:8002")
    print("  Frontend           -> http://localhost:5173")
    print("  Press Ctrl+C to stop all.\n")

    backend = subprocess.Popen(
        [venv_python(), "manage.py", "runserver"],
        cwd=ROOT,
        shell=IS_WIN,
    )
    cv_engine = subprocess.Popen(
        [venv_python(), "-m", "uvicorn", "app.main:app",
         "--host", "0.0.0.0", "--port", "8001"],
        cwd=ROOT / "cv-engine",
        shell=IS_WIN,
    )
    cover_letter_engine = subprocess.Popen(
        [venv_python(), "-m", "uvicorn", "coverletter.main:app",
         "--host", "0.0.0.0", "--port", "8002"],
        cwd=ROOT / "cover-letter-engine",
        shell=IS_WIN,
    )
    frontend = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=ROOT / "frontend",
        shell=IS_WIN,
    )

    def shutdown(sig, frame):
        for p in (frontend, cover_letter_engine, cv_engine, backend):
            try:
                if IS_WIN:
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(p.pid)],
                        capture_output=True,
                    )
                else:
                    p.kill()
            except OSError:
                pass
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown)

    try:
        backend.wait()
    except KeyboardInterrupt:
        shutdown(None, None)
    frontend.kill()
    cv_engine.kill()


if __name__ == "__main__":
    main()
