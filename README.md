# init-repo

Génère un projet complet en une commande, puis le tient à jour :

- charte de code (`CLAUDE.md` à la racine, dans `backend/` et `frontend/`) ;
- outillage partagé : `.claude/`, `.vscode/`, `.editorconfig`, `.gitattributes`, `.gitignore`,
  modèle de PR, `CODEOWNERS`, pre-commit (dont le refus de commiter sur `main` et `develop`) ;
- backend Django + Django Ninja (uv, mypy strict, ruff, pytest) ;
- frontend Nuxt 4 + Vue 3 + Tailwind 4 (pnpm, TypeScript strict) ;
- au besoin, le dépôt GitHub privé, avec `main` et `develop` protégées.

Le modèle vit dans [`template/`](template/), servi par [Copier](https://copier.readthedocs.io) :
chaque projet garde dans `.copier-answers.yml` ses réponses et la version du modèle dont il
part, ce qui permet de lui rapporter les évolutions sans écraser ses modifications locales.

## Installation

Prérequis : [uv](https://docs.astral.sh/uv/), [pnpm](https://pnpm.io/) (avec Node 24), git, et
[gh](https://cli.github.com) pour l'option `--github`.

```sh
uv tool install git+https://github.com/antoine-tena/init-repo
```

Mettre l'outil lui-même à jour : `uv tool upgrade init-repo`.

## Commandes

| Commande | Rôle |
|---|---|
| `init-repo nouveau <dossier>` | Génère le projet, verrouille et installe les dépendances, crée le premier commit sur `main`. |
| `init-repo installer` | Prépare un poste après un clone : dépendances, `backend/.env`, migrations, pre-commit. Relançable. |
| `init-repo dev` | Lance le backend (:8000) et le frontend (:3000) ensemble. |
| `init-repo maj` | Sur une branche, arbre propre : rapporte les évolutions du modèle, met à jour les dépendances, puis lance les contrôles. |
| `init-repo verifier` | Ruff, mypy et pytest côté backend, contrôle des types côté frontend. |

Options de `nouveau` : `--nom`, `--titre`, `--description`, `--proprietaire`,
`--equipe login1,login2` (relecteurs du `CODEOWNERS`), `--github` (crée le dépôt privé,
protège `main` et `develop`, invite l'équipe), `--sans-installation`, `--modele <chemin ou URL>`.
Les questions sans option sont posées dans le terminal.

Options de `maj` : `--sans-modele` (dépendances seulement), `--sans-deps` (architecture
seulement). Les conflits entre le modèle et une modification locale sont marqués dans le
fichier (`<<<<<<<`) : les résoudre, puis commiter et ouvrir une PR.

## Faire évoluer le modèle

Modifier `template/` sur une branche, ouvrir une PR. Une fois fusionnée dans `main`, chaque
projet la récupère par `init-repo maj`. Seuls les fichiers en `.jinja` sont interprétés ; les
questions sont dans [`copier.yml`](copier.yml).

```sh
uv run pytest            # le modèle se génère et se remplit correctement
uv run ruff check . && uv run mypy src tests
```
