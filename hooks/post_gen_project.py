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

    # Python or Notebook
    project_type = "{{cookiecutter.project_type}}"
    project_slug = "{{cookiecutter.project_slug}}"

    if project_type == "python":
        # Create TODO.md
        with open(os.path.join(PROJECT_DIRECTORY, "TODO.md"), "w") as f:
            f.write("# TODO\n\n- [ ] Implement features\n- [ ] Write tests\n")

        # Create main.py depending on layout
        if "{{cookiecutter.layout}}" == "src":
            main_path = os.path.join(PROJECT_DIRECTORY, "src", project_slug, "main.py")
        else:  # flat
            main_path = os.path.join(PROJECT_DIRECTORY, project_slug, "main.py")

        os.makedirs(os.path.dirname(main_path), exist_ok=True)
        with open(main_path, "w") as f:
            f.write(
                'def main():\n'
                '    print("Hello from {{cookiecutter.project_name}}!")\n\n'
                'if __name__ == "__main__":\n'
                '    main()\n'
            )

    elif project_type == "notebook":
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

        with open(os.path.join(PROJECT_DIRECTORY, "notebook.ipynb"), "w") as f:
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
            # init repo with main as default (fallback if -b not supported)
            try:
                run([git_executable, "-C", PROJECT_DIRECTORY, "init", "-b", "main"], check=True)
            except subprocess.CalledProcessError:
                run([git_executable, "-C", PROJECT_DIRECTORY, "init"], check=True)
                try:
                    run([git_executable, "-C", PROJECT_DIRECTORY, "checkout", "-b", "main"], check=True)
                except subprocess.CalledProcessError:
                    # As a last resort, continue on whatever default branch exists
                    pass

            # initial add/commit
            git("add", ".", check=True)

            precommit_executable = shutil.which("pre-commit")
            if precommit_executable is None:
                print("pre-commit executable not found in PATH, can't install pre-commit hooks.")
            else:
                # Run all hooks once; ignore failure to avoid blocking initialization
                subprocess.run([precommit_executable, "run", "-a"], cwd=PROJECT_DIRECTORY)

            git("add", ".", check=True)
            git("commit", "-m", "Initial commit", check=True)

            # Create difficulty branches (optional)
            if "{{cookiecutter.create_difficulty_branches}}" == "y":
                raw = "{{cookiecutter.variant_branches}}"
                branches = [b.strip() for b in raw.split(",") if b.strip()]
                # Ensure we're on main to branch from the initial commit
                try:
                    git("checkout", "main", check=True)
                except subprocess.CalledProcessError:
                    # if 'main' does not exist, skip—branches will be created from current branch
                    pass

                for br in branches:
                    # create branch, make an empty commit for visibility
                    git("checkout", "-b", br, check=True)
                    git("commit", "--allow-empty", "-m", f"Initialize {br} branch", check=True)

                # go back to main at the end
                try:
                    git("checkout", "main", check=True)
                except subprocess.CalledProcessError:
                    pass

            # Create and push GitHub repo with gh
            gh_executable = shutil.which("gh")
            if gh_executable is None:
                print("gh executable not found in PATH, please install GitHub CLI to create a repository.")
            else:
                # Authenticate if needed
                auth_rc = subprocess.run(
                    [gh_executable, "auth", "status"],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                ).returncode
                if auth_rc == 1:
                    print("You are not authenticated with GitHub CLI. Starting authentication...")
                    run([gh_executable, "auth", "login"], check=True)

                # Create repo and push current branch (main)
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

                # Optionally push difficulty branches
                if "{{cookiecutter.create_difficulty_branches}}" == "y" and "{{cookiecutter.push_difficulty_branches}}" == "y":
                    if has_remote_origin():
                        raw = "{{cookiecutter.variant_branches}}"
                        branches = [b.strip() for b in raw.split(",") if b.strip()]
                        for br in branches:
                            try:
                                git("push", "-u", "origin", br, check=True)
                            except subprocess.CalledProcessError:
                                print(f"Warning: could not push branch '{br}'.")
                    else:
                        print("Remote 'origin' not found; skipping push of difficulty branches.")
    else:
        # Repo not requested; still optionally create local branches for consistency
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
                raw = "{{cookiecutter.variant_branches}}"
                branches = [b.strip() for b in raw.split(",") if b.strip()]
                for br in branches:
                    git("checkout", "-b", br, check=True)
                    git("commit", "--allow-empty", "-m", f"Initialize {br} branch", check=True)
                try:
                    git("checkout", "main", check=True)
                except subprocess.CalledProcessError:
                    pass
