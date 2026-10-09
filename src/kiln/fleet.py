"""`kiln status --all` et `kiln update --all` : tous les repos kiln du dossier de code.

`update --all` ne change jamais la branche de l'arbre principal d'un repo : il travaille dans un
worktree (`.claude/worktrees/`) partant de la branche d'intégration, commite par lots de dix
fichiers au plus, pousse et ouvre une PR (en brouillon si les contrôles échouent), puis retire le
worktree. La branche reste, pour la PR.
"""

import datetime
import subprocess
from dataclasses import dataclass
from pathlib import Path

from kiln.check import run_checks
from kiln.install import install_project
from kiln.shell import KilnError, capture, require_tools, run, step
from kiln.stack import ANSWERS_FILE, load_stack, read_answers
from kiln.update import update_project

KILN_SOURCE_MARKERS = ("antoine-tena/kiln", "antoine-tena/init-repo")
KILN_REMOTE = "https://github.com/antoine-tena/kiln.git"
SEARCH_DEPTH = 3
SKIPPED_DIRS = frozenset({"node_modules", ".venv", ".git", ".claude", "_archives"})
WORKTREES_DIR = Path(".claude") / "worktrees"
UPDATE_BRANCH_PREFIX = "chore/kiln-update"
DEFAULT_INTEGRATION_BRANCH = "main"
MAX_FILES_PER_COMMIT = 10
COMMIT_ATTEMPTS = 2


@dataclass(frozen=True)
class ManagedRepo:
    root: Path
    template_commit: str


def find_repos(code_dir: Path) -> list[ManagedRepo]:
    """Repos du dossier de code générés par kiln (ou par init-repo, son ancien nom)."""
    repos = []
    for answers_path in _answer_files(code_dir, SEARCH_DEPTH):
        root = answers_path.parent
        answers = read_answers(root)
        if (root / ".git").is_dir() and any(
            marker in str(answers.get("_src_path", "")) for marker in KILN_SOURCE_MARKERS
        ):
            repos.append(ManagedRepo(root, str(answers.get("_commit", ""))))
    return repos


def _answer_files(directory: Path, depth: int) -> list[Path]:
    found = [directory / ANSWERS_FILE] if (directory / ANSWERS_FILE).is_file() else []
    if depth == 0:
        return found
    for child in sorted(directory.iterdir()):
        if child.is_dir() and child.name not in SKIPPED_DIRS:
            found += _answer_files(child, depth - 1)
    return found


def latest_template_commit() -> str:
    return capture(["git", "ls-remote", KILN_REMOTE, "HEAD"], Path.cwd()).split()[0]


def show_status(code_dir: Path) -> None:
    latest = latest_template_commit()
    for repo in find_repos(code_dir):
        branch = capture(["git", "branch", "--show-current"], repo.root)
        is_dirty = bool(capture(["git", "status", "--porcelain"], repo.root))
        is_current = bool(repo.template_commit) and latest.startswith(repo.template_commit)
        stack = load_stack(repo.root)
        print(
            f"{repo.root.relative_to(code_dir)!s:<30} {branch:<22} "
            f"{'modifié' if is_dirty else 'propre':<8} "
            f"{'modèle à jour' if is_current else 'modèle en retard':<17} "
            f"{stack.backend} + {stack.frontend}{' + podman' if stack.has_podman else ''}"
        )


def update_all(code_dir: Path, *, allow_major: bool) -> None:
    require_tools("git", "uv", "gh")
    results = [
        (repo, update_one(repo.root, allow_major=allow_major)) for repo in find_repos(code_dir)
    ]
    step("Bilan")
    for repo, outcome in results:
        print(f"{repo.root.relative_to(code_dir)!s:<30} {outcome}")


