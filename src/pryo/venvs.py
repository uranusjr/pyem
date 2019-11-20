__all__ = ["activate", "add", "remove", "show_all"]


def add(project, options):
    print("add venv with", options.python)


def remove(project, options):
    print("remove venv", options.spec)


def activate(project, options):
    print("activate venv", options.spec)


def show_all(project, options):
    print("list venvs as", options.format)
