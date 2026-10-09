"""`init-repo dev` : lance le backend et le frontend ensemble ; Ctrl+C arrête les deux."""

import subprocess
from pathlib import Path

from init_repo.shell import step

BACKEND_COMMAND = ["uv", "run", "python", "manage.py", "runserver"]
FRONTEND_COMMAND = ["pnpm", "dev"]


def run_dev_servers(root: Path) -> None:
    step("Backend http://localhost:8000 · frontend http://localhost:3000")
    processes = [
        subprocess.Popen(BACKEND_COMMAND, cwd=root / "backend"),
        subprocess.Popen(FRONTEND_COMMAND, cwd=root / "frontend"),
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