def update_one(root: Path, *, allow_major: bool) -> str:
    """Met un repo à jour dans un worktree et ouvre la PR ; renvoie le bilan en une ligne."""
    step(f"Repo {root.name}")
    integration = integration_branch(root)
    branch = f"{UPDATE_BRANCH_PREFIX}-{datetime.date.today().isoformat()}"
    worktree = root / WORKTREES_DIR / branch.replace("/", "-")
    try:
        _create_worktree(root, worktree, branch, integration)
        failed_checks = _update_worktree(worktree, allow_major=allow_major)
        if not capture(["git", "status", "--porcelain"], worktree):
            _remove_worktree(root, worktree, branch=branch)
            return "déjà à jour"
        commit_in_batches(worktree)
        pull_request = _publish(worktree, branch, integration, failed_checks)
    except KilnError as error:
        return f"échec : {error} (worktree laissé dans {worktree})"
    _remove_worktree(root, worktree)
    suffix = (
        f" en brouillon, contrôles en échec : {', '.join(failed_checks)}" if failed_checks else ""
    )
    return f"PR ouverte{suffix} : {pull_request}"


def _update_worktree(worktree: Path, *, allow_major: bool) -> list[str]:
    """Installe, met à jour modèle et dépendances, puis renvoie les contrôles en échec."""
    install_project(worktree)
    update_project(
        worktree,
        should_update_template=True,
        should_update_deps=True,
        allow_major=allow_major,
        should_check=False,
    )
    return run_checks(worktree)


def integration_branch(root: Path) -> str:
    completed = subprocess.run(
        ["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    head = completed.stdout.strip()
    return head.removeprefix("origin/") if completed.returncode == 0 else DEFAULT_INTEGRATION_BRANCH


def _create_worktree(root: Path, worktree: Path, branch: str, integration: str) -> None:
    run(["git", "fetch", "-q", "origin", integration], root)
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", str(WORKTREES_DIR / "x")], cwd=root, check=False
    )
    if ignored.returncode != 0:
        with (root / ".git" / "info" / "exclude").open("a") as exclude:
            exclude.write(f"\n{WORKTREES_DIR.as_posix()}/\n")
    run(
        [
            "git",
            "worktree",
            "add",
            "-q",
            "--no-track",
            str(worktree),
            "-b",
            branch,
            f"origin/{integration}",
        ],
        root,
    )


def _remove_worktree(root: Path, worktree: Path, *, branch: str | None = None) -> None:
    run(["git", "worktree", "remove", "--force", str(worktree)], root)
    if branch is not None:
        run(["git", "branch", "-q", "-D", branch], root)


def commit_in_batches(worktree: Path) -> None:
    """Commits de dix fichiers au plus ([COMMITS]), regroupés par dossier de premier niveau."""
    run(["git", "add", "-A"], worktree)
    changed = capture(["git", "diff", "--cached", "--name-only"], worktree).splitlines()
    run(["git", "reset", "-q"], worktree)
    groups: dict[str, list[str]] = {}
    for path in changed:
        groups.setdefault(path.split("/")[0] if "/" in path else "racine", []).append(path)
    for group, paths in groups.items():
        for start in range(0, len(paths), MAX_FILES_PER_COMMIT):
            batch = paths[start : start + MAX_FILES_PER_COMMIT]
            _commit(worktree, batch, f"chore: mise à jour kiln, {group}"[:50])


def _commit(worktree: Path, paths: list[str], message: str) -> None:
    """Commit avec les crochets pre-commit ; un crochet qui corrige (ruff) a droit à un retour."""
    for _ in range(COMMIT_ATTEMPTS):
        run(["git", "add", "-A", "--", *paths], worktree)
        committed = subprocess.run(
            ["git", "commit", "-q", "-m", message], cwd=worktree, check=False
        )
        if committed.returncode == 0:
            return
    raise KilnError(f"commit refusé par les crochets : {message}")


def _publish(worktree: Path, branch: str, integration: str, failed_checks: list[str]) -> str:
    run(["git", "push", "-q", "-u", "origin", branch], worktree)
    checks_line = (
        f"Contrôles en échec : {', '.join(failed_checks)}. À corriger avant la fusion."
        if failed_checks
        else "Contrôles : tous verts (kiln check)."
    )
    body = (
        "Mise à jour par `kiln update --all` : évolutions du modèle kiln et des dépendances.\n\n"
        f"{checks_line}"
    )
    command = [
        "gh",
        "pr",
        "create",
        "--base",
        integration,
        "--head",
        branch,
        "--title",
        f"chore: mise à jour kiln ({datetime.date.today().isoformat()})",
        "--body",
        body,
    ]
    return capture([*command, *(["--draft"] if failed_checks else [])], worktree)
