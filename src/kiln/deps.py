"""Verrous et mises à jour des dépendances, selon la politique de kiln.

Par défaut, des mises à jour compatibles : uv reste dans les bornes du pyproject.toml (même
version majeure), pnpm ne monte que les dépendances dont la dernière version garde la même
majeure. `--major` relève les bornes Python à la dernière version, prend les dernières versions
pnpm et met à jour les crochets pre-commit. Les contrôles suivent toujours (`kiln check`).
"""

import json
import subprocess
import tomllib
from pathlib import Path

import yaml  # fourni par copier
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

from kiln.shell import run, step
from kiln.stack import Stack

PNPM_WORKSPACE = "pnpm-workspace.yaml"
DEV_DEPENDENCY_TYPE = "devDependencies"


def lock_dependencies(root: Path, stack: Stack) -> None:
    """Verrous recalculés sans montée de version (le modèle a pu changer les dépendances)."""
    step("Verrous des dépendances")
    for directory in stack.python_dirs:
        run(["uv", "lock"], root / directory)
    if stack.pnpm_dir is not None:
        run(["pnpm", "install", "--lockfile-only"], root / stack.pnpm_dir)


def sync_dependencies(root: Path, stack: Stack) -> None:
    for directory in stack.python_dirs:
        run(["uv", "sync"], root / directory)
    if stack.pnpm_dir is not None:
        run(["pnpm", "install"], root / stack.pnpm_dir)


def update_dependencies(root: Path, stack: Stack, *, allow_major: bool) -> None:
    for directory in stack.python_dirs:
        step(f"{directory} : dépendances Python{' (majeures comprises)' if allow_major else ''}")
        if allow_major:
            raise_python_bounds(root / directory)
        run(["uv", "lock", "--upgrade"], root / directory)
    if stack.pnpm_dir is not None:
        step(f"{stack.pnpm_dir} : dépendances pnpm{' (majeures comprises)' if allow_major else ''}")
        update_pnpm(root / stack.pnpm_dir, allow_major=allow_major)
    if allow_major:
        step("Crochets pre-commit")
        run(["pre-commit", "autoupdate"], root)
    sync_dependencies(root, stack)


def _requirement_strings(pyproject: dict[str, object]) -> list[str]:
    project = pyproject.get("project", {})
    groups = pyproject.get("dependency-groups", {})
    strings = list(project.get("dependencies", [])) if isinstance(project, dict) else []
    if isinstance(groups, dict):
        strings += [item for group in groups.values() for item in group if isinstance(item, str)]
    return strings


def _major_bounds(version: Version) -> str:
    if version.major == 0:
        return f">={version},<0.{version.minor + 1}.0"
    return f">={version},<{version.major + 1}.0.0"


def _bare(requirement: Requirement) -> str:
    extras = f"[{','.join(sorted(requirement.extras))}]" if requirement.extras else ""
    return f"{requirement.name}{extras}"


def raise_python_bounds(project_dir: Path) -> None:
    """Bornes retirées, dernières versions résolues, puis bornes « même majeure » reposées."""
    pyproject_path = project_dir / "pyproject.toml"
    text = pyproject_path.read_text()
    bounded = [
        Requirement(raw)
        for raw in _requirement_strings(tomllib.loads(text))
        if Requirement(raw).specifier and Requirement(raw).url is None
    ]
    for requirement in bounded:
        text = text.replace(f'"{requirement}"', f'"{_bare(requirement)}"')
    pyproject_path.write_text(text)
    run(["uv", "lock", "--upgrade"], project_dir)
    locked = tomllib.loads((project_dir / "uv.lock").read_text()).get("package", [])
    versions = {canonicalize_name(package["name"]): package["version"] for package in locked}
    for requirement in bounded:
        version = Version(versions[canonicalize_name(requirement.name)])
        text = text.replace(
            f'"{_bare(requirement)}"', f'"{_bare(requirement)}{_major_bounds(version)}"'
        )
    pyproject_path.write_text(text)


def _major(version: str) -> int:
    return int(version.split(".")[0])


def _ignored_pnpm_dependencies(project_dir: Path) -> set[str]:
    workspace_path = project_dir / PNPM_WORKSPACE
    workspace = yaml.safe_load(workspace_path.read_text()) if workspace_path.exists() else {}
    update_config = (workspace or {}).get("updateConfig", {}) or {}
    return set(update_config.get("ignoreDependencies", []) or [])


def update_pnpm(project_dir: Path, *, allow_major: bool) -> None:
    """Versions exactes montées par `pnpm add`, majeures seulement si `allow_major`."""
    completed = subprocess.run(
        ["pnpm", "outdated", "--format", "json"],
        cwd=project_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    outdated = json.loads(completed.stdout or "{}")
    ignored = _ignored_pnpm_dependencies(project_dir)
    upgrades: dict[bool, list[str]] = {True: [], False: []}
    held_back = []
    for name, info in outdated.items():
        if name in ignored:
            continue
        if allow_major or _major(info["latest"]) == _major(info["current"]):
            upgrades[info.get("dependencyType") == DEV_DEPENDENCY_TYPE].append(
                f"{name}@{info['latest']}"
            )
        else:
            held_back.append(f"{name} {info['current']} → {info['latest']}")
    for is_dev, packages in upgrades.items():
        if packages:
            run(["pnpm", "add", *(["--save-dev"] if is_dev else []), *packages], project_dir)
    if held_back:
        print("Majeures disponibles (kiln update --major) : " + ", ".join(held_back))
