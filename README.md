# Template for datacraft's workshops

## Quickstart

On your local machine, navigate to the directory in which you want to
create a project directory, and run the following command:

```bash
uvx cookiecutter gh:datacraft-paris/cookiecutter-workshop-template
```

or if you don't have `uv` installed yet:

```bash
pip install cookiecutter
cookiecutter gh:datacraft-paris/cookiecutter-workshop-template
```

Follow the prompts to configure your project. Once completed, a new directory containing your project will be created. Then navigate into your newly created project directory and follow the instructions in the `README.md` to complete the setup of your project.

## Customize this project

If you want to customize default values for this project:
1. Clone or fork this project
2. Edit [`cookiecutter.json`](./cookiecutter.json) and insert your default values
3. You can then choose what the default values generate by manipulating the [`post_gen_hooks.py`](./hooks/post_gen_project.py) file.

In addition, you can extend step 3 to fully adapt the generation logic to your needs (e.g., adding or removing files, renaming paths, injecting extra configuration).
All the files and templates located in `{{cookiecutter.project_name}}` correspond to the default generated structure. You are free to modify them to define the base templates for your own project.

## Acknowledgements

This project is partially based on [Audrey
Feldroy\'s](https://github.com/audreyfeldroy)\'s great
[cookiecutter-pypackage](https://github.com/audreyfeldroy/cookiecutter-pypackage)
repository.
