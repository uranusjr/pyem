__all__ = ["activate", "add", "remove", "show_all"]


import logging
import os

from .errs import Error, errorlog
from .projects import runtimes


logger = logging.getLogger(__name__)


def add(project, options) -> int:
    try:
        runtime = project.create_runtime(options.python)
    except runtimes.InterpreterNotFound:
        logger.error("Not a valid interpreter: %r", options.python)
        return Error.interpreter_not_found
    except runtimes.PyUnavailable:
        if os.name == "nt":
            url = "https://docs.python.org/3/using/windows.html"
        else:
            url = "https://github.com/brettcannon/python-launcher"
        logger.error(
            "Specifying Python with version requires the Python "
            "Launcher\n%s",
            url,
        )
        return Error.py_unavailable
    except runtimes.VirtualenvNotFound:
        logger.error(
            "Requires virtualenv to create a virtual environment for %s",
            options.python,
        )
        return Error.virtualenv_unavailable
    except runtimes.EnvironmentCreationError as e:
        logger.error(
            "Failed to create a virtual environment for %s:\n%s",
            options.python,
            e,
        )
        return Error.runtime_invalid

    try:
        project.activate_runtime(runtime)
    except OSError as e:
        env_dir = runtime.root.relative_to(project.root)
        logger.warning("Failed to activate %s\n%s", env_dir, e)
        activated = False
    else:
        activated = True

    if activated:
        msg = "Created and activated virtual environment %s"
    else:
        msg = "Created virtual environment %s"
    logger.info(msg, runtime.name)

    return 0


def _no_runtime_match(e: runtimes.NoRuntimeMatch) -> int:
    logger.error(
        "No matching venv for %r, tried: %s",
        e.alias,
        ", ".join(r.name for r in e.tried),
    )
    return Error.runtime_no_match


def _multiple_runtime_matches(e: runtimes.MultipleRuntimeMatches) -> int:
    logger.error(
        "Name %r is ambiguous; choose from:\n%s",
        e.alias,
        "\n".join(f"  {r.name}" for r in e.matches),
    )
    return Error.runtime_multiple_matches


@errorlog(runtimes.MultipleRuntimeMatches, _multiple_runtime_matches)
@errorlog(runtimes.NoRuntimeMatch, _no_runtime_match)
def remove(project, options) -> int:
    runtime = project.find_runtime(options.spec)

    if project.get_active_runtime() == runtime:
        try:
            project.deactivate_runtime()
        except OSError as e:
            logger.error("Failed to deactivate %s\n%s", runtime.name, e)
            return e.errno
        deactivated = True
    else:
        deactivated = False

    try:
        project.remove_runtime(runtime)
    except OSError as e:
        env_dir = runtime.root.relative_to(project.root)
        logger.error("Failed to remove %s\n%s", env_dir, e)
        return e.errno

    if deactivated:
        msg = "Removed and deactivated virtual environment %s"
    else:
        msg = "Removed virtual environment %s"
    logger.info(msg, runtime.name)

    return 0


@errorlog(runtimes.MultipleRuntimeMatches, _multiple_runtime_matches)
@errorlog(runtimes.NoRuntimeMatch, _no_runtime_match)
def activate(project, options) -> int:
    if not options.spec:
        try:
            project.deactivate_runtime()
        except OSError as e:
            logger.error("Failed to deactivate runtime\n%s", e)
            return e.errno
        return 0

    runtime = project.find_runtime(options.spec)

    try:
        project.activate_runtime(runtime)
    except OSError as e:
        env_dir = runtime.root.relative_to(project.root)
        logger.error("Failed to activate %s\n%s", env_dir, e)
        return e.errno

    logger.info("Activated virtual environment: %s", runtime.name)
    return 0


def show_active(project, options) -> int:
    runtime = project.get_active_runtime()
    if not runtime:
        logger.error("No active runtime.")
        return Error.runtime_no_active
    print(runtime.name)
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
