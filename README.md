# kiln

Orchestrateur de repos : génère un projet complet en une commande, règle ses paramètres et le
tient à jour (architecture et dépendances) :

- charte de code (`CLAUDE.md` à la racine, dans `backend/` et `frontend/`), dont les règles
  contrôlables sont décrites dans `charte.toml` et vérifiées par la commande `charte` ;
- outillage partagé : `.claude/` (plugins `pile-django` et `pile-nuxt`, variables `PROJET_*`),
  `.vscode/`, `.editorconfig`, `.gitattributes`, `.gitignore`, modèle de PR, `CODEOWNERS`,
  pre-commit (ruff, charte, refus de commiter sur `main` et `develop`) ;
- CI GitHub (`.github/workflows/ci.yml`) qui appelle les workflows réutilisables des dotfiles
  d'antoine-tena : backend, frontend, charte, audit des dépendances ;
- en option (`--todo "<boussole>"`), le suivi du travail dans `docs/a-faire/` ;
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
uv tool install git+https://github.com/antoine-tena/kiln
```

Installe deux commandes : `kiln` et `charte`. Mettre l'outil à jour :
`uv tool upgrade kiln`. Python 3.14 est requis ; uv le télécharge au besoin.

## Commandes

| Commande | Rôle |
|---|---|
| `kiln new <directory>` | Génère le projet, verrouille et installe les dépendances, crée le premier commit sur `main`. |
| `kiln install` | Prépare un poste après un clone : dépendances, `backend/.env`, migrations, pre-commit. Relançable. |
| `kiln dev` | Lance le backend (:8000) et le frontend (:3000) ensemble. |
| `kiln update` | Sur une branche, arbre propre : rapporte les évolutions du modèle, met à jour les dépendances, puis lance les contrôles. |
| `kiln check` | Ruff, mypy et pytest côté backend, contrôle des types côté frontend. |
| `charte` | Vérifie le repo contre son `charte.toml` (`charte --detail`, `charte types`, `charte couverture`). |

Options de `new` : `--name`, `--title`, `--description`, `--owner`,
`--team login1,login2` (relecteurs du `CODEOWNERS`), `--todo "<boussole>"`, `--github` (crée
le dépôt privé, protège `main` et `develop`, invite l'équipe), `--no-install`,
`--template <chemin ou URL>`. Les questions sans option sont posées dans le terminal.

Options de `update` : `--no-template` (dépendances seulement), `--no-deps` (architecture
seulement). Les conflits entre le modèle et une modification locale sont marqués dans le
fichier (`<<<<<<<`) : les résoudre, puis commiter et ouvrir une PR.

## Faire évoluer le modèle

Modifier `template/` sur une branche, ouvrir une PR. Une fois fusionnée dans `main`, chaque
projet la récupère par `kiln update`. Seuls les fichiers en `.jinja` sont interprétés ; les
questions sont dans [`copier.yml`](copier.yml).

```sh
uv run pytest            # le modèle se génère et se remplit correctement
uv run ruff check . && uv run mypy src tests
```

## Moteur de charte

`src/kiln/charte/` lit le `charte.toml` à la racine du repo. Interdictions (`signaux-django`,
`journalisation`, `migrations-django`, `temps-constant`, `donnees-perso`, `style-vue`,
`renvois-audit`, `fichiers-interdits`, `copies`, `compose-profils`), cliquets et planchers
(`taille-fichier`, `routes-longues`, `verrous-django`, `occurrences`, `densite-tests`),
`[types]` (mypy en cliquet) et `[couverture]` (planchers de pytest-cov) ; paramètres dans la
docstring de chaque règle. Règle propre à un repo : un module listé dans `regles_locales`,
avec `verifier(depot, params) -> list[str]`.

La CI des projets dépend des workflows des dotfiles d'antoine-tena, partagés avec les dépôts de
ce compte : un projet généré sous un autre compte doit remplacer `ci.yml`.
