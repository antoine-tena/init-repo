# kiln

Orchestrateur de repos : génère un projet complet en une commande, règle ses paramètres à tout
moment et le tient à jour (architecture et dépendances). Jamais pip ni docker : uv pour Python,
pnpm pour JavaScript, podman pour les conteneurs.

Un projet généré contient :

- la stack choisie, conseillée selon le type de projet (voir ci-dessous) ;
- sa charte de code (`CLAUDE.md` à la racine, dans `backend/` et `frontend/`), dont les règles
  contrôlables sont décrites dans `charte.toml` et vérifiées par la commande `charte` ;
- l'outillage partagé : `.claude/` (plugins et variables `PROJET_*`), `.vscode/`, `.editorconfig`,
  `.gitattributes`, `.gitignore`, modèle de PR, `CODEOWNERS`, pre-commit (ruff, ESLint, charte,
  refus de commiter sur `main` et `develop`) ;
- la CI GitHub (`.github/workflows/ci.yml`), qui appelle les workflows réutilisables de kiln ;
- en option : le suivi du travail (`docs/a-faire/`), les conteneurs podman, le dépôt GitHub
  privé avec `main` et `develop` protégées et les correctifs de sécurité Dependabot.

Le modèle vit dans [`template/`](template/), servi par [Copier](https://copier.readthedocs.io) :
chaque projet garde dans `.copier-answers.yml` ses réponses et la version du modèle dont il
part, ce qui permet de lui rapporter les évolutions sans écraser ses modifications locales.

## Installation

Prérequis : [uv](https://docs.astral.sh/uv/) et git ; [pnpm](https://pnpm.io/) (Node 24) pour un
front JavaScript ; [podman](https://podman.io/) pour les conteneurs ; [gh](https://cli.github.com)
pour `--github`.

```sh
uv tool install git+https://github.com/antoine-tena/kiln
```

Installe deux commandes : `kiln` et `charte`. Mettre l'outil à jour : `uv tool upgrade kiln`.
Python 3.14 est requis ; uv le télécharge au besoin. Au premier `kiln install`, kiln demande le
système du poste (Linux, WSL ou macOS) et le garde dans `~/.config/kiln/config.toml`, avec
`proprietaire` et `equipe` par défaut si on les y ajoute.

## Commandes

| Commande | Rôle |
|---|---|
| `kiln new <directory>` | Questionnaire (type de projet, stack conseillée, podman…), génération, verrous, installation, premier commit sur `main`. |
| `kiln install` | Prépare un poste après un clone : outils (pre-commit avec pre-commit-uv, podman-compose), dépendances, `backend/.env`, migrations, pre-commit. Relançable. |
| `kiln dev` | Lance les serveurs de la stack ; `--containers` : toute la pile dans podman. |
| `kiln check` | Ruff, mypy et pytest pour chaque projet Python, ESLint et les types côté front, puis la charte. |
| `kiln set` | Sans argument, affiche les paramètres du repo. `kiln set clé=valeur…` les change (équipe, frameworks, podman, a-faire…) : le repo est régénéré, un framework retiré emporte ses fichiers. |
| `kiln update` | Évolutions du modèle, mises à jour compatibles des dépendances, puis contrôles. `--major` : versions majeures comprises. `--no-template`, `--no-deps` pour n'en faire qu'une partie. |
| `kiln update --all` | Tous les repos kiln du dossier de code (`~/code`, réglable par `dossier_code`) : pour chacun, un worktree depuis la branche d'intégration, la mise à jour, des commits de dix fichiers au plus, une PR (en brouillon si les contrôles échouent). L'arbre principal ne change jamais de branche. |
| `kiln status` | État des repos kiln du dossier de code : branche, arbre propre ou non, modèle à jour ou en retard, stack. |
| `charte` | Vérifie le repo contre son `charte.toml` (`charte --detail`, `charte types`, `charte couverture`). |

`set` et `update` travaillent sur une branche, arbre propre ; les conflits entre le modèle et une
modification locale sont marqués dans le fichier (`<<<<<<<`). Relire, commiter, ouvrir une PR.

Options de `new` : `--type`, `--backend`, `--frontend`, `--podman`, `--name`, `--title`,
`--description`, `--owner`, `--team login1,login2`, `--todo "<boussole>"`, `--github`,
`--no-install`, `--template <chemin ou URL>`. Les questions sans option sont posées dans le
terminal.

## Conseil de stack

Le type de projet précoche une stack, que l'on change à la question suivante ou plus tard par
`kiln set backend=… frontend=…`.

| Type de projet | Backend conseillé | Frontend conseillé |
|---|---|---|
| Application complète (`app`) | Django + Django Ninja | Nuxt + Vue |
| API seule (`api`) | FastAPI | aucun |
| Site de contenu (`site`) | aucun | Astro |
| Tableau de bord de données (`tableau`) | Données Python (polars, marimo, Plotly) | Streamlit |
| Analyse de données (`analyse`) | Données Python | aucun |

Backends : `django`, `fastapi`, `data`, `aucun`. Frontends : `nuxt`, `next`, `astro`,
`streamlit`, `dash`, `aucun`. Toutes les combinaisons sont générées et vérifiées par les tests.

## Mises à jour des dépendances

`kiln update` fait des mises à jour compatibles : uv reste dans les bornes du `pyproject.toml`
(même version majeure), pnpm ne monte que les dépendances qui gardent leur majeure et annonce les
autres. `kiln update --major` relève les bornes à la dernière version, prend les dernières
versions pnpm et met à jour les crochets pre-commit. Les contrôles suivent toujours : une montée
qui casse quelque chose est signalée avant le commit. Dependabot ne propose que les correctifs de
sécurité.

## Faire évoluer le modèle

Modifier `template/` sur une branche, ouvrir une PR. Une fois fusionnée dans `main`, chaque
projet la récupère par `kiln update`. Seuls les fichiers en `.jinja` sont interprétés ; un dossier
`{% if … %}nom{% endif %}` n'existe que si la condition tient ; les questions sont dans
[`copier.yml`](copier.yml) et les macros partagées (chaînes Python au format de ruff) dans
[`macros.jinja`](macros.jinja).

```sh
uv run pytest            # chaque stack se génère en fichiers valides
uv run ruff check . && uv run mypy src tests
```

## Moteur de charte

`src/kiln/charte/` lit le `charte.toml` à la racine du repo. Interdictions (`signaux-django`,
`journalisation`, `migrations-django`, `temps-constant`, `donnees-perso`, `style-vue`,
`renvois-audit`, `fichiers-interdits`, `copies`, `compose-profils`, `outils-interdits` : jamais
pip ni docker, ni leurs fichiers), cliquets et planchers
(`taille-fichier`, `routes-longues`, `verrous-django`, `occurrences`, `densite-tests`),
`[types]` (mypy en cliquet) et `[couverture]` (planchers de pytest-cov) ; paramètres dans la
docstring de chaque règle. Règle propre à un repo : un module listé dans `regles_locales`,
avec `verifier(depot, params) -> list[str]`. La liste des règles non vérifiées
(`scripts/ci/charte-non-verifiee.txt`) est recalculée par kiln à chaque `set` et `update`.

## Workflows réutilisables

kiln est public : ses workflows servent à n'importe quel dépôt, quel que soit son compte
(`uses: antoine-tena/kiln/.github/workflows/<nom>.yml@main`). Jamais pip ni docker : uv pour
Python, podman pour les conteneurs (bases de test comprises), podman-compose installé par uv.

| Workflow | Rôle |
|---|---|
| `django.yml` | Backend Django : ruff, `charte types`, migrations manquantes, pytest et couverture, contre PostgreSQL et Redis lancés par podman. |
| `python.yml` | Tout projet uv (FastAPI, données, Streamlit, Dash) : ruff, mypy, pytest avec un plancher de couverture ; PostgreSQL en option. |
| `pnpm.yml` | Front pnpm (Nuxt, Next.js, Astro) : scripts de `package.json` dans l'ordre ; pnpm pris dans `packageManager`. |
| `charte.yml` | Règles de `charte.toml`. |
| `securite.yml` | `uv audit` et `pnpm audit`. |
| `contrat-api.yml` | `openapi.json` et types du front à jour du code. |
| `infra.yml` | Images (`podman build`), actionlint, shellcheck, Caddyfile, compose (podman-compose). |
| `sbom.yml` | Nomenclatures CycloneDX du back et du front. |
| `mutation.yml` | Tests par mutation (mutmut), jamais bloquants. |
| `vercel.yml` | Déploiement du front sur Vercel. |

Actions : `actions/charte` (installe kiln et `charte`), `actions/services` (PostgreSQL et Redis
par podman, `DATABASE_URL` et `REDIS_URL` posées).
