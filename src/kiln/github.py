"""Création du dépôt GitHub, protection de main et develop, invitations de l'équipe."""

import json
import subprocess
from pathlib import Path

from kiln.shell import KilnError, run, step

RULESET_NAME = "Protection main et develop"
REPOSITORY_ADMIN_ROLE_ID = 5
REQUIRED_APPROVALS = 1

RULESET = {
    "name": RULESET_NAME,
    "target": "branch",
    "enforcement": "active",
    "conditions": {
        "ref_name": {"include": ["refs/heads/main", "refs/heads/develop"], "exclude": []},
    },
    # L'admin peut fusionner une PR sans approbation, jamais pousser directement.
    "bypass_actors": [
        {
            "actor_id": REPOSITORY_ADMIN_ROLE_ID,
            "actor_type": "RepositoryRole",
            "bypass_mode": "pull_request",
        },
    ],
    "rules": [
        {"type": "deletion"},
        {"type": "non_fast_forward"},
        {
            "type": "pull_request",
            "parameters": {
                "required_approving_review_count": REQUIRED_APPROVALS,
                "dismiss_stale_reviews_on_push": True,
                "require_code_owner_review": False,
                "require_last_push_approval": False,
                "required_review_thread_resolution": True,
                "allowed_merge_methods": ["merge"],
            },
        },
    ],
}


def publish(root: Path, repository: str, team_logins: list[str]) -> None:
    step(f"GitHub : dépôt privé {repository}")
    run(["gh", "repo", "create", repository, "--private", "--source", ".", "--push"], root)
    step("GitHub : protection de main et develop")
    _post_ruleset(root, repository)
    step("GitHub : alertes et correctifs de sécurité (Dependabot)")
    _enable_security_updates(root, repository)
    owner = repository.split("/")[0]
    for login in team_logins:
        if login != owner:
            step(f"GitHub : invitation de {login}")
            _gh_put(root, f"repos/{repository}/collaborators/{login}", "permission=push")


def _gh_put(root: Path, endpoint: str, *fields: str) -> None:
    field_options = [option for field in fields for option in ("-f", field)]
    run(["gh", "api", "-X", "PUT", endpoint, *field_options, "--silent"], root)


def _enable_security_updates(root: Path, repository: str) -> None:
    """Dependabot ne propose que les correctifs de sécurité ; le reste passe par kiln update."""
    _gh_put(root, f"repos/{repository}/vulnerability-alerts")
    _gh_put(root, f"repos/{repository}/automated-security-fixes")


def _post_ruleset(root: Path, repository: str) -> None:
    completed = subprocess.run(
        ["gh", "api", "-X", "POST", f"repos/{repository}/rulesets", "--input", "-", "--silent"],
        cwd=root,
        input=json.dumps(RULESET),
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise KilnError("création du ruleset refusée par GitHub")
