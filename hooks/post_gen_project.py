#!/usr/bin/env python
from __future__ import annotations

import os
import shutil
import subprocess

PROJECT_DIRECTORY = os.path.realpath(os.path.curdir)


def remove_file(filepath: str) -> None:
    os.remove(os.path.join(PROJECT_DIRECTORY, filepath))


def remove_dir(filepath: str) -> None:
    shutil.rmtree(os.path.join(PROJECT_DIRECTORY, filepath))


def move_file(filepath: str, target: str) -> None:
    os.rename(os.path.join(PROJECT_DIRECTORY, filepath), os.path.join(PROJECT_DIRECTORY, target))


def move_dir(src: str, target: str) -> None:
    shutil.move(os.path.join(PROJECT_DIRECTORY, src), os.path.join(PROJECT_DIRECTORY, target))


if __name__ == "__main__":
    if "{{cookiecutter.include_github_actions}}" != "y":
        remove_dir(".github")

    if "{{cookiecutter.dockerfile}}" != "y":
        remove_file("Dockerfile")

    if "{{cookiecutter.codecov}}" != "y":
        remove_file("codecov.yaml")
        if "{{cookiecutter.include_github_actions}}" == "y":
            remove_file(".github/workflows/validate-codecov-config.yml")

    if "{{cookiecutter.devcontainer}}" != "y":
        remove_dir(".devcontainer")
    if "{{cookiecutter.render}}}" != "y":
        remove_file("render.yaml")
    if "{{cookiecutter.makefile}}}" != "y":
        remove_file("Makefile")

    if "{{cookiecutter.layout}}" == "src":
        if os.path.isdir("src"):
            remove_dir("src")
        move_dir("{{cookiecutter.project_slug}}", os.path.join("src", "{{cookiecutter.project_slug}}"))
    uv_executable = shutil.which("uv")
    if uv_executable is None:
        print("uv executable not found in PATH, can't generate lockfile.")
    else:
        subprocess.run([uv_executable, "lock", "--directory", PROJECT_DIRECTORY], check=True)
    if "{{cookiecutter.create_github_repo}}}" != "n":
        git_executable = shutil.which("git")
        if git_executable is None:
            print("git executable not found in PATH, passing GitHub repository creation.")
        else:
            subprocess.run([git_executable, "-C", PROJECT_DIRECTORY, "init"], check=True)
            subprocess.run([git_executable, "-C", PROJECT_DIRECTORY, "add", "."], check=True)
            subprocess.run([git_executable, "-C", PROJECT_DIRECTORY, "commit", "-m", "Initial commit"], check=True)
            gh_executable = shutil.which("gh")
            if gh_executable is None:
                print("gh executable not found in PATH, please install GitHub CLI to create a repository.")
            else:
                if not subprocess.run(
                    [gh_executable, "auth", "status", "--show-token"],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                ):
                    print("You are not authenticated with GitHub CLI. Starting authentification...")
                    subprocess.run([gh_executable, "auth", "login"], check=True)
                subprocess.run(
                    [
                        gh_executable,
                        "repo",
                        "create",
                        "{{cookiecutter.project_name}}",
                        "--{{cookiecutter.create_github_repo}}",
                        "--source",
                        PROJECT_DIRECTORY,
                        "--push",
                    ]
                )
