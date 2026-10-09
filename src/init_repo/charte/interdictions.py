"""Interdictions : la règle est respectée partout, toute réintroduction échoue.

Chaque règle reçoit le dépôt et ses paramètres (`[interdictions.<nom>]` de charte.toml) et
renvoie la liste de ses échecs. Paramètres communs : `id` (identifiant de la règle dans la
charte du repo, affiché entre crochets), `fichiers` (motifs git), `message`.
"""

from __future__ import annotations

import ast
import re
from collections import defaultdict

from init_repo.charte.moteur import Depot, echec, hors_tests, justifie

PY = ["backend/*.py", "backend/**/*.py"]


def _code(depot: Depot, p: dict) -> list:
    return hors_tests(depot.suivis(p.get("fichiers", PY)))


def signaux_django(depot: Depot, p: dict) -> list[str]:
    """Les signaux Django sont interdits."""
    fautifs = [
        depot.rel(f)
        for f in _code(depot, p)
        if re.search(r"@receiver\b|from django\.db\.models\.signals import", f.read_text("utf-8"))
    ]
    return (
        [echec(p.get("id", "SIGNAUX"), p.get("message", "signaux Django interdits"), fautifs)]
        if fautifs
        else []
    )


def journalisation(depot: Depot, p: dict) -> list[str]:
    """Journalisation structurée obligatoire (structlog), `print()` banni hors tests."""
    stdlib, prints = [], []
    for f in depot.suivis(p.get("fichiers", PY)):
        texte = f.read_text("utf-8")
        if "logging.getLogger" in texte:
            stdlib.append(depot.rel(f))
        if "tests" not in f.parts and re.search(r"^\s*print\(", texte, re.M):
            prints.append(depot.rel(f))
    regle = p.get("id", "JOURNALISATION")
    sortie = []
    if stdlib:
        sortie.append(echec(regle, "logging.getLogger : utiliser structlog", stdlib))
    if prints:
        sortie.append(echec(regle, "print() banni hors script d'amorçage", prints))
    return sortie


def migrations_django(depot: Depot, p: dict) -> list[str]:
    """Migrations nommées `NNNN_nom.py`, numérotées sans trou ; une migration déjà présente sur
    la branche d'intégration n'est ni modifiée ni supprimée (la prod l'a peut-être appliquée)."""
    motif = p.get("fichiers", "backend/**/migrations/*.py")
    nom = re.compile(r"^(\d{4})_\w+\.py$")
    numeros: dict[str, list[int]] = defaultdict(list)
    mal_nommees = []
    for f in depot.suivis(motif, exclus=False):
        if f.name == "__init__.py":
            continue
        rel = depot.rel(f)
        if m := nom.match(f.name):
            numeros[rel.rsplit("/migrations/", 1)[0]].append(int(m.group(1)))
        else:
            mal_nommees.append(rel)
    for app, nums in numeros.items():
        if sorted(nums) != list(range(1, len(nums) + 1)):
            mal_nommees.append(f"{app}/migrations : numéros {sorted(nums)}")
    regle = p.get("id", "MIGRATIONS")
    sortie = []
    if mal_nommees:
        sortie.append(
            echec(regle, "migrations nommées NNNN_nom.py, numérotées sans trou", mal_nommees)
        )
    base = depot.git("merge-base", "HEAD", f"origin/{p.get('branche', 'develop')}").strip()
    if base:
        changees = depot.git("diff", "--name-status", "--diff-filter=MDR", base, "--", motif)
        reecrites = [
            l.split("\t")[1] for l in changees.splitlines() if not l.endswith("__init__.py")
        ]
        if reecrites:
            sortie.append(
                echec(
                    regle, "une migration fusionnée ne se modifie pas : en ajouter une", reecrites
                )
            )
    return sortie


SECRET = re.compile(r"token|secret|digest|signature|hash|otp|api_?key|verification_code", re.I)


def _noms(n: ast.expr) -> list[str]:
    if isinstance(n, ast.Name):
        return [n.id]
    if isinstance(n, ast.Attribute):
        return [n.attr, *_noms(n.value)]
    if (
        isinstance(n, ast.Subscript)
        and isinstance(n.slice, ast.Constant)
        and isinstance(n.slice.value, str)
    ):
        return [n.slice.value]
    return []


def temps_constant(depot: Depot, p: dict) -> list[str]:
    """Un secret ne se compare jamais par `==`/`!=` (le temps de réponse le trahit) :
    `hmac.compare_digest`. Exception justifiée par « # Temps constant : <raison> »."""
    fautifs = []
    for f in _code(depot, p):
        texte = f.read_text("utf-8")
        lignes = texte.splitlines()
        for n in ast.walk(ast.parse(texte)):
            if not isinstance(n, ast.Compare) or not any(
                isinstance(o, (ast.Eq, ast.NotEq)) for o in n.ops
            ):
                continue
            cotes = [n.left, *n.comparators]
            if any(isinstance(c, ast.Constant) for c in cotes):
                continue
            if any(SECRET.search(x) for c in cotes for x in _noms(c)) and not justifie(
                lignes, n.lineno, "Temps constant"
            ):
                fautifs.append(f"{depot.rel(f)}:{n.lineno}  {ast.unparse(n)[:70]}")
    if not fautifs:
        return []
    return [echec(p.get("id", "TEMPS-CONSTANT"), "comparer un secret par compare_digest", fautifs)]


PERSO = re.compile(
    r"^(e_?mail|.*_email|phone|.*_phone|first_name|last_name|full_name|name|ip|ip_address|client_ip|address)$"
)
JOURNAUX = re.compile(r"^(logger|log|_logger|audit_logger|security_logger|structlog)$")
METHODES = {"debug", "info", "warning", "warn", "error", "exception", "critical", "bind"}


