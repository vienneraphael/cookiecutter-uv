#!/usr/bin/env python
from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Sequence
from contextlib import suppress
from pathlib import Path
from typing import Any

# Constants & tool detection

PROJECT_DIRECTORY = Path.cwd().resolve()
GIT_EXE: str | None = shutil.which("git")
GH_EXE: str | None = shutil.which("gh")
UV_EXE: str | None = shutil.which("uv")
PRE_COMMIT_EXE: str | None = shutil.which("pre-commit")

# Branches created when requested by the template
_DIFFICULTY_BRANCHES_RAW = "correction"


# Errors


class GitNotFoundError(RuntimeError):
    """Raised when the git executable cannot be located in PATH."""

    def __init__(self) -> None:
        super().__init__("git executable not found in PATH.")


# Helper functions


def _run(
    cmd: Sequence[str],
    *,
    check: bool = True,
    cwd: Path | None = None,
    **popen_kwargs: Any,
) -> subprocess.CompletedProcess[Any]:
    """Run a system command."""
    return subprocess.run(
        list(cmd),
        check=check,
        cwd=str(cwd or PROJECT_DIRECTORY),
        **popen_kwargs,
    )


def _git(*args: str, check: bool = True, **popen_kwargs: Any) -> subprocess.CompletedProcess[Any]:
    """Run a git command inside :data:`PROJECT_DIRECTORY`."""
    if GIT_EXE is None:
        raise GitNotFoundError()
    return _run([GIT_EXE, "-C", str(PROJECT_DIRECTORY), *args], check=check, **popen_kwargs)


