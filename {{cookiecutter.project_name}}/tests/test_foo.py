{% if cookiecutter.layout == "backend" %}
from {{cookiecutter.layout}}.main import main
{% else %}
from {{cookiecutter.project_slug}}.main import main
{% endif %}

def test_main():
    assert main() == 42
