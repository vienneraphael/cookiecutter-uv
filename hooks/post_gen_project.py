#!/usr/bin/env python
from __future__ import annotations

import os
import shutil
import subprocess
import json

PROJECT_DIRECTORY = os.path.realpath(os.path.curdir)

def remove_file(filepath: str) -> None:
    os.remove(os.path.join(PROJECT_DIRECTORY, filepath))


def remove_dir(filepath: str) -> None:
    shutil.rmtree(os.path.join(PROJECT_DIRECTORY, filepath))


def move_file(filepath: str, target: str) -> None:
    os.rename(os.path.join(PROJECT_DIRECTORY, filepath), os.path.join(PROJECT_DIRECTORY, target))


def move_dir(src: str, target: str) -> None:
    shutil.move(os.path.join(PROJECT_DIRECTORY, src), os.path.join(PROJECT_DIRECTORY, target))


def run(cmd: list[str], check: bool = True, cwd: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, cwd=cwd)


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    git_executable = shutil.which("git")
    if git_executable is None:
        raise RuntimeError("git executable not found in PATH.")
    return run([git_executable, "-C", PROJECT_DIRECTORY, *args], check=check)


def has_remote_origin() -> bool:
    git_executable = shutil.which("git")
    if git_executable is None:
        return False
    cp = subprocess.run(
        [git_executable, "-C", PROJECT_DIRECTORY, "remote", "get-url", "origin"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return cp.returncode == 0


# ---------- HELPERS UNIFORMISÉS ----------
def slug_dir_path(project_slug: str) -> str:
    """
    Retourne le chemin du dossier 'slug' selon le layout :
      - layout == 'src'  -> 'src/<slug>'
      - layout == 'flat' -> '<slug>'
    """
    layout = "{{cookiecutter.layout}}"
    return os.path.join("src", project_slug) if layout == "src" else project_slug


def remove_on_main(paths: list[str]) -> None:
    """
    Se place sur 'main', supprime les chemins s'ils existent du dépôt et du working tree,
    puis commit la suppression. Ignore poliment si rien à faire.
    """
    try:
        git("checkout", "main", check=True)
    except subprocess.CalledProcessError:
        return

    existing = []
    for p in paths:
        if not p:
            continue
        abs_p = os.path.join(PROJECT_DIRECTORY, p)
        if os.path.exists(abs_p):
            existing.append(p)

    if not existing:
        return

    git_executable = shutil.which("git")
    if git_executable is not None:
        subprocess.run(
            [git_executable, "-C", PROJECT_DIRECTORY, "rm", "-r", "--quiet", "--ignore-unmatch", *existing],
            check=False,
        )

    for p in existing:
        abs_p = os.path.join(PROJECT_DIRECTORY, p)
        if os.path.isdir(abs_p):
            shutil.rmtree(abs_p, ignore_errors=True)
        else:
            try:
                os.remove(abs_p)
            except FileNotFoundError:
                pass

    git("add", "-A", check=True)
    try:
        git("commit", "-m", "chore(main): remove package slug and tests for main", check=True)
    except subprocess.CalledProcessError:
        pass
# ---------- FIN HELPERS UNIFORMISÉS ----------
def remove_on_all_but_main(paths: list[str]) -> None:
    """
    Supprime les chemins donnés de toutes les branches sauf 'main'.
    """
    # Récupérer toutes les branches locales
    cp = subprocess.run(
        [shutil.which("git"), "-C", PROJECT_DIRECTORY, "branch", "--format=%(refname:short)"],
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

        existing = []
        for p in paths:
            abs_p = os.path.join(PROJECT_DIRECTORY, p)
            if os.path.exists(abs_p):
                existing.append(p)

        if not existing:
            continue

        subprocess.run(
            [shutil.which("git"), "-C", PROJECT_DIRECTORY, "rm", "-r", "--quiet", "--ignore-unmatch", *existing],
            check=False,
        )
        for p in existing:
            try:
                os.remove(os.path.join(PROJECT_DIRECTORY, p))
            except FileNotFoundError:
                pass

        git("add", "-A", check=True)
        try:
            git("commit", "-m", f"chore({br}): remove README.md", check=True)
        except subprocess.CalledProcessError:
            pass

    # Revenir sur main à la fin
    try:
        git("checkout", "main", check=True)
    except subprocess.CalledProcessError:
        pass



if __name__ == "__main__":
    # Optional assets
    if "{{cookiecutter.include_github_actions}}" != "y":
        remove_dir(".github")

    if "{{cookiecutter.dockerfile}}" != "y":
        remove_file("Dockerfile")

    if "{{cookiecutter.codecov}}" != "y":
        remove_file("codecov.yaml")

    if "{{cookiecutter.devcontainer}}" != "y":
        remove_dir(".devcontainer")

    if "{{cookiecutter.render}}" != "y":
        remove_file("render.yaml")

    if "{{cookiecutter.makefile}}" != "y":
        remove_file("Makefile")

    # Layout handling
    if "{{cookiecutter.layout}}" == "src":
        if os.path.isdir("src"):
            remove_dir("src")
        move_dir("{{cookiecutter.project_slug}}", os.path.join("src", "{{cookiecutter.project_slug}}"))

    if "{{cookiecutter.layout}}" == "flat":
        if os.path.isdir("src"):
            remove_dir("src")

    # Types de projet
    project_type = "{{cookiecutter.project_type}}"
    project_slug = "{{cookiecutter.project_slug}}"

    # Toujours garantir l'existence du dossier slug (après move éventuel ci-dessus)
    slug_path = slug_dir_path(project_slug)
    os.makedirs(slug_path, exist_ok=True)

    if project_type == "python":
        # Create TODO.md
        with open(os.path.join(PROJECT_DIRECTORY, "TODO.md"), "w") as f:
            f.write("# TODO\n\n- [ ] Implement features\n- [ ] Write tests\n")

        # Créer __init__.py pour déclarer le package
        init_path = os.path.join(PROJECT_DIRECTORY, slug_path, "__init__.py")
        open(init_path, "a").close()

        # Créer main.py comme point d'entrée
        main_path = os.path.join(PROJECT_DIRECTORY, slug_path, "main.py")
        with open(main_path, "w") as f:
            f.write(
                'def main():\n'
                '    print("Hello from {{cookiecutter.project_name}}!")\n\n'
                'if __name__ == "__main__":\n'
                '    main()\n'
            )

    elif project_type == "notebook":
        # Pas de __init__.py ni main.py pour le mode notebook
        notebook_path = os.path.join(PROJECT_DIRECTORY, slug_path, "notebook.ipynb")
        notebook_content = {
            "cells": [
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": ["### Welcome to {{cookiecutter.project_name}} notebook"]
                }
            ],
            "metadata": {},
            "nbformat": 4,
            "nbformat_minor": 5
        }
        with open(notebook_path, "w") as f:
            json.dump(notebook_content, f, indent=2)

    # Python deps with uv (optional)
    uv_executable = shutil.which("uv")
    if uv_executable is None:
        print("uv executable not found in PATH, can't generate lockfile.")
    else:
        run([uv_executable, "lock", "--directory", PROJECT_DIRECTORY], check=True)
        run([uv_executable, "sync", "--locked", "--dev"], cwd=PROJECT_DIRECTORY, check=True)

    # Git init / first commit / branches / GitHub repo
    if "{{cookiecutter.create_github_repo}}" != "n":
        git_executable = shutil.which("git")
        if git_executable is None:
            print("git executable not found in PATH, passing GitHub repository creation.")
        else:
            # init repo with main as default (fallback si -b non supporté)
            try:
                run([git_executable, "-C", PROJECT_DIRECTORY, "init", "-b", "main"], check=True)
            except subprocess.CalledProcessError:
                run([git_executable, "-C", PROJECT_DIRECTORY, "init"], check=True)
                try:
                    run([git_executable, "-C", PROJECT_DIRECTORY, "checkout", "-b", "main"], check=True)
                except subprocess.CalledProcessError:
                    pass

            # initial add/commit
            git("add", ".", check=True)

            precommit_executable = shutil.which("pre-commit")
            if precommit_executable is None:
                print("pre-commit executable not found in PATH, can't install pre-commit hooks.")
            else:
                # Exécuter les hooks une fois; ignorer l'échec pour ne pas bloquer
                subprocess.run([precommit_executable, "run", "-a"], cwd=PROJECT_DIRECTORY)

            git("add", ".", check=True)
            git("commit", "-m", "Initial commit", check=True)

            # Create difficulty branches (optional)
            if "{{cookiecutter.create_difficulty_branches}}" == "y":
                raw = "{{cookiecutter.difficulty_branches}}"
                branches = [b.strip() for b in raw.split(",") if b.strip()]
                # S'assurer d'être sur main pour brancher depuis le commit initial
                try:
                    git("checkout", "main", check=True)
                except subprocess.CalledProcessError:
                    pass

                for br in branches:
                    # créer la branche et un commit vide pour visibilité
                    git("checkout", "-b", br, check=True)
                    # Supprimer README.md sur toutes les branches sauf main
                    git("commit", "--allow-empty", "-m", f"Initialize {br} branch", check=True)
                
                remove_on_all_but_main(["README.md"])

                # Revenir sur main
                try:
                    git("checkout", "main", check=True)
                except subprocess.CalledProcessError:
                    pass

                # *** SUPPRIMER slug + tests SUR MAIN AVANT CREATION/PUSH DU REPO ***
                remove_on_main([
                    slug_path,
                    "tests",
                    "TODO.md",
                    f"{project_slug}.egg-info",
                    os.path.join("src", f"{project_slug}.egg-info"),
                    "src",
                ])

            # Create and push GitHub repo with gh
            gh_executable = shutil.which("gh")
            if gh_executable is None:
                print("gh executable not found in PATH, please install GitHub CLI to create a repository.")
            else:
                # Auth si besoin
                auth_rc = subprocess.run(
                    [gh_executable, "auth", "status"],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                ).returncode
                if auth_rc == 1:
                    print("You are not authenticated with GitHub CLI. Starting authentication...")
                    run([gh_executable, "auth", "login"], check=True)

                # Créer le repo et pousser la branche courante (main)
                run(
                    [
                        gh_executable,
                        "repo",
                        "create",
                        "{{cookiecutter.project_name}}",
                        "--{{cookiecutter.create_github_repo}}",
                        "--source",
                        PROJECT_DIRECTORY,
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
            git_executable = shutil.which("git")
            if git_executable is None:
                print("git executable not found in PATH, skipping local branch creation.")
            else:
                try:
                    run([git_executable, "-C", PROJECT_DIRECTORY, "init", "-b", "main"], check=True)
                except subprocess.CalledProcessError:
                    run([git_executable, "-C", PROJECT_DIRECTORY, "init"], check=True)
                    try:
                        run([git_executable, "-C", PROJECT_DIRECTORY, "checkout", "-b", "main"], check=True)
                    except subprocess.CalledProcessError:
                        pass
                git("add", ".", check=True)
                git("commit", "-m", "Initial commit", check=True)

                raw = "{{cookiecutter.difficulty_branches}}"
                branches = [b.strip() for b in raw.split(",") if b.strip()]
                for br in branches:
                    git("checkout", "-b", br, check=True)
                    git("commit", "--allow-empty", "-m", f"Initialize {br} branch", check=True)

                remove_on_all_but_main(["README.md"])

                try:
                    git("checkout", "main", check=True)
                except subprocess.CalledProcessError:
                    pass

                # *** SUPPRIMER slug + tests SUR MAIN (cas sans GH) ***
                remove_on_main([
                    slug_path,
                    "tests",
                    "TODO.md",
                    f"{project_slug}.egg-info",
                    os.path.join("src", f"{project_slug}.egg-info"),
                    "src",
                ])