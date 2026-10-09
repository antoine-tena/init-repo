#!/usr/bin/env python3
"""charte — vérifie un repo contre les règles de sa charte (CLAUDE.md), décrites dans le
`charte.toml` de sa racine. Installée avec kiln, à côté de la commande `kiln`.

Une charte que rien n'exécute décrit un projet qui n'existe pas. Deux régimes, parce qu'un
contrôle qui échoue sur 47 fichiers dès le premier jour finit désactivé :

- **interdiction** (`[interdictions.<nom>]`) : la règle est respectée partout, toute
  réintroduction échoue ;
- **cliquet** (`[cliquets.<nom>]`, `budget`) : la règle a un passif, le nombre courant devient
  un plafond. Le contrôle échoue si le passif augmente, et signale s'il diminue — le budget
  doit alors être abaissé dans charte.toml, ce qui rend la dette impossible à reprendre.
  Un **plancher** (`[planchers.<nom>]`, `plancher`) est le cliquet inverse.

Le nom d'une section est celui de la règle (voir interdictions.py et cliquets.py) ; une clé
`regle` permet d'en déclarer plusieurs du même type. `regles_locales` : modules Python du
repo, chacun avec une fonction `verifier(depot, params) -> list[str]`, pour ses règles propres.

Usage : charte [verifier]   règles de la charte (défaut)
        charte types        typage mypy en cliquet ([types])
        charte couverture   planchers de couverture du backend ([couverture])
        charte --detail     valeur de chaque cliquet et plancher, sans juger
Sortie non nulle si une règle est enfreinte.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tomllib
from pathlib import Path

from kiln.charte.cliquets import COMPTEURS
from kiln.charte.interdictions import REGLES
from kiln.charte.moteur import Depot, echec
from kiln.charte.outils_python import couverture, types

FIN_RAPPORT = "Règles de CLAUDE.md non vérifiées"


def charger() -> Depot:
    racine = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
    ).stdout.strip()
    config = Path(racine or ".") / "charte.toml"
    if not config.exists():
        sys.exit(f"charte : pas de charte.toml à la racine du repo ({config.parent}).")
    return Depot(config.parent, tomllib.loads(config.read_text("utf-8")))


def _regles_locales(depot: Depot) -> list:
    fonctions = []
    for chemin in depot.config.get("regles_locales", []):
        spec = importlib.util.spec_from_file_location(Path(chemin).stem, depot.racine / chemin)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        fonctions.append(module.verifier)
    return fonctions


def _regles_non_verifiees(depot: Depot) -> None:
    fichier = depot.config.get("regles_non_verifiees")
    if not fichier:
        return
    regles = [
        r
        for r in (depot.racine / fichier).read_text("utf-8").splitlines()
        if r and not r.startswith("#")
    ]
    print(f"\n{FIN_RAPPORT} par ce script (à appliquer ou à amender) :")
    print("\n".join(f"  - {r}" for r in regles))


def mesures(depot: Depot, section: str) -> list[tuple[str, dict, int, list[str]]]:
    sortie = []
    for nom, p in depot.config.get(section, {}).items():
        valeur, detail = COMPTEURS[p.get("regle", nom)](depot, p)
        sortie.append((nom, p, valeur, detail))
    return sortie


def verifier(depot: Depot) -> int:
    problemes: list[str] = []
    for nom, p in depot.config.get("interdictions", {}).items():
        problemes.extend(REGLES[p.get("regle", nom)](depot, p))
    for fonction in _regles_locales(depot):
        problemes.extend(fonction(depot, {}))

    a_resserrer = []
    for nom, p, valeur, detail in mesures(depot, "cliquets"):
        budget = p["budget"]
        if valeur > budget:
            message = f"{p.get('message', nom)} : {valeur} infractions, plafond {budget}. {valeur - budget} de plus qu'au dernier abaissement."
            problemes.append(echec(p.get("id", "CLIQUET"), message, detail))
        elif valeur < budget:
            a_resserrer.append(
                f"  {nom} : {valeur} < {budget} — abaisser `budget` de [cliquets.{nom}] à {valeur} (charte.toml)."
            )
    for nom, p, valeur, detail in mesures(depot, "planchers"):
        plancher = p["plancher"]
        if valeur < plancher:
            message = (
                f"{p.get('message', nom)} : {valeur}, plancher {plancher}. La valeur a baissé."
            )
            problemes.append(echec(p.get("id", "PLANCHER"), message, detail))
        elif valeur > plancher:
            a_resserrer.append(
                f"  {nom} : {valeur} > {plancher} — relever `plancher` de [planchers.{nom}] à {valeur} (charte.toml)."
            )

    if a_resserrer:
        print("Dette réduite, budgets à resserrer (le contrôle reste vert) :")
        print("\n".join(a_resserrer))
        print()
    if problemes:
        print("Violations de CLAUDE.md :\n")
        print("\n\n".join(problemes))
        print("\nLa charte est la norme du dépôt. Corriger, ou l'amender explicitement.")
        _regles_non_verifiees(depot)
        return 1
    print("Règles contrôlées de CLAUDE.md : aucune violation, aucun cliquet dépassé.")
    _regles_non_verifiees(depot)
    return 0


def detail(depot: Depot) -> int:
    for section in ("cliquets", "planchers"):
        for nom, p, valeur, _ in mesures(depot, section):
            print(f"{section}.{nom} = {valeur} (seuil {p.get('budget', p.get('plancher'))})")
    return 0


def main() -> int:
    commande = sys.argv[1] if len(sys.argv) > 1 else "verifier"
    depot = charger()
    actions = {"verifier": verifier, "types": types, "couverture": couverture, "--detail": detail}
    if commande not in actions:
        sys.exit(__doc__)
    return actions[commande](depot)


def lancer() -> None:
    """Point d'entrée de la commande `charte` installée avec kiln."""
    sys.exit(main())


if __name__ == "__main__":
    lancer()
