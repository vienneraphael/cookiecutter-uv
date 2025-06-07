{% if cookiecutter.layout == "src" %}
from {{cookiecutter.project_name}}.main import main
{% else %}
{% if cookiecutter.layout == "backend" %}
from {{cookiecutter.layout}}.main import main
{% endif %}

def test_main():
    assert main() == 42
