"""Liste des règles de la charte qu'aucun contrôle ne vérifie, recalculée par kiln.

Une règle est vérifiée quand `charte.toml` la cite (`id = "…"`) ou quand un outil de la CI la
tient (mypy, TypeScript strict, verrous figés, audit, pre-commit). Toutes les autres, lues dans
les `CLAUDE.md`, vont dans `scripts/ci/charte-non-verifiee.txt`, appliquées en revue : une règle
locale ajoutée à la charte y apparaît d'elle-même, une règle qui gagne son contrôle en sort.
"""

import re
import tomllib
from pathlib import Path

from kiln.stack import PNPM_FRONTENDS, Stack

UNVERIFIED_RULES_FILE = Path("scripts") / "ci" / "charte-non-verifiee.txt"
CHARTER_FILES = ("CLAUDE.md", "backend/CLAUDE.md", "frontend/CLAUDE.md")
RULE_PATTERN = re.compile(r"\*\*\[([A-Z0-9+-]+)\]\*\*")

ALWAYS_VERIFIED = frozenset({"PAS-SUR-MAIN", "DEPENDANCES-FIGEES", "AUDIT-VULNERABILITES"})
PYTHON_VERIFIED = frozenset({"TYPAGE", "TYPAGE-STRICT", "MYPY"})
PNPM_VERIFIED = frozenset({"TS-STRICT", "ZERO-ANY"})

HEADER = """\
# Règles de CLAUDE.md qu'aucun contrôle ne vérifie : appliquées en revue.
# Fichier recalculé par kiln (set, update) depuis les CLAUDE.md et charte.toml : pour en retirer
# une règle, ajouter son contrôle dans charte.toml, ou l'amender dans CLAUDE.md.
"""


def charter_rules(root: Path) -> list[str]:
    """Identifiants des règles des charters, dans leur ordre d'apparition, sans doublon."""
    rules: dict[str, None] = {}
    for name in CHARTER_FILES:
        path = root / name
        if path.exists():
            rules.update(dict.fromkeys(RULE_PATTERN.findall(path.read_text())))
    return list(rules)


def verified_rules(root: Path, stack: Stack) -> set[str]:
    charte_path = root / "charte.toml"
    config = tomllib.loads(charte_path.read_text()) if charte_path.exists() else {}
    verified = set(ALWAYS_VERIFIED)
    for section in ("interdictions", "cliquets", "planchers"):
        rules = config.get(section, {})
        verified |= {str(rule["id"]) for rule in rules.values() if "id" in rule}
    if stack.python_dirs:
        verified |= PYTHON_VERIFIED
    if stack.frontend in PNPM_FRONTENDS:
        verified |= PNPM_VERIFIED
    return verified


def write_unverified_rules(root: Path, stack: Stack) -> None:
    verified = verified_rules(root, stack)
    unverified = [rule for rule in charter_rules(root) if rule not in verified]
    path = root / UNVERIFIED_RULES_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(HEADER + "".join(f"[{rule}]\n" for rule in unverified))
