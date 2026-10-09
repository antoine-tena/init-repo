"""Lancement des commandes externes (git, uv, pnpm, gh) et messages à l'utilisateur."""

import shutil
import subprocess
from pathlib import Path


class KilnError(Exception):
    """Erreur attendue, affichée sans trace à l'utilisateur."""


def step(title: str) -> None:
    print(f"\n==> {title}", flush=True)


def run(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    """Lance une commande en affichant sa sortie ; échoue si elle échoue."""
    completed = subprocess.run(command, cwd=cwd, env=env, check=False)
    if completed.returncode != 0:
        raise KilnError(f"échec de `{' '.join(command)}` (code {completed.returncode})")


def capture(command: list[str], cwd: Path) -> str:
    """Lance une commande et renvoie sa sortie standard, sans espaces autour."""
    completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise KilnError(f"échec de `{' '.join(command)}` : {completed.stderr.strip()}")
    return completed.stdout.strip()


INSTALL_HINTS = {
    "git": "https://git-scm.com/downloads",
    "uv": "curl -LsSf https://astral.sh/uv/install.sh | sh",
    "pnpm": "npm install -g pnpm (Node 24 requis)",
    "gh": "https://cli.github.com, puis gh auth login",
}


def require_tools(*tool_names: str) -> None:
    missing_tools = [name for name in tool_names if shutil.which(name) is None]
    if missing_tools:
        hints = "\n".join(f"  {name} : {INSTALL_HINTS.get(name, '')}" for name in missing_tools)
        raise KilnError(f"outils manquants :\n{hints}")


def repo_root(start: Path) -> Path:
    return Path(capture(["git", "rev-parse", "--show-toplevel"], start))
