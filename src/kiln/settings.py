"""`kiln set` : affiche ou change les paramètres d'un repo (équipe, frameworks, podman…).

Le repo est régénéré avec les nouvelles réponses, sans écraser les modifications locales : un
framework retiré emporte ses fichiers, un framework ajouté apporte les siens, puis les verrous,
les dépendances et la liste des règles non vérifiées suivent.
"""

import shutil
from pathlib import Path

import yaml  # fourni par copier

from kiln.check import check_project
from kiln.deps import lock_dependencies, sync_dependencies
from kiln.rules import write_unverified_rules
from kiln.shell import KilnError, require_tools, step
from kiln.stack import BACKEND_DIR, BUILD_ARTIFACTS, FRONTEND_DIR, Stack, load_stack, read_answers
from kiln.statusline import apply_statusline_settings
from kiln.update import apply_template, check_working_branch, report_changes

SETTABLE_KEYS = (
    "envergure",
    "nom",
    "titre",
    "description",
    "proprietaire",
    "equipe",
    "type_projet",
    "backend",
    "frontend",
    "podman",
    "boussole",
    "statusline_ci",
    "url_sante_prod",
)
LIST_KEYS = frozenset({"equipe"})


def show_settings(root: Path) -> None:
    answers = read_answers(root)
    width = max(len(key) for key in SETTABLE_KEYS)
    for key in SETTABLE_KEYS:
        if key in answers:
            print(f"{key:<{width}}  {answers[key]}")
    print("\nChanger : kiln set clé=valeur [clé=valeur…], sur une branche, arbre propre.")


def parse_assignments(assignments: list[str]) -> dict[str, object]:
    """`clé=valeur` lus comme du YAML (`true`, `[a, b]`) ; une équipe peut s'écrire `a,b`."""
    parsed: dict[str, object] = {}
    for assignment in assignments:
        key, separator, raw_value = assignment.partition("=")
        if not separator or key not in SETTABLE_KEYS:
            raise KilnError(
                f"« {assignment} » : attendu clé=valeur, clés : {', '.join(SETTABLE_KEYS)}"
            )
        if key in LIST_KEYS and not raw_value.startswith("["):
            parsed[key] = [login.strip() for login in raw_value.split(",") if login.strip()]
        else:
            parsed[key] = yaml.safe_load(raw_value) if raw_value else ""
    return parsed


def apply_settings(root: Path, assignments: list[str]) -> None:
    changes = parse_assignments(assignments)
    require_tools("git", "uv")
    check_working_branch(root)
    step("Paramètres : " + ", ".join(f"{key}={value}" for key, value in changes.items()))
    previous_stack = load_stack(root)
    apply_template(root, changes)
    stack = load_stack(root)
    remove_replaced_artifacts(root, previous_stack, stack)
    apply_statusline_settings(root)
    if stack.pnpm_dir is not None:
        require_tools("pnpm")
    lock_dependencies(root, stack)
    sync_dependencies(root, stack)
    write_unverified_rules(root, stack)
    report_changes(root)
    check_project(root)


def remove_replaced_artifacts(root: Path, previous: Stack, current: Stack) -> None:
    """Produits de build d'un framework remplacé (`.nuxt`, `node_modules`, `.venv`…), qui
    gêneraient les outils du nouveau ; jamais de données ni de `.env`."""
    replaced = [
        (BACKEND_DIR, previous.backend) if previous.backend != current.backend else None,
        (FRONTEND_DIR, previous.frontend) if previous.frontend != current.frontend else None,
    ]
    for directory, framework in filter(None, replaced):
        for artifact in BUILD_ARTIFACTS.get(framework, ()):
            path = root / directory / artifact
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()
            else:
                continue
            print(f"Retiré : {directory}/{artifact} ({framework})")
