"""Configuration de kiln propre au poste : `~/.config/kiln/config.toml`.

Le système (Linux, WSL, macOS) est demandé une fois, à la première installation ; le
propriétaire GitHub, l'équipe et le dossier des repos donnent leurs valeurs par défaut à
`kiln new` et à `kiln update --all`.
"""

import os
import platform
import sys
import tomllib
from dataclasses import dataclass, replace
from pathlib import Path

CONFIG_DIR_VARIABLE = "XDG_CONFIG_HOME"
CONFIG_RELATIVE_PATH = Path("kiln") / "config.toml"
DEFAULT_CODE_DIR = Path.home() / "code"

SYSTEMS = ("linux", "wsl", "macos")
SYSTEM_LABELS = {"linux": "Linux", "wsl": "Windows (WSL)", "macos": "macOS"}


@dataclass(frozen=True)
class UserConfig:
    system: str | None = None
    owner: str | None = None
    team: tuple[str, ...] = ()
    code_dir: Path = DEFAULT_CODE_DIR


def config_path() -> Path:
    base_dir = os.environ.get(CONFIG_DIR_VARIABLE)
    return (Path(base_dir) if base_dir else Path.home() / ".config") / CONFIG_RELATIVE_PATH


def load_config() -> UserConfig:
    path = config_path()
    if not path.exists():
        return UserConfig()
    values = tomllib.loads(path.read_text())
    team = values.get("equipe", [])
    return UserConfig(
        system=values.get("systeme"),
        owner=values.get("proprietaire"),
        team=tuple(str(login) for login in team) if isinstance(team, list) else (),
        code_dir=Path(values.get("dossier_code", str(DEFAULT_CODE_DIR))).expanduser(),
    )


def save_config(config: UserConfig) -> None:
    lines = ["# Configuration de kiln pour ce poste (kiln install la crée)."]
    if config.system:
        lines.append(f'systeme = "{config.system}"')
    if config.owner:
        lines.append(f'proprietaire = "{config.owner}"')
    if config.team:
        lines.append("equipe = [" + ", ".join(f'"{login}"' for login in config.team) + "]")
    lines.append(f'dossier_code = "{config.code_dir}"')
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def detect_system() -> str:
    if platform.system() == "Darwin":
        return "macos"
    proc_version = Path("/proc/version")
    if proc_version.exists() and "microsoft" in proc_version.read_text().lower():
        return "wsl"
    return "linux"


def ask_system(detected: str) -> str:
    """Demande le système, la valeur détectée par défaut ; hors terminal, la garde."""
    if not sys.stdin.isatty():
        return detected
    choices = " / ".join(f"{key} ({SYSTEM_LABELS[key]})" for key in SYSTEMS)
    answer = input(f"Système de ce poste ? {choices} [{detected}] : ").strip().lower()
    return answer if answer in SYSTEMS else detected


def ensure_system(config: UserConfig) -> UserConfig:
    """Système du poste, demandé une seule fois puis gardé dans la configuration."""
    if config.system in SYSTEMS:
        return config
    updated = replace(config, system=ask_system(detect_system()))
    save_config(updated)
    print(f"Système enregistré dans {config_path()} : {updated.system}.")
    return updated
