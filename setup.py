#!/usr/bin/env python3
"""
PathFinder -- one-command setup script.

Run:  python setup.py

What it does:
  1. Checks Python >= 3.10 and Node >= 18
  2. Installs uv if missing (pip install uv)
  3. Installs Python dependencies  (uv sync)
  4. Copies .env.example -> .env   (if .env missing) + generates secret key
  5. Copies config/profile.example.py -> config/profile.py  (if missing)
  6. Runs database migrations
  7. Installs frontend dependencies (npm install)
  8. Optionally starts both backend + frontend
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


def copy_profile() -> None:
    banner("Candidate profile")
    dst = ROOT / "config" / "profile.py"
    if dst.exists():
        info("config/profile.py already exists -- skipping")
        return
    src = ROOT / "config" / "profile.example.py"
    shutil.copy2(src, dst)
    ok("Copied profile.example.py -> config/profile.py")
    info("Edit config/profile.py with your real info")


def migrate() -> None:
    banner("Running database migrations")
    run([sys.executable, "manage.py", "migrate"])


def install_frontend_deps() -> None:
    banner("Installing frontend dependencies")
    run(["npm", "install"], cwd=ROOT / "frontend")


# -- main ---------------------------------------------------------------------

def main() -> None:
    banner("PathFinder -- Setup")
    print("  This script installs everything you need in one go.\n")

    check_python()
    check_node()
    ensure_uv()

    install_python_deps()
    copy_env()
    copy_profile()
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
      > Create one for "Mail" > "Other (Custom name)" > name it "PathFinder"

  Step 2 -- Edit your profile (config/profile.py)
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Open config/profile.py and fill in:

      Your name, email, phone number
      Your skills (backend, frontend, cloud, etc.)
      Your projects (name, description, tech stack)
      What jobs you are looking for

    The matcher uses this to score jobs against your profile.

  Step 3 -- Start the app
  ~~~~~~~~~~~~~~~~~~~~~~~
    > python manage.py run_all

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
    """Start Django backend + Vite frontend in parallel. Ctrl+C kills both."""
    banner("Starting PathFinder")
    print("  Backend  -> http://localhost:8000")
    print("  Frontend -> http://localhost:5173")
    print("  Press Ctrl+C to stop both.\n")

    backend = subprocess.Popen(
        [sys.executable, "manage.py", "runserver"],
        cwd=ROOT,
        shell=IS_WIN,
    )
    frontend = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=ROOT / "frontend",
        shell=IS_WIN,
    )

    def shutdown(sig, frame):
        for p in (frontend, backend):
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


if __name__ == "__main__":
    main()