def donnees_perso(depot: Depot, p: dict) -> list[str]:
    """Aucune donnée personnelle dans un journal : l'identifiant, jamais la personne.
    Exception justifiée par « # Donnée perso : <raison> »."""
    fautifs = []
    for f in _code(depot, p):
        texte = f.read_text("utf-8")
        lignes = texte.splitlines()
        for n in ast.walk(ast.parse(texte)):
            if not (
                isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute)
                and n.func.attr in METHODES
            ):
                continue
            cible = n.func.value
            if not JOURNAUX.match(
                cible.id if isinstance(cible, ast.Name) else getattr(cible, "attr", "")
            ):
                continue
            cles = [k.arg for k in n.keywords if k.arg and PERSO.match(k.arg)]
            for v in [*n.args, *(k.value for k in n.keywords)]:
                if isinstance(v, ast.Dict):
                    cles += [
                        k.value
                        for k in v.keys
                        if isinstance(k, ast.Constant) and PERSO.match(str(k.value))
                    ]
            if cles and not justifie(lignes, n.lineno, "Donnée perso"):
                fautifs.append(f"{depot.rel(f)}:{n.lineno}  {', '.join(cles)}")
    if not fautifs:
        return []
    return [echec(p.get("id", "DONNEES-PERSO"), "donnée personnelle dans un journal", fautifs)]


def style_vue(depot: Depot, p: dict) -> list[str]:
    """Aucune balise <style> (en début de ligne) dans un composant .vue."""
    bloc = re.compile(r"^<style\b", re.M)
    fautifs = [
        depot.rel(f)
        for f in depot.suivis(p.get("fichiers", "frontend/app/**/*.vue"))
        if bloc.search(f.read_text("utf-8"))
    ]
    message = p.get(
        "message", "aucune balise <style> dans un .vue : classes Tailwind ou feuille partagée"
    )
    return [echec(p.get("id", "STYLE-1"), message, fautifs)] if fautifs else []


def renvois_audit(depot: Depot, p: dict) -> list[str]:
    """Aucun renvoi à un identifiant d'audit dans le code : un commentaire dit la contrainte au
    présent, l'historique va dans le commit. `prefixes` : préfixes des constats (regex)."""
    suffixes = set(
        p.get("suffixes", [".py", ".ts", ".vue", ".mjs", ".js", ".cjs", ".yml", ".yaml", ".sh"])
    )
    exclus = re.compile(p.get("exclus", r"^docs/"))
    motif = re.compile(
        rf"\b(?:audits?|constats?)\s[A-Z]{{1,4}}\d|\b(?:{p['prefixes']})-\d{{2}}\b|\baudits?\s(?:frontend|backend)\b"
    )
    fautifs = []
    for f in depot.suivis([], exclus=False):
        rel = depot.rel(f)
        if f.suffix not in suffixes or exclus.search(rel):
            continue
        for i, ligne in enumerate(f.read_text("utf-8").splitlines(), start=1):
            if motif.search(ligne):
                fautifs.append(f"{rel}:{i}: {ligne.strip()[:100]}")
    message = "renvoi à un identifiant d'audit : dire la contrainte au présent, l'historique va dans le commit"
    return [echec(p.get("id", "RENVOIS-AUDIT"), message, fautifs)] if fautifs else []


def fichiers_interdits(depot: Depot, p: dict) -> list[str]:
    """Fichiers qui ne doivent pas (ou plus) exister : `chemins`, `message`."""
    presents = [c for c in p["chemins"] if (depot.racine / c).exists()]
    return (
        [echec(p.get("id", "FICHIERS"), p.get("message", "fichier interdit"), presents)]
        if presents
        else []
    )


def copies(depot: Depot, p: dict) -> list[str]:
    """Copies qui doivent rester identiques à leur original : `paires` = [[original, copie], …]."""
    sortie = []
    for original, copie in p["paires"]:
        a, b = depot.racine / original, depot.racine / copie
        if not (a.exists() and b.exists() and a.read_bytes() == b.read_bytes()):
            sortie.append(
                echec(
                    p.get("id", "COPIES"),
                    f"{copie} doit être une copie exacte de {original}",
                    [original, copie],
                )
            )
    return sortie


def _yaml(chemin) -> dict:
    try:
        import yaml
    except ImportError:
        import json
        import subprocess

        code = "import json, sys, yaml; print(json.dumps(yaml.safe_load(open(sys.argv[1]))))"
        sortie = subprocess.run(
            ["uv", "run", "--no-project", "--with", "pyyaml", "python", "-c", code, str(chemin)],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        return json.loads(sortie)
    return yaml.safe_load(chemin.read_text("utf-8"))


def compose_profils(depot: Depot, p: dict) -> list[str]:
    """Services d'un fichier compose qui doivent être derrière un profil (ex. un intercepteur de
    courrier qui avalerait tout) : `fichier`, `services`. Lu par PyYAML, ou par `uv` s'il manque."""
    compose = _yaml(depot.racine / p["fichier"])
    fautifs = [
        n
        for n, s in compose.get("services", {}).items()
        if n in p["services"] and not s.get("profiles")
    ]
    message = p.get("message", "service à mettre derrière un profil (`profiles: dev`)")
    return [echec(p.get("id", "COMPOSE"), message, fautifs)] if fautifs else []


REGLES = {
    "signaux-django": signaux_django,
    "journalisation": journalisation,
    "migrations-django": migrations_django,
    "temps-constant": temps_constant,
    "donnees-perso": donnees_perso,
    "style-vue": style_vue,
    "renvois-audit": renvois_audit,
    "fichiers-interdits": fichiers_interdits,
    "copies": copies,
    "compose-profils": compose_profils,
}
