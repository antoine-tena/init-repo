"""`init-repo nouveau` : génère un projet complet, l'installe et le publie au besoin."""

import os
import sys
from dataclasses import dataclass
from pathlib import Path

import copier
import yaml  # fourni par copier

from init_repo import github, installer
from init_repo.modele import TEMPLATE_REVISION, template_source
from init_repo.shell import InitRepoError, require_tools, run, step

INITIAL_COMMIT_MESSAGE = "chore: projet généré par init-repo"


@dataclass(frozen=True)
class NewProjectRequest:
    destination: Path
    answers: dict[str, object]
    template: str | None
    should_install: bool
    should_publish: bool


def create_project(request: NewProjectRequest) -> None:
    if request.destination.exists() and any(request.destination.iterdir()):
        raise InitRepoError(f"{request.destination} existe déjà et n'est pas vide")
    require_tools("git", "uv", "pnpm", *(["gh"] if request.should_publish else []))
    step("Génération depuis le modèle")
    copier.run_copy(
        template_source(request.template),
        request.destination,
        data=request.answers,
        vcs_ref=TEMPLATE_REVISION,
        unsafe=False,
        # Hors terminal (CI, agent), les questions sans réponse prennent leur valeur par défaut.
        defaults=not sys.stdin.isatty(),
    )
    root = request.destination.resolve()
    run(["git", "init", "-q", "-b", "main"], root)
    _lock_dependencies(root)
    if request.should_install:
        installer.install(root)
    _initial_commit(root)
    if request.should_publish:
        github.publish(root, _repository_name(root), _team_logins(root))


def _lock_dependencies(root: Path) -> None:
    step("Verrous des dépendances")
    run(["uv", "lock"], root / "backend")
    run(["pnpm", "install", "--lockfile-only"], root / "frontend")


def _initial_commit(root: Path) -> None:
    step("Premier commit sur main")
    run(["git", "add", "-A"], root)
    # Seul commit admis sur main : celui qui crée le dépôt ([PAS-SUR-MAIN]).
    commit_env = {**os.environ, "SKIP": "no-commit-to-branch"}
    run(["git", "commit", "-q", "-m", INITIAL_COMMIT_MESSAGE], root, env=commit_env)


def _read_answers(root: Path) -> dict[str, object]:
    loaded: dict[str, object] = yaml.safe_load((root / ".copier-answers.yml").read_text())
    return loaded


def _repository_name(root: Path) -> str:
    answers = _read_answers(root)
    return f"{answers['proprietaire']}/{answers['nom']}"


def _team_logins(root: Path) -> list[str]:
    team = _read_answers(root).get("equipe", [])
    return [str(login) for login in team] if isinstance(team, list) else []
