"""`kiln update` : rapporte les évolutions du modèle, puis met à jour les dépendances."""

from collections.abc import Mapping
from pathlib import Path

import copier
from copier.errors import UserMessageError

from kiln.check import check_project
from kiln.contract import generate_api_contract
from kiln.deps import lock_dependencies, sync_dependencies, update_dependencies
from kiln.rules import write_unverified_rules
from kiln.shell import KilnError, capture, require_tools, run, step
from kiln.stack import ANSWERS_FILE, load_stack
from kiln.template import DEFAULT_TEMPLATE_SOURCE, TEMPLATE_REVISION

PROTECTED_BRANCHES = ("main", "develop")
# Ancienne adresse du modèle (init-repo, renommé kiln) : GitHub redirige, mais on la remplace.
LEGACY_TEMPLATE_SOURCES = ("https://github.com/antoine-tena/init-repo.git",)


def update_project(
    root: Path,
    *,
    should_update_template: bool,
    should_update_deps: bool,
    allow_major: bool,
    should_check: bool = True,
) -> None:
    require_tools("git", "uv")
    check_working_branch(root)
    if should_update_template:
        step("Architecture : évolutions du modèle")
        apply_template(root)
    stack = load_stack(root)
    if should_update_deps:
        update_dependencies(root, stack, allow_major=allow_major)
    elif should_update_template:
        lock_dependencies(root, stack)
        sync_dependencies(root, stack)
    generate_api_contract(root, stack)
    write_unverified_rules(root, stack)
    report_changes(root)
    if should_check:
        check_project(root)


def apply_template(root: Path, answers: Mapping[str, object] | None = None) -> None:
    """Modèle réappliqué (révision la plus récente, réponses éventuellement changées), sans
    écraser les modifications locales : les conflits sont marqués dans les fichiers."""
    try:
        copier.run_update(
            root,
            data=dict(answers or {}),
            vcs_ref=TEMPLATE_REVISION,
            defaults=True,
            skip_answered=True,
            overwrite=True,
            conflict="inline",
            unsafe=False,
        )
    except UserMessageError as error:
        raise KilnError(f"mise à jour du modèle refusée : {error}") from error
    # Après Copier, qui exige un arbre propre et réécrit le fichier de réponses.
    replace_legacy_source(root)


def check_working_branch(root: Path) -> None:
    if not (root / ANSWERS_FILE).exists():
        raise KilnError(f"pas de {ANSWERS_FILE} : ce dépôt n'a pas été généré par kiln")
    branch = capture(["git", "branch", "--show-current"], root)
    if branch in PROTECTED_BRANCHES:
        raise KilnError(f"sur {branch} : créer d'abord une branche (ex. chore/kiln-update)")
    if capture(["git", "status", "--porcelain"], root):
        raise KilnError("arbre non propre : commiter ou mettre de côté les modifications")


def report_changes(root: Path) -> None:
    step("Fichiers modifiés")
    run(["git", "status", "--short"], root)
    print("\nRelire le diff (conflits marqués <<<<<<<), puis commiter et ouvrir une PR.")


def replace_legacy_source(root: Path) -> None:
    answers_path = root / ANSWERS_FILE
    text = answers_path.read_text()
    for legacy_source in LEGACY_TEMPLATE_SOURCES:
        text = text.replace(f"_src_path: {legacy_source}", f"_src_path: {DEFAULT_TEMPLATE_SOURCE}")
    answers_path.write_text(text)
