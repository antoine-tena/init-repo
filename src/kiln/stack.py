"""La stack d'un projet (backend, frontend, podman), lue dans ses réponses Copier.

Tout ce qui dépend des frameworks choisis passe par ici : dossiers Python et pnpm, serveurs de
développement, contrôles. Les commandes (`install`, `dev`, `check`, `update`, `set`) ne
connaissent pas les frameworks, seulement une `Stack`.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import yaml  # fourni par copier

from kiln.shell import KilnError

ANSWERS_FILE = ".copier-answers.yml"
BACKEND_DIR = "backend"
FRONTEND_DIR = "frontend"

PYTHON_BACKENDS = frozenset({"django", "fastapi", "data"})
API_BACKENDS = frozenset({"django", "fastapi"})
PYTHON_FRONTENDS = frozenset({"streamlit", "dash"})
PNPM_FRONTENDS = frozenset({"nuxt", "next", "astro"})
NO_FRAMEWORK = "aucun"

# Projets générés avant le choix des frameworks : Django et Nuxt, seule stack d'alors.
LEGACY_BACKEND = "django"
LEGACY_FRONTEND = "nuxt"

BACKEND_DEV_COMMANDS: Mapping[str, tuple[str, ...]] = {
    "django": ("uv", "run", "python", "manage.py", "runserver"),
    "fastapi": ("uv", "run", "uvicorn", "app.main:app", "--reload", "--port", "8000"),
    "data": ("uv", "run", "marimo", "edit", "notebooks", "--port", "2718", "--headless"),
}
FRONTEND_DEV_COMMANDS: Mapping[str, tuple[str, ...]] = {
    "nuxt": ("pnpm", "dev"),
    "next": ("pnpm", "dev"),
    "astro": ("pnpm", "dev"),
    "streamlit": ("uv", "run", "streamlit", "run", "app.py"),
    "dash": ("uv", "run", "python", "app.py"),
}
PNPM_CHECK_SCRIPTS: Mapping[str, tuple[str, ...]] = {
    "nuxt": ("lint", "typecheck"),
    "next": ("lint", "typecheck"),
    "astro": ("typecheck",),
}
# Produits de build et d'installation d'un framework, retirés quand on en change (`kiln set`).
# Jamais de données ni de .env : seulement ce que l'outil régénère.
PYTHON_ARTIFACTS = (".venv", ".pytest_cache", ".mypy_cache", ".ruff_cache", "htmlcov", ".coverage")
BUILD_ARTIFACTS: Mapping[str, tuple[str, ...]] = {
    "django": PYTHON_ARTIFACTS,
    "fastapi": PYTHON_ARTIFACTS,
    "data": (*PYTHON_ARTIFACTS, "__marimo__"),
    "streamlit": PYTHON_ARTIFACTS,
    "dash": PYTHON_ARTIFACTS,
    "nuxt": ("node_modules", ".nuxt", ".output", ".data"),
    "next": ("node_modules", ".next", "next-env.d.ts", "tsconfig.tsbuildinfo"),
    "astro": ("node_modules", ".astro", "dist"),
}
PYTHON_CHECKS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ruff", ("uv", "run", "ruff", "check", ".")),
    ("format", ("uv", "run", "ruff", "format", "--check", ".")),
    ("mypy", ("uv", "run", "mypy", ".")),
    ("pytest", ("uv", "run", "pytest", "-q")),
)


@dataclass(frozen=True)
class Command:
    """Une commande à lancer dans un dossier du projet, avec son libellé."""

    label: str
    directory: str
    argv: tuple[str, ...]


@dataclass(frozen=True)
class Stack:
    backend: str
    frontend: str
    has_podman: bool

    @property
    def has_api(self) -> bool:
        return self.backend in API_BACKENDS

    @property
    def python_dirs(self) -> tuple[str, ...]:
        backend_dirs = (BACKEND_DIR,) if self.backend in PYTHON_BACKENDS else ()
        frontend_dirs = (FRONTEND_DIR,) if self.frontend in PYTHON_FRONTENDS else ()
        return backend_dirs + frontend_dirs

    @property
    def pnpm_dir(self) -> str | None:
        return FRONTEND_DIR if self.frontend in PNPM_FRONTENDS else None

    def dev_commands(self) -> list[Command]:
        commands = []
        if self.backend in BACKEND_DEV_COMMANDS:
            commands.append(Command(self.backend, BACKEND_DIR, BACKEND_DEV_COMMANDS[self.backend]))
        if self.frontend in FRONTEND_DEV_COMMANDS:
            argv = FRONTEND_DEV_COMMANDS[self.frontend]
            commands.append(Command(self.frontend, FRONTEND_DIR, argv))
        return commands

    def check_commands(self) -> list[Command]:
        commands = [
            Command(f"{directory} {label}", directory, argv)
            for directory in self.python_dirs
            for label, argv in PYTHON_CHECKS
        ]
        if self.pnpm_dir is not None:
            commands += [
                Command(f"{self.pnpm_dir} {script}", self.pnpm_dir, ("pnpm", script))
                for script in PNPM_CHECK_SCRIPTS[self.frontend]
            ]
        return [*commands, Command("charte", ".", ("charte",))]


def read_answers(root: Path) -> dict[str, object]:
    answers_path = root / ANSWERS_FILE
    if not answers_path.exists():
        raise KilnError(f"pas de {ANSWERS_FILE} : ce dépôt n'a pas été généré par kiln")
    loaded = yaml.safe_load(answers_path.read_text())
    return dict(loaded) if isinstance(loaded, dict) else {}


def stack_from_answers(answers: Mapping[str, object]) -> Stack:
    return Stack(
        backend=str(answers.get("backend", LEGACY_BACKEND)),
        frontend=str(answers.get("frontend", LEGACY_FRONTEND)),
        has_podman=answers.get("podman") is True,
    )


def load_stack(root: Path) -> Stack:
    return stack_from_answers(read_answers(root))
