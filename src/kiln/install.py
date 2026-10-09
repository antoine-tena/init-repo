"""`kiln install` : prépare un poste après le clone, selon la stack ; relançable sans risque."""

import os
import secrets
import shutil
import subprocess
from pathlib import Path

from kiln.config import UserConfig, ensure_system, load_config
from kiln.shell import KilnError, require_tools, run, step
from kiln.stack import BACKEND_DIR, Stack, load_stack
from kiln.statusline import apply_statusline_settings

SECRET_KEY_VARIABLE = "DJANGO_SECRET_KEY"
SECRET_KEY_BYTES = 50
ENV_FILE_MODE = 0o600

# Conseils d'installation par système (jamais pip ni docker).
SYSTEM_HINTS: dict[str, dict[str, str]] = {
    "pnpm": {
        "linux": "corepack enable pnpm (Node 24, par mise ou le gestionnaire de paquets)",
        "wsl": "corepack enable pnpm (Node 24, par mise ou apt)",
        "macos": "brew install node@24 && corepack enable pnpm",
    },
    "podman": {
        "linux": "sudo apt install podman",
        "wsl": "sudo apt install podman (dans WSL, pas Podman Desktop sous Windows)",
        "macos": "brew install podman && podman machine init && podman machine start",
    },
}


def install_project(root: Path) -> None:
    config = ensure_system(load_config())
    stack = load_stack(root)
    _require_stack_tools(stack, config)
    _ensure_uv_tool("pre-commit", "pre-commit-uv")
    if stack.has_podman:
        _ensure_uv_tool("podman-compose")
    for directory in stack.python_dirs:
        step(f"{directory} : dépendances Python")
        run(["uv", "sync", "--locked"], root / directory)
    if stack.has_api:
        step("backend : .env")
        _ensure_env_file(root / BACKEND_DIR)
    if stack.backend == "django":
        step("backend : migrations")
        run(["uv", "run", "python", "manage.py", "migrate"], root / BACKEND_DIR)
    if stack.pnpm_dir is not None:
        step(f"{stack.pnpm_dir} : dépendances pnpm")
        run(["pnpm", "install", "--frozen-lockfile"], root / stack.pnpm_dir)
    step("Garde-fous git (pre-commit) et status line")
    run(["pre-commit", "install"], root)
    apply_statusline_settings(root)
    print("\nPrêt. Lancer le projet : kiln dev")


def _require_stack_tools(stack: Stack, config: UserConfig) -> None:
    require_tools("git", "uv")
    needed = (["pnpm"] if stack.pnpm_dir else []) + (["podman"] if stack.has_podman else [])
    missing = [tool for tool in needed if shutil.which(tool) is None]
    if missing:
        system = config.system or "linux"
        hints = "\n".join(f"  {tool} : {SYSTEM_HINTS[tool][system]}" for tool in missing)
        raise KilnError(f"outils manquants :\n{hints}")
    if stack.has_podman and config.system == "macos":
        _require_podman_machine()


def _require_podman_machine() -> None:
    completed = subprocess.run(["podman", "info"], capture_output=True, check=False)
    if completed.returncode != 0:
        raise KilnError("podman ne répond pas : podman machine start (ou podman machine init)")


def _ensure_uv_tool(tool: str, *extras: str) -> None:
    """Outil en ligne de commande installé par uv (jamais pip), avec ses greffons."""
    if shutil.which(tool) is not None and not extras:
        return
    step(f"Outil {tool} (uv tool)")
    with_options = [option for extra in extras for option in ("--with", extra)]
    run(["uv", "tool", "install", tool, *with_options], Path.cwd())


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
    os.chmod(env_file, ENV_FILE_MODE)
    print("backend/.env créé avec une clé secrète locale.")
