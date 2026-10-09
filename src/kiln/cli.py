"""kiln : orchestrateur de repos. Génère un projet, règle ses paramètres et le tient à jour."""

import argparse
import sys
from pathlib import Path

from kiln import check, dev, install, new, settings, update
from kiln.shell import KilnError, repo_root

EXIT_FAILURE = 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kiln", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    _add_new_command(commands)
    commands.add_parser("install", help="préparer le poste après un clone")
    _add_update_command(commands)
    dev_parser = commands.add_parser("dev", help="lancer le projet en local")
    dev_parser.add_argument("--containers", action="store_true", help="toute la pile dans podman")
    commands.add_parser("check", help="lancer les contrôles du projet")
    set_parser = commands.add_parser("set", help="afficher ou changer les paramètres du repo")
    set_parser.add_argument("assignments", nargs="*", metavar="clé=valeur")
    return parser


def _add_new_command(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    new_parser = commands.add_parser("new", help="générer un nouveau projet complet")
    new_parser.add_argument("directory", type=Path, help="dossier du projet à créer")
    new_parser.add_argument("--name", help="nom court (par défaut : nom du dossier)")
    new_parser.add_argument("--title", help="titre affiché")
    new_parser.add_argument("--description", help="une phrase sur le projet")
    new_parser.add_argument("--owner", help="compte GitHub propriétaire")
    new_parser.add_argument("--team", help="logins GitHub séparés par des virgules")
    new_parser.add_argument("--todo", metavar="GOAL", help="suivi docs/a-faire/ et sa boussole")
    new_parser.add_argument("--github", action="store_true", help="créer et protéger le dépôt")
    new_parser.add_argument("--no-install", action="store_true", help="ne rien installer")
    new_parser.add_argument("--template", help="source du modèle (chemin ou URL git)")


def _add_update_command(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    update_parser = commands.add_parser("update", help="mettre à jour modèle et dépendances")
    update_parser.add_argument("--no-template", action="store_true", help="garder l'architecture")
    update_parser.add_argument("--no-deps", action="store_true", help="garder les dépendances")
    update_parser.add_argument("--major", action="store_true", help="versions majeures comprises")


def _new_project_request(arguments: argparse.Namespace) -> new.NewProjectRequest:
    answers: dict[str, object] = {"nom": arguments.name or arguments.directory.name}
    if arguments.title:
        answers["titre"] = arguments.title
    if arguments.description:
        answers["description"] = arguments.description
    if arguments.todo:
        answers.update({"avec_a_faire": True, "boussole": arguments.todo})
    if arguments.owner:
        answers["proprietaire"] = arguments.owner
    if arguments.team:
        answers["equipe"] = [login.strip() for login in arguments.team.split(",")]
    return new.NewProjectRequest(
        destination=arguments.directory,
        answers=answers,
        template=arguments.template,
        should_install=not arguments.no_install,
        should_publish=arguments.github,
    )


def dispatch(arguments: argparse.Namespace) -> None:
    if arguments.command == "new":
        new.create_project(_new_project_request(arguments))
        return
    root = repo_root(Path.cwd())
    if arguments.command == "install":
        install.install_project(root)
    elif arguments.command == "update":
        update.update_project(
            root,
            should_update_template=not arguments.no_template,
            should_update_deps=not arguments.no_deps,
            allow_major=arguments.major,
        )
    elif arguments.command == "dev":
        dev.run_dev_servers(root, in_containers=arguments.containers)
    elif arguments.command == "check":
        check.check_project(root)
    elif arguments.command == "set":
        if arguments.assignments:
            settings.apply_settings(root, arguments.assignments)
        else:
            settings.show_settings(root)


def main() -> None:
    try:
        dispatch(build_parser().parse_args())
    except KilnError as error:
        print(f"kiln : {error}", file=sys.stderr)
        sys.exit(EXIT_FAILURE)
