"""Socle commun aux règles : fichiers du dépôt, mise en forme des échecs, justifications."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


class Depot:
    """Le repo vérifié : sa racine, sa configuration (`charte.toml`) et ses fichiers."""

    def __init__(self, racine: Path, config: dict) -> None:
        self.racine = racine
        self.config = config
        # Sous-chaînes de chemin ignorées par toutes les règles (ex. "/migrations/").
        self.exclus = config.get("exclus", [])
        # Fichiers engendrés : la liste vit dans `.gitattributes` (attribut linguist-generated).
        self.engendres = set(self.git("ls-files", "--", ":(attr:linguist-generated=true)").split())

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=self.racine, capture_output=True, text=True, check=False
        ).stdout

    def suivis(self, motifs: str | list[str], *, exclus: bool = True) -> list[Path]:
        """Fichiers suivis ET fichiers nouveaux non ignorés : `git ls-files` seul ignorait un module
        créé mais pas encore indexé, et le contrôle local passait au vert sur du code que la CI
        aurait refusé. Un fichier supprimé mais encore indexé est ignoré."""
        motifs = [motifs] if isinstance(motifs, str) else motifs
        sortie = self.git(
            "ls-files", "--cached", "--others", "--exclude-standard", "--", *motifs
        ).split()
        vus = dict.fromkeys(
            p
            for p in sortie
            if (self.racine / p).exists() and not (exclus and any(e in p for e in self.exclus))
        )
        return [self.racine / p for p in vus]

    def rel(self, chemin: Path) -> str:
        return str(chemin.relative_to(self.racine))

    def engendre(self, chemin: Path) -> bool:
        return self.rel(chemin) in self.engendres


def echec(regle: str, message: str, fautifs: list[str]) -> str:
    liste = "\n".join(f"      {f}" for f in fautifs[:15])
    reste = f"\n      … et {len(fautifs) - 15} autre(s)" if len(fautifs) > 15 else ""
    return f"  [{regle}] {message}\n{liste}{reste}"


def justifie(lignes: list[str], numero: int, motif: str, au_dessus: int = 8) -> bool:
    """Une exception se justifie par un commentaire (`# <motif> : raison`) dans les lignes qui
    précèdent la ligne `numero` (1-indexée), elle comprise."""
    bloc = "\n".join(lignes[max(0, numero - au_dessus - 1) : numero])
    return re.search(rf"#\s*{motif}\s*:", bloc) is not None


def hors_tests(fichiers: list[Path]) -> list[Path]:
    return [f for f in fichiers if "tests" not in f.parts]
