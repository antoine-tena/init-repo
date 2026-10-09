"""`kiln dev` : lance les serveurs de développement de la stack ; Ctrl+C les arrête tous.

Avec `--containers` (projet podman), toute la pile tourne dans podman (`compose.yaml`).
"""

import subprocess
from pathlib import Path

from kiln.shell import KilnError, require_tools, run, step
from kiln.stack import load_stack

COMPOSE_FILE = "compose.yaml"


def run_dev_servers(root: Path, *, in_containers: bool = False) -> None:
    stack = load_stack(root)
    if in_containers:
        _run_containers(root, has_podman=stack.has_podman)
        return
    commands = stack.dev_commands()
    step(" · ".join(f"{command.label} ({command.directory}/)" for command in commands))
    processes = [
        subprocess.Popen(list(command.argv), cwd=root / command.directory) for command in commands
    ]
    try:
        for process in processes:
            process.wait()
    except KeyboardInterrupt:
        pass
    finally:
        for process in processes:
            process.terminate()
        for process in processes:
            process.wait()


def _run_containers(root: Path, *, has_podman: bool) -> None:
    if not has_podman or not (root / COMPOSE_FILE).exists():
        raise KilnError("pas de podman dans ce projet : kiln set podman=true, sur une branche")
    require_tools("podman", "podman-compose")
    step("Pile podman (podman-compose up --build)")
    try:
        run(["podman-compose", "-f", COMPOSE_FILE, "up", "--build"], root)
    except KeyboardInterrupt:
        run(["podman-compose", "-f", COMPOSE_FILE, "down"], root)
