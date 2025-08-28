# {{cookiecutter.project_name}}

{{cookiecutter.project_description}}

## Instructions to create your workshop

You are currently on the **main** branch.
This project contains **2 branches**:

- **main** → used to introduce the theme of your workshop.
- **correction** → where you should implement everything you want to do.

Once your correction branch is ready, you can create additional branches for each difficulty level of your exercises.
To do so, use the following command:

```bash
git checkout -b <difficulty_branch>
````

In the next sections of this README, you will find examples of basic components that you can reuse or adapt when writing your own README.
Good luck creating you workshop !

## Table of Contents

- **[Learning Objectives](#learning-objectives)**
- **[Workshop Structure](#workshop-structure)**
- **[Repository Organization](#repository-organization)**

## Learning Objectives

## Workshop Structure

## Repository Organization

| Branch         | Purpose                                                                    |
|----------------|----------------------------------------------------------------------------|
| `main`         | Core concepts and theoretical foundations of model calibration             |
| `easy`         | Beginner-friendly version with step-by-step guidance                      |
| `intermediate` | Standard version with partial implementation guidance                      |
| `hard`         | Advanced challenges for experienced practitioners                          |
| `correction`   | Complete solutions with detailed explanations                             |

> **Recommendation**: Start with the `main` branch to grasp the theoretical foundations. Choose your subsequent branch based on your experience level. Feel free to start with the `hard` branch if you're up for a challenge. If it gets tricky, switch to `intermediate` or `easy` for progressive hints. Even if you're experienced, the `easy` branch can provide valuable insights into best practices.

### Directory Structure

### Navigating the Workshop

This workshop offers different difficulty levels to match your learning pace. To switch between levels:

```bash
git checkout <branch-name>
```

Replace `<branch-name>` with one of the following :

- `main`         → basic explanation and introduction
- `easy`         → Step-by-step version
- `intermediate` → standard level
- `hard`         → advanced version
- `correction`   → Complete solution

---

## Setup

### Install the project

```bash
uv sync
uvx pre-commit install
```
