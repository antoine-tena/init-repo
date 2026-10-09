"""Compteurs des cliquets (`[cliquets.<nom>]`, plafond `budget` qui ne fait que baisser) et des
planchers (`[planchers.<nom>]`, valeur `plancher` qui ne fait que monter).

Chaque compteur reçoit le dépôt et ses paramètres et renvoie (valeur, détail).
"""

from __future__ import annotations

import ast
import re

from kiln.charte.moteur import Depot, hors_tests


def taille_fichier(depot: Depot, p: dict) -> tuple[int, list[str]]:
    """`max_lignes` (300) lignes au plus par fichier ; les fichiers engendrés ne comptent pas."""
    suffixes = set(p.get("suffixes", [".py", ".ts", ".vue", ".css", ".mjs"]))
    plafond = p.get("max_lignes", 300)
    fautifs = []
    for f in depot.suivis(p["fichiers"]):
        if f.suffix not in suffixes or depot.engendre(f):
            continue
        n = len(f.read_text("utf-8").splitlines())
        if n > plafond:
            fautifs.append(f"{n:5d}  {depot.rel(f)}")
    return len(fautifs), sorted(fautifs, reverse=True)


def routes_longues(depot: Depot, p: dict) -> tuple[int, list[str]]:
    """Vues de plus de `max_lignes` (15) lignes, repérées par leur décorateur (`decorateur`,
    regex ; par défaut celui de django-ninja)."""
    decorateur = re.compile(p.get("decorateur", r"\s*@(api|router)\.(get|post|put|patch|delete)"))
    plafond = p.get("max_lignes", 15)
    fautifs = []
    for f in depot.suivis(p.get("fichiers", ["backend/*/api/*.py", "backend/*/api.py"])):
        lignes = f.read_text("utf-8").splitlines()
        for i, ligne in enumerate(lignes):
            if not decorateur.match(ligne):
                continue
            j = i
            while j < len(lignes) and not re.match(r"\s*def ", lignes[j]):
                j += 1
            if j >= len(lignes):
                continue
            retrait = len(lignes[j]) - len(lignes[j].lstrip())
            k = j + 1
            while k < len(lignes) and not (
                lignes[k].strip() and len(lignes[k]) - len(lignes[k].lstrip()) <= retrait
            ):
                k += 1
            if k - j > plafond:
                fautifs.append(f"{k - j:5d}  {depot.rel(f)}:{j + 1}  {lignes[j].strip()[:60]}")
    return len(fautifs), sorted(fautifs, reverse=True)


def verrous_django(depot: Depot, p: dict) -> tuple[int, list[str]]:
    """`select_for_update` sans `nowait`/`skip_locked` ni justification « # Verrou bloquant : »
    dans les 8 lignes au-dessus. Analyse syntaxique : une docstring n'est pas un verrou."""
    fautifs = []
    for f in hors_tests(depot.suivis(p.get("fichiers", ["backend/*.py", "backend/**/*.py"]))):
        texte = f.read_text("utf-8")
        lignes = texte.splitlines()
        for n in ast.walk(ast.parse(texte)):
            if not (isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "select_for_update"):
                continue
            garde = any(k.arg in {"nowait", "skip_locked"} for k in n.keywords)
            au_dessus = "\n".join(lignes[max(0, n.lineno - 9) : n.lineno])
            if not garde and not re.search(r"#\s*Verrou bloquant\s*:", au_dessus):
                fautifs.append(f"{depot.rel(f)}:{n.lineno}")
    return len(fautifs), fautifs


def occurrences(depot: Depot, p: dict) -> tuple[int, list[str]]:
    """Nombre d'occurrences d'un texte (`motif`, littéral) dans des fichiers : par exemple
    `timezone.now()` dans les tests, où l'horloge doit être figée."""
    fautifs = []
    for f in depot.suivis(p["fichiers"]):
        n = f.read_text("utf-8").count(p["motif"])
        if n:
            fautifs.append(f"{n:4d}  {depot.rel(f)}")
    return sum(int(o.split()[0]) for o in fautifs), sorted(fautifs, reverse=True)


def densite_tests(depot: Depot, p: dict) -> tuple[int, list[str]]:
    """Lignes de test pour mille lignes de code (fichiers engendrés exclus). Les fichiers de
    test finissent par un des `suffixes_tests`."""
    suffixes = set(p.get("suffixes", [".ts", ".vue", ".mjs"]))
    tests_fin = tuple(p.get("suffixes_tests", [".spec.ts", ".nuxt.spec.ts"]))
    code = tests = 0
    for f in depot.suivis(p["fichiers"]):
        if f.suffix not in suffixes or depot.engendre(f):
            continue
        n = len(f.read_text("utf-8").splitlines())
        if f.name.endswith(tests_fin):
            tests += n
        else:
            code += n
    ratio = round(1000 * tests / code) if code else 0
    return ratio, [f"{tests} lignes de test pour {code} lignes de code ({ratio}/1000)"]


COMPTEURS = {
    "taille-fichier": taille_fichier,
    "routes-longues": routes_longues,
    "verrous-django": verrous_django,
    "occurrences": occurrences,
    "densite-tests": densite_tests,
}
