"""`kiln install` : prépare un poste après le clone, relançable sans risque."""

import os
import secrets
import shutil
from pathlib import Path

from kiln.shell import require_tools, run, step

SECRET_KEY_VARIABLE = "DJANGO_SECRET_KEY"
SECRET_KEY_BYTES = 50


def install_project(root: Path) -> None:
    require_tools("git", "uv", "pnpm")
    _ensure_pre_commit()
    step("Backend : dépendances")
    run(["uv", "sync", "--locked"], root / "backend")
    step("Backend : .env")
    _ensure_env_file(root / "backend")
    step("Backend : migrations")
    run(["uv", "run", "python", "manage.py", "migrate"], root / "backend")
    step("Frontend : dépendances")
    run(["pnpm", "install", "--frozen-lockfile"], root / "frontend")
    step("Garde-fous git (pre-commit)")
    run(["pre-commit", "install"], root)
    print("\nPrêt. Lancer le backend et le frontend : kiln dev")


def _ensure_pre_commit() -> None:
    if shutil.which("pre-commit") is None:
        step("Installation de pre-commit")
        run(["uv", "tool", "install", "pre-commit"], Path.cwd())


def _ensure_env_file(backend_dir: Path) -> None:
    env_file = backend_dir / ".env"
    if env_file.exists():
        print("backend/.env existe déjà, conservé.")
        return
    template_lines = (backend_dir / ".env.example").read_text().splitlines()
    secret_key = secrets.token_urlsafe(SECRET_KEY_BYTES)
    env_lines = [
        f"{SECRET_KEY_VARIABLE}={secret_key}"
        if line.startswith(f"{SECRET_KEY_VARIABLE}=")
        else line
        for line in template_lines
    ]
    env_file.write_text("\n".join(env_lines) + "\n")
    os.chmod(env_file, 0o600)
    print("backend/.env créé avec une clé secrète locale.")
