__all__ = ["run"]

import errno
import logging
import os
import pathlib
import shutil
import subprocess
import typing

from .errs import Error
from .projects import Project, looks_like_path, runtimes


logger = logging.getLogger(__name__)


class _NoActiveRuntime(Exception):
    pass


def _find_runtime(project: Project, options) -> runtimes.Runtime:
    if options.spec:
        return project.find_runtime(options.spec)
    runtime = project.get_active_runtime()
    if not runtime:
        raise _NoActiveRuntime()
    return runtime


def _resolve_command_from_path(s: str) -> typing.Optional[str]:
    if pathlib.Path(s).is_file():
        return s
    return None


def run(project: Project, options) -> int:
    try:
        runtime = _find_runtime(project, options)
    except _NoActiveRuntime:
        logger.error(
            "No active runtime. Set with `venv use` first, or select one "
            "explicitly with `--spec`"
        )
        return Error.runtime_no_active
    except runtimes.MultipleRuntimeMatches as e:
        logger.error(
            "Specifier %r is ambiguous; choose from:\n %s",
            e.alias,
            "\n".join(f"  {m.name}" for m in e.matches),
        )
        return Error.runtime_multiple_matches
    except runtimes.NoRuntimeMatch as e:
        logger.error(
            "Specifier %r does not match any runtimes; tried:\n %s",
            e.alias,
            "\n".join(f"  {m.name}" for m in e.tried),
        )
        return Error.runtime_no_match

    environ_path = runtime.derive_environ_path()
    if looks_like_path(options.cmd):
        command = _resolve_command_from_path(options.cmd)
    else:
        command = shutil.which(options.cmd, path=environ_path)

    if not command:
        logger.error("Command not found: %r", options.cmd)
        return errno.ENOENT

    env = os.environ.copy()
    env["PATH"] = environ_path
    env["VIRTUAL_ENV"] = str(runtime.root)

    proc = subprocess.run([command, *options.args], env=env)
    return proc.returncode
