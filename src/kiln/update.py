"""`kiln update` : rapporte les évolutions du modèle, puis met à jour les dépendances."""

from pathlib import Path

import copier

from kiln.check import check_project
from kiln.shell import KilnError, capture, require_tools, run, step
from kiln.template import TEMPLATE_REVISION

PROTECTED_BRANCHES = ("main", "develop")


def update_project(root: Path, *, should_update_template: bool, should_update_deps: bool) -> None:
    require_tools("git", "uv", "pnpm")
    _check_working_branch(root)
    if should_update_template:
        step("Architecture : évolutions du modèle")
        copier.run_update(
            root,
            vcs_ref=TEMPLATE_REVISION,
            defaults=True,
            skip_answered=True,
            overwrite=True,
            conflict="inline",
            unsafe=False,
        )
    if should_update_deps:
        _update_dependencies(root)
    elif should_update_template:
        _sync_lockfiles(root)
    step("Fichiers modifiés")
    run(["git", "status", "--short"], root)
    print("\nRelire le diff (conflits marqués <<<<<<<), puis commiter et ouvrir une PR.")
    check_project(root)


def _check_working_branch(root: Path) -> None:
    if not (root / ".copier-answers.yml").exists():
        raise KilnError("pas de .copier-answers.yml : ce dépôt n'a pas été généré par kiln")
    branch = capture(["git", "branch", "--show-current"], root)
    if branch in PROTECTED_BRANCHES:
        raise KilnError(f"sur {branch} : créer d'abord une branche (ex. chore/kiln-update)")
    if capture(["git", "status", "--porcelain"], root):
        raise KilnError("arbre non propre : commiter ou mettre de côté les modifications")


def _sync_lockfiles(root: Path) -> None:
    """Le modèle a pu ajouter ou retirer des dépendances : verrous recalculés, sans montée."""
    step("Verrous des dépendances")
    run(["uv", "lock"], root / "backend")
    run(["uv", "sync"], root / "backend")
    run(["pnpm", "install"], root / "frontend")


def _update_dependencies(root: Path) -> None:
    step("Backend : dépendances")
    run(["uv", "lock", "--upgrade"], root / "backend")
    run(["uv", "sync"], root / "backend")
    step("Frontend : dépendances")
    run(["pnpm", "update", "--latest"], root / "frontend")
    run(["pnpm", "install"], root / "frontend")
    step("Crochets pre-commit")
    run(["uv", "tool", "run", "pre-commit", "autoupdate"], root)
