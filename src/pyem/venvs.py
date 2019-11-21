__all__ = ["activate", "add", "remove", "show_all"]

import typing

from .projects import Project, Runtime


def _find_runtime_match(
    project: Project, alias: str
) -> typing.Optional[Runtime]:
    return project.find_runtime(alias)


def add(project, options):
    runtime = project.create_runtime(options.python)
    print("created", runtime.name)


def remove(project, options):
    runtime = _find_runtime_match(project, options.spec)
    project.remove_runtime(runtime)
    print("removed", runtime.name)


def activate(project, options):
    runtime = _find_runtime_match(project, options.spec)
    project.activate_runtime(runtime)
    print("activated", runtime.name)


def show_all(project, options):
    print("  Quintuplet")
    print("=" * 45)

    active_runtime = project.get_active_runtime()
    for runtime in project.iter_runtimes():
        line = "{} {}".format(
            "*" if runtime == active_runtime else " ", runtime.name
        )
        print(line)
