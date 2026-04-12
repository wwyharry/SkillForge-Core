from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
ENV_EXAMPLE = BACKEND_DIR / ".env.example"
ENV_FILE = BACKEND_DIR / ".env"


def ensure_backend_exists() -> None:
    if not BACKEND_DIR.exists():
        raise SystemExit(f"Backend directory not found: {BACKEND_DIR}")


def ensure_env_file() -> None:
    if ENV_FILE.exists() or not ENV_EXAMPLE.exists():
        return
    shutil.copyfile(ENV_EXAMPLE, ENV_FILE)
    print(f"Created {ENV_FILE.relative_to(ROOT)} from .env.example")


def run() -> int:
    ensure_backend_exists()
    ensure_env_file()

    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        os.environ.get("SKILLFORGE_HOST", "127.0.0.1"),
        "--port",
        os.environ.get("SKILLFORGE_PORT", "8000"),
        "--reload",
        "--reload-exclude",
        "exports/*",
    ]

    print("Starting SkillForge backend...")
    print("URL: http://127.0.0.1:8000")
    print("Press Ctrl+C to stop")

    try:
        completed = subprocess.run(command, cwd=BACKEND_DIR)
        return completed.returncode
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0


if __name__ == "__main__":
    raise SystemExit(run())
