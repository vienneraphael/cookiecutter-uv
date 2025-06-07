# {{cookiecutter.project_name}}

{{cookiecutter.project_description}}

## Quick Start

### Install the project

{% if cookiecutter.makefile == "y" %}
`make install`
{% else %}

```bash
uv sync
uvx pre-commit install
```

{% endif %}
