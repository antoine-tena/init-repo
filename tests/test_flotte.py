import subprocess
from pathlib import Path

from kiln.fleet import MAX_FILES_PER_COMMIT, commit_in_batches, find_repos


def make_repo(root: Path, source: str) -> Path:
    root.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    (root / ".copier-answers.yml").write_text(f"_commit: abc1234\n_src_path: {source}\n")
    return root


def test_only_kiln_repos_are_found(tmp_path: Path) -> None:
    make_repo(tmp_path / "association" / "projet", "https://github.com/antoine-tena/kiln.git")
    make_repo(tmp_path / "ancien", "https://github.com/antoine-tena/init-repo.git")
    make_repo(tmp_path / "autre", "gh:quelquun/modele")

    found = sorted(repo.root.name for repo in find_repos(tmp_path))

    assert found == ["ancien", "projet"]


def test_commits_hold_at_most_ten_files(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "projet", "https://github.com/antoine-tena/kiln.git")
    git = ["git", "-c", "user.email=t@t", "-c", "user.name=t"]
    subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "init"], cwd=repo, check=True)
    for index in range(MAX_FILES_PER_COMMIT + 3):
        (repo / f"fichier_{index}.txt").write_text("contenu\n")

    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    commit_in_batches(repo)

    sizes = [
        len(
            subprocess.run(
                ["git", "show", "--name-only", "--format=", revision],
                cwd=repo,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.split()
        )
        for revision in ("HEAD", "HEAD~1")
    ]
    # Les treize fichiers et le fichier de réponses : dix, puis quatre.
    assert sorted(sizes) == [4, 10]
