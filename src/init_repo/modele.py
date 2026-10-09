"""Accès au modèle Copier : source par défaut et révision suivie."""

import os

DEFAULT_TEMPLATE_SOURCE = "https://github.com/antoine-tena/init-repo.git"
TEMPLATE_SOURCE_VARIABLE = "INIT_REPO_MODELE"
# Les projets suivent la tête de main du modèle, sans attendre d'étiquette de version.
TEMPLATE_REVISION = "HEAD"


def template_source(explicit_source: str | None) -> str:
    """Source du modèle : option, puis variable d'environnement, puis dépôt GitHub."""
    if explicit_source:
        return explicit_source
    return os.environ.get(TEMPLATE_SOURCE_VARIABLE, DEFAULT_TEMPLATE_SOURCE)
