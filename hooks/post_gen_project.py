#!/usr/bin/env python

import os
import shutil
import subprocess
import json
from pathlib import Path
from typing import List, Optional


PROJECT_DIRECTORY = Path(os.path.realpath(os.path.curdir))
GIT_EXE: Optional[str] = shutil.which("git")
GH_EXE: Optional[str] = shutil.which("gh")
UV_EXE: Optional[str] = shutil.which("uv")
PRE_COMMIT_EXE: Optional[str] = shutil.which("pre-commit")


def run(cmd: List[str], check: bool = True, cwd: Optional[Path] = None, **popen_kwargs) -> subprocess.CompletedProcess:
    """Exécute une commande système."""
    return subprocess.run(cmd, check=check, cwd=str(cwd) if cwd else None, **popen_kwargs)


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    """Exécute une commande git dans PROJECT_DIRECTORY."""
    if GIT_EXE is None:
        raise RuntimeError("git executable not found in PATH.")
    return run([GIT_EXE, "-C", str(PROJECT_DIRECTORY), *args], check=check)


def has_remote_origin() -> bool:
    """Retourne True si un remote 'origin' est configuré."""
    if GIT_EXE is None:
        return False
    cp = subprocess.run(
        [GIT_EXE, "-C", str(PROJECT_DIRECTORY), "remote", "get-url", "origin"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return cp.returncode == 0


def is_inside_git_repo() -> bool:
    if GIT_EXE is None:
        return False
    cp = subprocess.run(
        [GIT_EXE, "-C", str(PROJECT_DIRECTORY), "rev-parse", "--is-inside-work-tree"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    return (cp.returncode == 0) and (cp.stdout.strip().lower() == "true")


# ---------- HELPERS UNIFORMISÉS ----------
def slug_dir_path(project_slug: str) -> str:
    """
    Retourne le chemin du dossier 'slug' selon le layout :
      - layout == 'src'  -> 'src/<slug>'
      - layout == 'flat' -> '<slug>'
    """
    layout = "{{cookiecutter.layout}}"
    return os.path.join("src", project_slug) if layout == "src" else project_slug


def _fs_remove_paths(paths: list[str]) -> list[str]:
    """
    Supprime les chemins (FS) s'ils existent et retourne la liste de ceux effectivement supprimés.
    On choisit la suppression FS + `git add -A` ensuite pour rester cohérents.
    """
    removed: list[str] = []
    for p in paths:
        if not p:
            continue
        abs_p = PROJECT_DIRECTORY / p
        if abs_p.exists():
            if abs_p.is_dir():
                shutil.rmtree(abs_p, ignore_errors=True)
            else:
                try:
                    abs_p.unlink()
                except FileNotFoundError:
                    pass
            removed.append(p)
    return removed


def remove_on_main(paths: list[str]) -> None:
    """
    Se place sur 'main', supprime (FS) les chemins s'ils existent, puis commit la suppression.
    Ignore poliment si rien à faire.
    """
    try:
        git("checkout", "main", check=True)
    except subprocess.CalledProcessError:
        return

    removed = _fs_remove_paths(paths)
    if not removed:
        return

    git("add", "-A", check=True)
    try:
        git("commit", "-m", "main: remove package slug and tests for workshop scaffolding", check=True)
    except subprocess.CalledProcessError:
        pass


def remove_on_all_but_main(paths: list[str]) -> None:
    """
    Supprime (FS) les chemins donnés de toutes les branches locales sauf 'main'.
    """
    if GIT_EXE is None:
        return

    cp = subprocess.run(
        [GIT_EXE, "-C", str(PROJECT_DIRECTORY), "branch", "--format=%(refname:short)"],
        check=True,
        capture_output=True,
        text=True,
    )
    branches = [b.strip() for b in cp.stdout.splitlines() if b.strip()]
    if not branches:
        return

    for br in branches:
        if br == "main":
            continue
        try:
            git("checkout", br, check=True)
        except subprocess.CalledProcessError:
            continue

        removed = _fs_remove_paths(paths)
        if not removed:
            continue

        git("add", "-A", check=True)
        try:
            git("commit", "-m", f"{br}: remove selected files", check=True)
        except subprocess.CalledProcessError:
            pass

    # Revenir sur main à la fin
    try:
        git("checkout", "main", check=True)
    except subprocess.CalledProcessError:
        pass


def _replace_readme(project_name: str) -> None:
    """
    Remplace le README.md courant par un modèle spécifique à la branche.
    """
    readme_path = PROJECT_DIRECTORY / "README.md"
    # Suppression FS (pas de git rm ici, on standardise l'approche)
    try:
        readme_path.unlink()
    except FileNotFoundError:
        pass

    readme_path.write_text(
        f"# {project_name} — To do\n\n"
        "## This README is for your instructions \n\n",
        encoding="utf-8",
    )
    git("add", "README.md", check=True)
    git("commit", "-m", f"docs: branch-specific README for {project_name}", check=True)


def create_difficulty_branches(branches: list[str], project_name: str) -> None:
    """
    Crée les branches de difficulté à partir de main, ajoute un commit vide, et remplace le README.
    """
    try:
        git("checkout", "main", check=True)
    except subprocess.CalledProcessError:
        pass

    for br in branches:
        git("checkout", "-b", br, check=True)
        git("commit", "--allow-empty", "-m", f"Initialize {br} branch", check=True)
        _replace_readme(project_name)

    # Revenir sur main
    try:
        git("checkout", "main", check=True)
    except subprocess.CalledProcessError:
        pass


# ---------- FIN HELPERS UNIFORMISÉS ----------

if __name__ == "__main__":
    # Optional assets
    if "{{cookiecutter.include_github_actions}}" != "y":
        if (PROJECT_DIRECTORY / ".github").exists():
            shutil.rmtree(PROJECT_DIRECTORY / ".github", ignore_errors=True)

    if "{{cookiecutter.dockerfile}}" != "y":
        try:
            (PROJECT_DIRECTORY / "Dockerfile").unlink()
        except FileNotFoundError:
            pass

    if "{{cookiecutter.codecov}}" != "y":
        try:
            (PROJECT_DIRECTORY / "codecov.yaml").unlink()
        except FileNotFoundError:
            pass

    if "{{cookiecutter.devcontainer}}" != "y":
        if (PROJECT_DIRECTORY / ".devcontainer").exists():
            shutil.rmtree(PROJECT_DIRECTORY / ".devcontainer", ignore_errors=True)

    if "{{cookiecutter.render}}" != "y":
        try:
            (PROJECT_DIRECTORY / "render.yaml").unlink()
        except FileNotFoundError:
            pass

    if "{{cookiecutter.makefile}}" != "y":
        try:
            (PROJECT_DIRECTORY / "Makefile").unlink()
        except FileNotFoundError:
            pass

    # Layout handling
    if "{{cookiecutter.layout}}" == "src":
        if (PROJECT_DIRECTORY / "src").exists():
            shutil.rmtree(PROJECT_DIRECTORY / "src", ignore_errors=True)
        # Déplacer le slug dans src/<slug>
        moved_src = PROJECT_DIRECTORY / "{{cookiecutter.project_slug}}"
        target_src = PROJECT_DIRECTORY / "src" / "{{cookiecutter.project_slug}}"
        target_src.parent.mkdir(parents=True, exist_ok=True)
        if moved_src.exists():
            shutil.move(str(moved_src), str(target_src))

    if "{{cookiecutter.layout}}" == "flat":
        if (PROJECT_DIRECTORY / "src").exists():
            shutil.rmtree(PROJECT_DIRECTORY / "src", ignore_errors=True)

    # Types de projet
    project_type = "{{cookiecutter.project_type}}"
    project_slug = "{{cookiecutter.project_slug}}"
    project_name = "{{cookiecutter.project_name}}"

    # Toujours garantir l'existence du dossier slug (après move éventuel ci-dessus)
    slug_path = Path(slug_dir_path(project_slug))
    (PROJECT_DIRECTORY / slug_path).mkdir(parents=True, exist_ok=True)

    if project_type == "python":
        # Create TODO.md
        (PROJECT_DIRECTORY / "TODO.md").write_text("# TODO\n\n- [ ] Implement features for your workshop\n", encoding="utf-8")

        # Créer __init__.py pour déclarer le package
        init_path = PROJECT_DIRECTORY / slug_path / "__init__.py"
        init_path.touch()

        # Créer main.py comme point d'entrée
        main_path = PROJECT_DIRECTORY / slug_path / "main.py"
        main_path.write_text(
            'def main():\n'
            '    print("Hello from {{cookiecutter.project_name}}!")\n\n'
            'if __name__ == "__main__":\n'
            '    main()\n',
            encoding="utf-8",
        )

    elif project_type == "notebook":
        # Pas de __init__.py ni main.py pour le mode notebook
        notebook_path = PROJECT_DIRECTORY / slug_path / "notebook.ipynb"
        notebook_content = {
            "cells": [
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": ["## Welcome to {{cookiecutter.project_name}} notebook \n # Implement features for your workshop"]
                }
            ],
            "metadata": {
                "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                "language_info": {"name": "python", "version": "3"}
            },
            "nbformat": 4,
            "nbformat_minor": 5
        }
        notebook_path.parent.mkdir(parents=True, exist_ok=True)
        notebook_path.write_text(json.dumps(notebook_content, indent=2), encoding="utf-8")

    # Python deps with uv (optional)
    pyproject = PROJECT_DIRECTORY / "pyproject.toml"
    if UV_EXE is None or not pyproject.exists():
        print("Skipping uv: missing 'uv' executable or 'pyproject.toml'.")
    else:
        run([UV_EXE, "lock", "--directory", str(PROJECT_DIRECTORY)], check=True)
        run([UV_EXE, "sync", "--locked", "--dev"], cwd=PROJECT_DIRECTORY, check=True)

    # Git init / first commit / branches / GitHub repo
    if "{{cookiecutter.create_github_repo}}" != "n":
        if GIT_EXE is None:
            print("git executable not found in PATH, passing GitHub repository creation.")
        else:
            # init repo with main as default (fallback si -b non supporté)
            if not is_inside_git_repo():
                try:
                    run([GIT_EXE, "-C", str(PROJECT_DIRECTORY), "init", "-b", "main"], check=True)
                except subprocess.CalledProcessError:
                    run([GIT_EXE, "-C", str(PROJECT_DIRECTORY), "init"], check=True)
                    try:
                        run([GIT_EXE, "-C", str(PROJECT_DIRECTORY), "checkout", "-b", "main"], check=True)
                    except subprocess.CalledProcessError:
                        pass

            # initial add/commit
            git("add", ".", check=True)

            if PRE_COMMIT_EXE is None:
                print("pre-commit executable not found in PATH, can't install pre-commit hooks.")
            else:
                # Installer puis exécuter les hooks une fois; ignorer l'échec pour ne pas bloquer
                subprocess.run([PRE_COMMIT_EXE, "install"], cwd=str(PROJECT_DIRECTORY))
                subprocess.run([PRE_COMMIT_EXE, "run", "-a"], cwd=str(PROJECT_DIRECTORY))

            git("add", ".", check=True)
            try:
                git("commit", "-m", "Initial commit", check=True)
            except subprocess.CalledProcessError:
                # Déjà commité ? on ignore
                pass

            # Create difficulty branches (optional)
            if "{{cookiecutter.create_difficulty_branches}}" == "y":
                raw = "{{cookiecutter.difficulty_branches}}"
                branches = [b.strip() for b in raw.split(",") if b.strip()]
                create_difficulty_branches(branches, project_name)

                # *** SUPPRIMER slug + tests SUR MAIN AVANT CREATION/PUSH DU REPO ***
                remove_on_main([
                    str(slug_path),
                    "tests",
                    "TODO.md",
                    f"{project_slug}.egg-info",
                    os.path.join("src", f"{project_slug}.egg-info"),
                    "src",
                ])

            # Create and push GitHub repo with gh
            if GH_EXE is None:
                print("gh executable not found in PATH, please install GitHub CLI to create a repository.")
            else:
                # Vérifier l'authentification; si absente, ne pas lancer login interactif
                auth_rc = subprocess.run(
                    [GH_EXE, "auth", "status"],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                ).returncode
                if auth_rc == 1:
                    print("You are not authenticated with GitHub CLI. Run 'gh auth login' and re-run creation if needed.")
                else:
                    # Créer le repo et pousser la branche courante (main)
                    run(
                        [
                            GH_EXE,
                            "repo",
                            "create",
                            f"{{cookiecutter.repository_owner}}/{{cookiecutter.project_name}}",
                            "--{{cookiecutter.create_github_repo}}",
                            "--source",
                            str(PROJECT_DIRECTORY),
                            "--push",
                        ],
                        check=True,
                    )

                    # Pousser éventuellement les branches de difficulté
                    if "{{cookiecutter.create_difficulty_branches}}" == "y" and "{{cookiecutter.push_difficulty_branches}}" == "y":
                        if has_remote_origin():
                            raw = "{{cookiecutter.difficulty_branches}}"
                            branches = [b.strip() for b in raw.split(",") if b.strip()]
                            for br in branches:
                                try:
                                    git("push", "-u", "origin", br, check=True)
                                except subprocess.CalledProcessError:
                                    print(f"Warning: could not push branch '{br}'.")
                        else:
                            print("Remote 'origin' not found; skipping push of difficulty branches.")
    else:
        # Pas de repo distant; on peut quand même créer les branches localement
        if "{{cookiecutter.create_difficulty_branches}}" == "y":
            if GIT_EXE is None:
                print("git executable not found in PATH, skipping local branch creation.")
            else:
                if not is_inside_git_repo():
                    try:
                        run([GIT_EXE, "-C", str(PROJECT_DIRECTORY), "init", "-b", "main"], check=True)
                    except subprocess.CalledProcessError:
                        run([GIT_EXE, "-C", str(PROJECT_DIRECTORY), "init"], check=True)
                        try:
                            run([GIT_EXE, "-C", str(PROJECT_DIRECTORY), "checkout", "-b", "main"], check=True)
                        except subprocess.CalledProcessError:
                            pass
                git("add", ".", check=True)
                try:
                    git("commit", "-m", "Initial commit", check=True)
                except subprocess.CalledProcessError:
                    pass

                raw = "{{cookiecutter.difficulty_branches}}"
                branches = [b.strip() for b in raw.split(",") if b.strip()]
                create_difficulty_branches(branches, project_name)

                # *** SUPPRIMER slug + tests SUR MAIN (cas sans GH) ***
                remove_on_main([
                    str(slug_path),
                    "tests",
                    "TODO.md",
                    f"{project_slug}.egg-info",
                    os.path.join("src", f"{project_slug}.egg-info"),
                    "src",
                ])