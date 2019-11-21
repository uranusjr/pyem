__all__ = ["activate", "add", "remove", "show_all"]


def _find_runtime_match(project, alias: str):
    return project.find_runtime(alias)


def add(project, options) -> int:
    runtime = project.create_runtime(options.python)
    print("created", runtime.name)
    return 0


def remove(project, options) -> int:
    runtime = _find_runtime_match(project, options.spec)
    project.remove_runtime(runtime)
    print("removed", runtime.name)
    return 0


def activate(project, options) -> int:
    runtime = _find_runtime_match(project, options.spec)
    project.activate_runtime(runtime)
    print("activated", runtime.name)
    return 0


def show_all(project, options) -> int:
    print("  Quintuplet")
    print("=" * 45)

    active_runtime = project.get_active_runtime()
    for runtime in project.iter_runtimes():
        line = "{} {}".format(
            "*" if runtime == active_runtime else " ", runtime.name
        )
        print(line)

    return 0
