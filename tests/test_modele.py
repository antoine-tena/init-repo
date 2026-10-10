import json
import tomllib
from pathlib import Path

import copier
import pytest
import yaml

TEMPLATE_DIR = Path(__file__).resolve().parent.parent
ANSWERS = {
    "nom": "demo",
    "titre": "Démo",
    "description": "Projet de démonstration.",
    "proprietaire": "antoine-tena",
    "equipe": ["antoine-tena", "NathanBarrachin"],
}
BACKENDS = ("django", "fastapi", "data", "aucun")
FRONTENDS = ("nuxt", "next", "astro", "streamlit", "dash", "aucun")
STACKS = [
    (back, front) for back in BACKENDS for front in FRONTENDS if (back, front) != ("aucun",) * 2
]
JSON_FILES = (".vscode/settings.json", ".vscode/extensions.json", ".claude/settings.json")


def generate(destination: Path, **extra_answers: object) -> Path:
    copier.run_copy(
        str(TEMPLATE_DIR),
        destination,
        data={**ANSWERS, **extra_answers},
        defaults=True,
        vcs_ref="HEAD",
        quiet=True,
    )
    return destination


def test_default_stack_is_django_and_nuxt(tmp_path: Path) -> None:
    project_dir = generate(tmp_path / "demo")

    assert (project_dir / "backend/config/api.py").is_file()
    assert (project_dir / "frontend/nuxt.config.ts").is_file()
    assert (
        (project_dir / ".github/CODEOWNERS")
        .read_text()
        .endswith("* @antoine-tena @NathanBarrachin\n")
    )


@pytest.mark.parametrize(("backend", "frontend"), STACKS)
def test_every_stack_renders_valid_files(tmp_path: Path, backend: str, frontend: str) -> None:
    project_dir = generate(tmp_path / "demo", backend=backend, frontend=frontend)

    rendered = [
        path for path in project_dir.rglob("*") if path.is_file() and ".git" not in path.parts
    ]
    assert not [path for path in rendered if path.suffix == ".jinja"]
    assert not [path for path in rendered if path.suffix != ".ico" and "{%" in path.read_text()]
    tomllib.loads((project_dir / "charte.toml").read_text())
    yaml.safe_load((project_dir / ".github/workflows/ci.yml").read_text())
    yaml.safe_load((project_dir / ".pre-commit-config.yaml").read_text())
    for name in JSON_FILES:
        json.loads((project_dir / name).read_text())
    assert (project_dir / "backend").is_dir() == (backend != "aucun")
    assert (project_dir / "frontend").is_dir() == (frontend != "aucun")


@pytest.mark.parametrize(("backend", "frontend"), STACKS)
def test_podman_adds_containers_for_every_stack(
    tmp_path: Path, backend: str, frontend: str
) -> None:
    project_dir = generate(tmp_path / "demo", backend=backend, frontend=frontend, podman=True)

    compose = yaml.safe_load((project_dir / "compose.yaml").read_text())
    for directory in ("backend", "frontend"):
        if (project_dir / directory).is_dir():
            containerfile = (project_dir / directory / "Containerfile").read_text()
            instructions = [line for line in containerfile.splitlines() if not line.startswith("#")]
            # Outil interdit : la règle [UV-PODMAN] est justement vérifiée ici.
            assert not [line for line in instructions if "pip install" in line or "docker " in line]
    assert compose["services"]


def test_stack_advice_follows_project_type(tmp_path: Path) -> None:
    project_dir = generate(tmp_path / "demo", type_projet="tableau")

    answers = yaml.safe_load((project_dir / ".copier-answers.yml").read_text())
    assert (answers["backend"], answers["frontend"]) == ("data", "streamlit")


def test_vue_templates_keep_their_mustaches(tmp_path: Path) -> None:
    project_dir = generate(tmp_path / "demo")

    health_component = (project_dir / "frontend/app/components/HealthStatus.vue").read_text()
    assert "{{ health?.status }}" in health_component


def test_a_faire_is_always_there(tmp_path: Path) -> None:
    project_dir = generate(tmp_path / "demo", boussole="la démo en ligne", backend="fastapi")

    a_faire = (project_dir / "docs/a-faire/a-faire.md").read_text()
    assert "La boussole est **la démo en ligne**." in a_faire
    assert "docs/a-faire/" in (project_dir / "CLAUDE.md").read_text()
    urgent = (project_dir / "docs/a-faire/urgent.md").read_text()
    # La status line compte les lignes qui commencent par une case ouverte : aucune au départ.
    assert not [line for line in urgent.splitlines() if line.lstrip().startswith("- [ ]")]


def test_data_stack_accepts_numeric_arrays_and_trained_models(tmp_path: Path) -> None:
    project_dir = generate(tmp_path / "demo", backend="data", frontend="streamlit")

    rules = (project_dir / "backend/CLAUDE.md").read_text()
    assert "NumPy" in rules
    assert "`data/models/`" in rules
    attributes = (project_dir / ".gitattributes").read_text()
    assert "backend/data/models/** linguist-generated=true" in attributes
