"""Génère un projet complet (charte, outillage, Django + Nuxt) et le tient à jour."""

import argparse
import sys
from pathlib import Path

from init_repo import dev, installer, maj, nouveau, verifier
from init_repo.shell import InitRepoError, repo_root

EXIT_FAILURE = 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="init-repo", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    _add_new_command(commands)
    commands.add_parser("installer", help="préparer le poste après un clone")
    update_parser = commands.add_parser("maj", help="mettre à jour architecture et dépendances")
    update_parser.add_argument("--sans-modele", action="store_true", help="garder l'architecture")
    update_parser.add_argument("--sans-deps", action="store_true", help="garder les dépendances")
    commands.add_parser("dev", help="lancer le backend et le frontend")
    commands.add_parser("verifier", help="lancer les contrôles du backend et du frontend")
    return parser


def _add_new_command(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    new_parser = commands.add_parser("nouveau", help="générer un nouveau projet complet")
    new_parser.add_argument("dossier", type=Path, help="dossier du projet à créer")
    new_parser.add_argument("--nom", help="nom court (par défaut : nom du dossier)")
    new_parser.add_argument("--titre", help="titre affiché")
    new_parser.add_argument("--description", help="une phrase sur le projet")
    new_parser.add_argument("--proprietaire", help="compte GitHub propriétaire")
    new_parser.add_argument("--equipe", help="logins GitHub séparés par des virgules")
    new_parser.add_argument("--github", action="store_true", help="créer et protéger le dépôt")
    new_parser.add_argument("--sans-installation", action="store_true", help="ne rien installer")
    new_parser.add_argument("--modele", help="source du modèle (chemin ou URL git)")


def _new_project_request(arguments: argparse.Namespace) -> nouveau.NewProjectRequest:
    answers: dict[str, object] = {"nom": arguments.nom or arguments.dossier.name}
    if arguments.titre:
        answers["titre"] = arguments.titre
    if arguments.description:
        answers["description"] = arguments.description
    if arguments.proprietaire:
        answers["proprietaire"] = arguments.proprietaire
    if arguments.equipe:
        answers["equipe"] = [login.strip() for login in arguments.equipe.split(",")]
    return nouveau.NewProjectRequest(
        destination=arguments.dossier,
        answers=answers,
        template=arguments.modele,
        should_install=not arguments.sans_installation,
        should_publish=arguments.github,
    )


def dispatch(arguments: argparse.Namespace) -> None:
    if arguments.command == "nouveau":
        nouveau.create_project(_new_project_request(arguments))
        return
    root = repo_root(Path.cwd())
    if arguments.command == "installer":
        installer.install(root)
    elif arguments.command == "maj":
        maj.update_project(
            root,
            should_update_template=not arguments.sans_modele,
            should_update_deps=not arguments.sans_deps,
        )
    elif arguments.command == "dev":
        dev.run_dev_servers(root)
    elif arguments.command == "verifier":
        verifier.verify(root)


def main() -> None:
    try:
        dispatch(build_parser().parse_args())
    except InitRepoError as error:
        print(f"init-repo : {error}", file=sys.stderr)
        sys.exit(EXIT_FAILURE)
