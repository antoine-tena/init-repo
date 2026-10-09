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


def test_charter_tooling_is_generated(tmp_path: Path) -> None:
    project_dir = generate(tmp_path / "demo")

    for name in ("charte.toml", "scripts/ci/charte-non-verifiee.txt", ".github/workflows/ci.yml"):
        assert (project_dir / name).is_file(), name
    assert not (project_dir / "docs").exists()


def test_a_faire_is_optional(tmp_path: Path) -> None:
    project_dir = tmp_path / "demo"
    copier.run_copy(
        str(TEMPLATE_DIR),
        project_dir,
        data={**ANSWERS, "avec_a_faire": True, "boussole": "la démo en ligne"},
        defaults=True,
        vcs_ref="HEAD",
        quiet=True,
    )

    a_faire = (project_dir / "docs/a-faire/a-faire.md").read_text()
    assert "La boussole est **la démo en ligne**." in a_faire
    assert "docs/a-faire/" in (project_dir / "CLAUDE.md").read_text()
