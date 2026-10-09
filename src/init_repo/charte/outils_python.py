"""Cliquets mesurés par des outils Python : écarts de typage (mypy) et couverture (pytest-cov)."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

from init_repo.charte.moteur import Depot


def types(depot: Depot) -> int:
    """`[types]` : `dossier` (projet uv), `paquets` (passés à mypy par -p), `budget` (écarts
    tolérés, qui ne fait que baisser), `env` (variables attendues par les réglages du projet,
    surchargées par l'environnement)."""
    p = depot.config["types"]
    env = {**p.get("env", {}), **os.environ}
    commande = ["uv", "run", "mypy", *(a for paquet in p["paquets"] for a in ("-p", paquet))]
    resultat = subprocess.run(
        commande,
        cwd=depot.racine / p.get("dossier", "backend"),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    sortie = resultat.stdout + resultat.stderr
    trouve = re.search(r"Found (\d+) errors? in \d+ files?", sortie)
    if trouve:
        ecarts = int(trouve.group(1))
    elif "no issues found" in sortie:
        ecarts = 0
    else:
        print(sortie, file=sys.stderr)
        print("mypy n'a pas pu s'exécuter : voir la sortie ci-dessus.", file=sys.stderr)
        return 2
    budget = p.get("budget", 0)
    if ecarts > budget:
        print(sortie, file=sys.stderr)
        print(
            f"\nTypage : {ecarts} écarts relevés par mypy, pour un plafond de {budget}.\n"
            "Corriger les écarts ajoutés, ou les annoter avec le motif.",
            file=sys.stderr,
        )
        return 1
    if ecarts < budget:
        print(
            f"Typage : {ecarts} écarts (plafond {budget}) — abaisser `budget` de [types] à {ecarts} (charte.toml)."
        )
        return 0
    print(f"Typage : {ecarts} écarts, le plafond est tenu ({', '.join(p['paquets'])}).")
    return 0


def couverture(depot: Depot) -> int:
    """`[couverture]` : `rapport` (coverage.xml de `pytest --cov --cov-report=xml`), `planchers`
    (pourcentage de lignes couvertes du `TOTAL` et des modules critiques, qui ne fait que
    monter), `marge` (points au-dessus du plancher avant de suggérer de le relever)."""
    p = depot.config["couverture"]
    rapport = depot.racine / p["rapport"]
    if not rapport.exists():
        print(f"{rapport} introuvable : lancer d'abord `uv run pytest --cov --cov-report=xml`.")
        return 1
    racine = ET.parse(rapport).getroot()
    taux = {"TOTAL": float(racine.get("line-rate", 0)) * 100}
    for element in racine.iter("class"):
        taux[element.get("filename", "")] = float(element.get("line-rate", 0)) * 100
    marge = p.get("marge", 2)
    problemes, a_relever = [], []
    for nom, plancher in p["planchers"].items():
        mesure = taux.get(nom)
        if mesure is None:
            problemes.append(
                f"{nom} : absent du rapport (fichier renommé ? mettre à jour [couverture.planchers])."
            )
        elif mesure < plancher:
            problemes.append(
                f"{nom} : {mesure:.1f} % de lignes couvertes, sous le plancher de {plancher} %."
            )
        elif mesure >= plancher + marge:
            a_relever.append(
                f"{nom} : {mesure:.1f} % — relever [couverture.planchers] « {nom} » à {int(mesure)}."
            )
    if a_relever:
        print("Couverture en hausse, planchers à relever (le contrôle reste vert) :")
        print("\n".join(f"  {l}" for l in a_relever))
    if problemes:
        print("Couverture sous les planchers :")
        print("\n".join(f"  {l}" for l in problemes))
        return 1
    print("Couverture : tous les planchers sont tenus.")
    return 0
