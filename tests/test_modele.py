from pathlib import Path

import copier

TEMPLATE_DIR = Path(__file__).resolve().parent.parent
ANSWERS = {
    "nom": "demo",
    "titre": "Démo",
    "description": "Projet de démonstration.",
    "proprietaire": "antoine-tena",
    "equipe": ["antoine-tena", "NathanBarrachin"],
}


def generate(destination: Path) -> Path:
    copier.run_copy(
        str(TEMPLATE_DIR), destination, data=ANSWERS, defaults=True, vcs_ref="HEAD", quiet=True
    )
    return destination


def test_generated_project_has_full_layout(tmp_path: Path) -> None:
    project_dir = generate(tmp_path / "demo")

    expected_files = [
        ".claude/settings.json",
        ".vscode/settings.json",
        ".pre-commit-config.yaml",
        "CLAUDE.md",
        "backend/CLAUDE.md",
        "frontend/CLAUDE.md",
        "backend/.env.example",
        "backend/config/api.py",
        "frontend/nuxt.config.ts",
        ".copier-answers.yml",
    ]
    missing_files = [name for name in expected_files if not (project_dir / name).is_file()]
    assert missing_files == []


def test_answers_fill_project_files(tmp_path: Path) -> None:
    project_dir = generate(tmp_path / "demo")

    assert (
        (project_dir / ".github/CODEOWNERS")
        .read_text()
        .endswith("* @antoine-tena @NathanBarrachin\n")
    )
    assert 'name = "demo-backend"' in (project_dir / "backend/pyproject.toml").read_text()
    assert (project_dir / "README.md").read_text().startswith("# Démo\n")


def test_vue_templates_keep_their_mustaches(tmp_path: Path) -> None:
    project_dir = generate(tmp_path / "demo")

    health_component = (project_dir / "frontend/app/components/HealthStatus.vue").read_text()
    assert "{{ health?.status }}" in health_component
