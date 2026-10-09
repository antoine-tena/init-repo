from pathlib import Path

import pytest
from packaging.version import Version

from kiln.deps import _major_bounds
from kiln.rules import charter_rules, verified_rules
from kiln.settings import parse_assignments
from kiln.shell import KilnError
from kiln.stack import Stack, stack_from_answers


def test_legacy_answers_mean_django_and_nuxt() -> None:
    assert stack_from_answers({}) == Stack(backend="django", frontend="nuxt", has_podman=False)


def test_python_dirs_cover_backend_and_python_frontend() -> None:
    stack = Stack(backend="data", frontend="streamlit", has_podman=False)

    assert stack.python_dirs == ("backend", "frontend")
    assert stack.pnpm_dir is None


def test_checks_end_with_charter() -> None:
    commands = Stack(backend="fastapi", frontend="next", has_podman=False).check_commands()

    assert [command.label for command in commands][-3:] == [
        "frontend lint",
        "frontend typecheck",
        "charte",
    ]


def test_major_bounds_keep_the_major() -> None:
    assert _major_bounds(Version("6.1.2")) == ">=6.1.2,<7.0.0"
    assert _major_bounds(Version("0.25.1")) == ">=0.25.1,<0.26.0"


def test_team_accepts_a_comma_list() -> None:
    assert parse_assignments(["equipe=a, b", "podman=true"]) == {
        "equipe": ["a", "b"],
        "podman": True,
    }


def test_unknown_key_is_refused() -> None:
    with pytest.raises(KilnError):
        parse_assignments(["couleur=bleu"])


def test_rules_checked_by_charte_are_verified(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("- **[SIGNAUX]** a\n- **[NOMS-INTERDITS]** b\n")
    (tmp_path / "charte.toml").write_text('[interdictions.signaux-django]\nid = "SIGNAUX"\n')

    stack = Stack(backend="django", frontend="aucun", has_podman=False)
    unverified = set(charter_rules(tmp_path)) - verified_rules(tmp_path, stack)

    assert unverified == {"NOMS-INTERDITS"}
