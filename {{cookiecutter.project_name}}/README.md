# {{cookiecutter.project_name}}

{{cookiecutter.project_description}}

---

## Table of Contents
- **[Learning Objectives](#learning-objectives)**
- **[Workshop Structure](#workshop-structure)**
- **[Repository Organization](#repository-organization)**
- **[Getting Started](#getting-started)**

---

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