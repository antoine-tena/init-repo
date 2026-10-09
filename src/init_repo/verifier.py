"""`init-repo verifier` : rejoue les contrôles du backend et du frontend, sans s'arrêter."""

import subprocess
from pathlib import Path

from init_repo.shell import InitRepoError, step

CHECKS: tuple[tuple[str, str, list[str]], ...] = (
    ("backend", "ruff", ["uv", "run", "ruff", "check", "."]),
    ("backend", "mypy", ["uv", "run", "mypy", "."]),
    ("backend", "pytest", ["uv", "run", "pytest", "-q"]),
    ("frontend", "types", ["pnpm", "typecheck"]),
)


def verify(root: Path) -> None:
    """Lance chaque contrôle, puis échoue en listant ceux qui ont échoué."""
    failed_checks: list[str] = []
    for folder, label, command in CHECKS:
        step(f"Vérification {folder} : {label}")
        completed = subprocess.run(command, cwd=root / folder, check=False)
        if completed.returncode != 0:
            failed_checks.append(f"{folder} {label}")
    if failed_checks:
        raise InitRepoError(f"contrôles en échec : {', '.join(failed_checks)}")
    print("\nTous les contrôles passent.")
