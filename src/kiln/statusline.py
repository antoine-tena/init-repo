"""Réglages de la status line de Claude Code (`~/.claude/statusline.py`) propres au repo.

Ils vivent dans les réponses de kiln (`statusline_ci`, `url_sante_prod`), donc partagés par
l'équipe, et sont posés en `git config statusline.*` à chaque `kiln install`, `kiln new` et
`kiln set` : personne n'a rien à régler à la main.
"""

from pathlib import Path

from kiln.shell import run
from kiln.stack import read_answers


def apply_statusline_settings(root: Path) -> None:
    answers = read_answers(root)
    show_ci = answers.get("statusline_ci", True) is not False
    run(["git", "config", "statusline.ci", "true" if show_ci else "false"], root)
    prod_url = str(answers.get("url_sante_prod") or "")
    if prod_url:
        run(["git", "config", "statusline.prod-url", prod_url], root)
