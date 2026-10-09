"""`kiln check` : rejoue les contrôles de la stack et la charte, sans s'arrêter au premier."""

import subprocess
from pathlib import Path

from kiln.shell import KilnError, step
from kiln.stack import load_stack


def run_checks(root: Path) -> list[str]:
    """Lance chaque contrôle et renvoie les libellés de ceux qui ont échoué."""
    failed_checks: list[str] = []
    for command in load_stack(root).check_commands():
        step(f"Vérification : {command.label}")
        completed = subprocess.run(list(command.argv), cwd=root / command.directory, check=False)
        if completed.returncode != 0:
            failed_checks.append(command.label)
    return failed_checks


def check_project(root: Path) -> None:
    """Lance chaque contrôle, puis échoue en listant ceux qui ont échoué."""
    failed_checks = run_checks(root)
    if failed_checks:
        raise KilnError(f"contrôles en échec : {', '.join(failed_checks)}")
    print("\nTous les contrôles passent.")
