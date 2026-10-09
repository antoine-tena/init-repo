"""`kiln new` : génère un projet complet, l'installe et le publie au besoin."""

import os
import sys
from dataclasses import dataclass
from pathlib import Path

import copier

from kiln import github, install
from kiln.config import load_config
from kiln.deps import lock_dependencies
from kiln.rules import write_unverified_rules
from kiln.shell import KilnError, require_tools, run, step
from kiln.stack import load_stack, read_answers
from kiln.template import TEMPLATE_REVISION, template_source

INITIAL_COMMIT_MESSAGE = "chore: projet généré par kiln"


@dataclass(frozen=True)
class NewProjectRequest:
    destination: Path
    answers: dict[str, object]
    template: str | None
    should_install: bool
    should_publish: bool


def create_project(request: NewProjectRequest) -> None:
    if request.destination.exists() and any(request.destination.iterdir()):
        raise KilnError(f"{request.destination} existe déjà et n'est pas vide")
    require_tools("git", "uv", *(["gh"] if request.should_publish else []))
    step("Génération depuis le modèle")
    copier.run_copy(
        template_source(request.template),
        request.destination,
        data=request.answers,
        user_defaults=_user_defaults(),
        vcs_ref=TEMPLATE_REVISION,
        unsafe=False,
        # Hors terminal (CI, agent), les questions sans réponse prennent leur valeur par défaut.
        defaults=not sys.stdin.isatty(),
    )
    root = request.destination.resolve()
    stack = load_stack(root)
    if stack.pnpm_dir is not None:
        require_tools("pnpm")
    run(["git", "init", "-q", "-b", "main"], root)
    lock_dependencies(root, stack)
    write_unverified_rules(root, stack)
    if request.should_install:
        install.install_project(root)
    _initial_commit(root)
    if request.should_publish:
        github.publish(root, _repository_name(root), _team_logins(root))


def _user_defaults() -> dict[str, object]:
    """Propriétaire et équipe par défaut, pris dans la configuration du poste."""
    config = load_config()
    defaults: dict[str, object] = {}
    if config.owner:
        defaults["proprietaire"] = config.owner
    if config.team:
        defaults["equipe"] = list(config.team)
    return defaults


def _initial_commit(root: Path) -> None:
    step("Premier commit sur main")
    run(["git", "add", "-A"], root)
    # Seul commit admis sur main : celui qui crée le dépôt ([PAS-SUR-MAIN]).
    commit_env = {**os.environ, "SKIP": "no-commit-to-branch"}
    run(["git", "commit", "-q", "-m", INITIAL_COMMIT_MESSAGE], root, env=commit_env)


def _repository_name(root: Path) -> str:
    answers = read_answers(root)
    return f"{answers['proprietaire']}/{answers['nom']}"


def _team_logins(root: Path) -> list[str]:
    team = read_answers(root).get("equipe", [])
    return [str(login) for login in team] if isinstance(team, list) else []