def _has_remote_origin() -> bool:
    """Return True if a remote named origin exists."""
    if GIT_EXE is None:
        return False
    cp = subprocess.run(
        [GIT_EXE, "-C", str(PROJECT_DIRECTORY), "remote", "get-url", "origin"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return cp.returncode == 0


def _inside_git_repo() -> bool:
    """Return True if inside a git repo."""
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


def _ensure_git_identity() -> None:
    """Ensure a local Git identity so non-interactive commits work."""
    if GIT_EXE is None or not _inside_git_repo():
        return

    name_rc = subprocess.run(
        [GIT_EXE, "-C", str(PROJECT_DIRECTORY), "config", "--get", "user.name"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    email_rc = subprocess.run(
        [GIT_EXE, "-C", str(PROJECT_DIRECTORY), "config", "--get", "user.email"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )

    if not name_rc.stdout.strip():
        _run([GIT_EXE, "-C", str(PROJECT_DIRECTORY), "config", "user.name", "cookiecutter"], check=True)
    if not email_rc.stdout.strip():
        _run(
            [GIT_EXE, "-C", str(PROJECT_DIRECTORY), "config", "user.email", "cookiecutter@example.com"],
            check=True,
        )


def _slug_dir_path(project_slug: str) -> Path:
    """Return the slug directory path according to the selected layout."""
    layout = "{{cookiecutter.layout}}"
    return (PROJECT_DIRECTORY / "src" / project_slug) if layout == "src" else (PROJECT_DIRECTORY / project_slug)


def _safe_commit(message: str) -> None:
    """Stage all changes and commit iff there is something to commit."""
    _git("add", "-A", check=True)
    res = _git("status", "--porcelain", check=False, capture_output=True, text=True)
    if res.stdout.strip() == "":
        print("No changes, skipping commit.")
        return
    _git("commit", "-m", message, "--no-verify", check=True)


def _write_branch_readme(project_name: str) -> None:
    """Write a minimal, valid README for a difficulty branch (no commit)"""
    readme_path = PROJECT_DIRECTORY / "README.md"
    with suppress(FileNotFoundError):
        readme_path.unlink()
    content = (
        f"# {project_name}\n\n"
        "## Workshop instructions\n\n"
        "You are currently on the **correction** branch.\n"
        "This project contains **2 branches**:\n\n"
        "- **main** → used to introduce the theme of your workshop.\n"
        "- **correction** → where you should implement everything you want to do.\n\n"
        "After fully implementig this branch, you can create additional branches for each difficulty level "
        "(for example: `easy`, `intermediate`, `hard`).\n"
        "To do so, use the following command:\n\n"
        "```bash\n"
        "git checkout -b <branch-name>\n"
        "```\n"
    )

    readme_path.write_text(content, encoding="utf-8")


def _run_precommit_check(*, context: str, strict: bool = False, autocommit: bool = False) -> int:
    """Execute `pre-commit run --all-files` and optionally commit autofixes.
    Returns the return code from pre-commit."""
    if PRE_COMMIT_EXE is None:
        print(f"[pre-commit:{context}] not found in PATH. Skipping.")
        return 0
    if not _inside_git_repo():
        print(f"[pre-commit:{context}] not in a Git repo. Skipping.")
        return 0

    subprocess.run([PRE_COMMIT_EXE, "install"], cwd=str(PROJECT_DIRECTORY))

    print(f"[pre-commit:{context}] running hooks on all files…")
    rc = subprocess.run([PRE_COMMIT_EXE, "run", "--all-files"], cwd=str(PROJECT_DIRECTORY)).returncode
    if rc == 0:
        print(f"[pre-commit:{context}] hooks passed.")
    else:
        print(f"[pre-commit:{context}] hooks failed with code {rc}.")
        if strict:
            raise SystemExit(rc)

    return rc


def _create_difficulty_branches(branches: list[str], project_name: str) -> None:
    """Create difficulty branches from main with a single branch-specific commit."""
    with suppress(subprocess.CalledProcessError):
        _git("checkout", "main", check=True)

    for br in branches:
        _git("checkout", "-b", br, check=True)
        _write_branch_readme(project_name)
        _safe_commit("initializing branch with branch-specific README")
        print()
        _run_precommit_check(context=br, strict=False, autocommit=True)

    with suppress(subprocess.CalledProcessError):
        _git("checkout", "main", check=True)


def _ensure_git_repo(*, default_branch: str = "main") -> None:
    """Ensure a Git repository exists and that ``default_branch`` is present."""
    if GIT_EXE is None or _inside_git_repo():
        return
    try:
        _run([GIT_EXE, "-C", str(PROJECT_DIRECTORY), "init", "-b", default_branch], check=True)
    except subprocess.CalledProcessError:
        _run([GIT_EXE, "-C", str(PROJECT_DIRECTORY), "init"], check=True)
        with suppress(subprocess.CalledProcessError):
            _run([GIT_EXE, "-C", str(PROJECT_DIRECTORY), "checkout", "-b", default_branch], check=True)


def _gh_git_protocol() -> str:
    """Return 'ssh' or 'https' according to gh config (default https)."""
    if GH_EXE is None:
        return "https"
    cp = subprocess.run(
        [GH_EXE, "config", "get", "git_protocol"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    proto = (cp.stdout or "").strip().lower()
    return "ssh" if proto == "ssh" else "https"


def _ensure_remote_origin(owner: str, name: str) -> None:
    """Ensure a proper 'origin' remote pointing to owner/name (SSH or HTTPS)."""
    proto = _gh_git_protocol()
    url = f"git@github.com:{owner}/{name}.git" if proto == "ssh" else f"https://github.com/{owner}/{name}.git"
    try:
        _git("remote", "add", "origin", url, check=True)
    except subprocess.CalledProcessError:
        # S'il existe déjà, on met simplement à jour l'URL
        _git("remote", "set-url", "origin", url, check=True)


# Main


if __name__ == "__main__":
    # Python deps with uv
    pyproject = PROJECT_DIRECTORY / "pyproject.toml"
    if UV_EXE is None or not pyproject.exists():
        print("Skipping uv: missing 'uv' or 'pyproject.toml'.")
    else:
        _run([UV_EXE, "lock", "--directory", str(PROJECT_DIRECTORY)], check=True)
        _run([UV_EXE, "sync", "--locked", "--dev"], check=True)

    # Ensure a Git repo exists
    _ensure_git_repo(default_branch="main")
    _ensure_git_identity()

    # Install pre-commit hooks (idempotent). Internal commits use --no-verify.
    if PRE_COMMIT_EXE is None:
        print("Install pre-commit with 'pipx install pre-commit' or 'pip install pre-commit'.")
    else:
        if _inside_git_repo():
            print("Installing pre-commit hooks…")
            subprocess.run([PRE_COMMIT_EXE, "install"], cwd=str(PROJECT_DIRECTORY))
        else:
            print("Not inside a Git repository, skipping pre-commit installation.")

    # Optional assets (filesystem only; do not commit here)
    if "{{cookiecutter.include_github_actions}}" != "y" and (PROJECT_DIRECTORY / ".github").exists():
        shutil.rmtree(PROJECT_DIRECTORY / ".github", ignore_errors=True)

    if "{{cookiecutter.dockerfile}}" != "y":
        with suppress(FileNotFoundError):
            (PROJECT_DIRECTORY / "Dockerfile").unlink()

    if "{{cookiecutter.codecov}}" != "y":
        with suppress(FileNotFoundError):
            (PROJECT_DIRECTORY / "codecov.yaml").unlink()

    if "{{cookiecutter.devcontainer}}" != "y" and (PROJECT_DIRECTORY / ".devcontainer").exists():
        shutil.rmtree(PROJECT_DIRECTORY / ".devcontainer", ignore_errors=True)

    if "{{cookiecutter.render}}" != "y":
        with suppress(FileNotFoundError):
            (PROJECT_DIRECTORY / "render.yaml").unlink()

    if "{{cookiecutter.makefile}}" != "y":
        with suppress(FileNotFoundError):
            (PROJECT_DIRECTORY / "Makefile").unlink()

    # Layout handling (filesystem only)
    if "{{cookiecutter.layout}}" == "src":
        if (PROJECT_DIRECTORY / "src").exists():
            shutil.rmtree(PROJECT_DIRECTORY / "src", ignore_errors=True)
        moved_src = PROJECT_DIRECTORY / "{{cookiecutter.project_slug}}"
        target_src = PROJECT_DIRECTORY / "src" / "{{cookiecutter.project_slug}}"
        target_src.parent.mkdir(parents=True, exist_ok=True)
        if moved_src.exists():
            shutil.move(str(moved_src), str(target_src))

    if "{{cookiecutter.layout}}" == "flat" and (PROJECT_DIRECTORY / "src").exists():
        shutil.rmtree(PROJECT_DIRECTORY / "src", ignore_errors=True)

    # Project types (filesystem only)
    project_type = "{{cookiecutter.project_type}}"
    project_slug = "{{cookiecutter.project_slug}}"
    project_name = "{{cookiecutter.project_name}}"

    slug_path = _slug_dir_path(project_slug)
    slug_path.mkdir(parents=True, exist_ok=True)

    if project_type == "python":
        pass

    elif project_type == "notebook":
        notebook_path = slug_path / "{{cookiecutter.project_slug}}.ipynb"
        notebook_content = {
            "cells": [
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": [
                        "## Welcome to {{cookiecutter.project_name}} notebook\n",
                        "Implement features for your workshop.",
                    ],
                }
            ],
            "metadata": {
                "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                "language_info": {"name": "python", "version": "3"},
            },
            "nbformat": 4,
            "nbformat_minor": 5,
        }
        notebook_path.parent.mkdir(parents=True, exist_ok=True)
        notebook_path.write_text(json.dumps(notebook_content, indent=2) + "\n", encoding="utf-8")
        for filename in ("main.py", "__init__.py"):
            file_path = slug_path / filename
            if file_path.exists():
                file_path.unlink()

    # Minimal commits
    if "{{cookiecutter.create_github_repo}}" != "n":
        if GIT_EXE is None:
            print("git not found; skipping GitHub repo creation.")
        else:
            if not _inside_git_repo():
                try:
                    _run([GIT_EXE, "-C", str(PROJECT_DIRECTORY), "init", "-b", "main"], check=True)
                except subprocess.CalledProcessError:
                    _run([GIT_EXE, "-C", str(PROJECT_DIRECTORY), "init"], check=True)
                    with suppress(subprocess.CalledProcessError):
                        _run([GIT_EXE, "-C", str(PROJECT_DIRECTORY), "checkout", "-b", "main"], check=True)

            _ensure_git_identity()

            # Single initial commit (local only)
            _git("add", ".", check=True)
            with suppress(subprocess.CalledProcessError):
                _git("commit", "-m", "Initial commit", "--no-verify", check=True)

            # 2) Difficulty branches — local only (no push)
            branches = [b.strip() for b in _DIFFICULTY_BRANCHES_RAW.split(",") if b.strip()]
            _create_difficulty_branches(branches, project_name)

            # 3) Create/link the GitHub repo (no push)
        if GH_EXE is None:
            print("gh CLI not found; cannot create/link remote.")
        else:
            auth_rc = subprocess.run(
                [GH_EXE, "auth", "status"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ).returncode
            if auth_rc == 1:
                print("Run 'gh auth login' to authenticate, then re-run if needed.")
            else:
                owner = "{{cookiecutter.repository_owner}}"
                name = "{{cookiecutter.project_name}}"
                full = f"{owner}/{name}"

                if _has_remote_origin():
                    print("Remote 'origin' already configured; skipping repo creation.")
                else:
                    # if repo already exists, we link it to the remote repo
                    exists_rc = subprocess.run(
                        [GH_EXE, "repo", "view", full],
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    ).returncode

                    if exists_rc == 0:
                        print(f"GitHub repo '{full}' already exists; linking 'origin'.")
                        _ensure_remote_origin(owner, name)
                    else:
                        _run(
                            [
                                GH_EXE,
                                "repo",
                                "create",
                                full,
                                "--{{cookiecutter.create_github_repo}}",  # --public / --private
                                "--source",
                                str(PROJECT_DIRECTORY),
                                "-r",
                                "origin",
                            ],
                            check=True,
                        )

    else:
        # Local-only: still make minimal commits so hooks can run if enabled
        if GIT_EXE is None:
            print("git not found; skipping local branch creation.")
        else:
            if not _inside_git_repo():
                try:
                    _run([GIT_EXE, "-C", str(PROJECT_DIRECTORY), "init", "-b", "main"], check=True)
                except subprocess.CalledProcessError:
                    _run([GIT_EXE, "-C", str(PROJECT_DIRECTORY), "init"], check=True)
                    with suppress(subprocess.CalledProcessError):
                        _run([GIT_EXE, "-C", str(PROJECT_DIRECTORY), "checkout", "-b", "main"], check=True)

            _ensure_git_identity()

            _git("add", ".", check=True)
            with suppress(subprocess.CalledProcessError):
                _git("commit", "-m", "Initial commit", "--no-verify", check=True)

            branches = [b.strip() for b in _DIFFICULTY_BRANCHES_RAW.split(",") if b.strip()]
            _create_difficulty_branches(branches, project_name)

    # Final clean-up of the main branch
    try:
        _git("switch", "main", check=True)
    except subprocess.CalledProcessError:
        print("Impossible de basculer sur 'main', nettoyage ignoré.")
    else:
        readme_path = PROJECT_DIRECTORY / "README.md"
        if not readme_path.exists():
            readme_path.write_text(f"# {project_name}\n", encoding="utf-8")

        deleted = False
        for entry in PROJECT_DIRECTORY.iterdir():
            name = entry.name
            if name in ("README.md", ".git"):
                continue
            try:
                if entry.is_dir():
                    shutil.rmtree(entry, ignore_errors=True)
                else:
                    entry.unlink(missing_ok=True)
                deleted = True
            except Exception:
                with suppress(FileNotFoundError):
                    if entry.is_dir():
                        shutil.rmtree(entry, ignore_errors=True)
                    else:
                        entry.unlink()
                deleted = True

        if deleted:
            _safe_commit("main: clean workspace, keep README only")
            print()
        else:
            print("Aucun fichier à supprimer sur main.")

    # Ensure requirements.txt is staged & committed if generated
    req = PROJECT_DIRECTORY / "requirements.txt"
    if req.exists():
        _git("add", "requirements.txt", check=True)
        res = _git("status", "--porcelain", check=False, capture_output=True, text=True)
        if "requirements.txt" in res.stdout:
            with suppress(subprocess.CalledProcessError):
                _git("commit", "-m", "chore: add generated requirements.txt", "--no-verify", check=True)

    # Final push
    if _has_remote_origin():
        try:
            # Push all local branches and set upstreams
            _git("push", "-u", "origin", "--all", check=True)
            # Push tags if any
            with suppress(subprocess.CalledProcessError):
                _git("push", "-u", "origin", "--tags", check=True)
        except subprocess.CalledProcessError:
            print("Final push failed. Check your permissions/authentication and try again.")
    else:
        print("No 'origin' remote configured; skipping final push.")
