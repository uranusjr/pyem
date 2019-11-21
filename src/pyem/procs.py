__all__ = ["run"]

import os
import subprocess

from .projects import Project


class NoActiveRuntime(Exception):
    pass


def run(project: Project, options) -> int:
    if not options.spec:
        runtime = project.get_active_runtime()
    else:
        runtime = project.find_runtime(options.spec)

    if not runtime:
        raise NoActiveRuntime()

    env = os.environ.copy()
    env["PATH"] = runtime.derive_environ_path()
    env["VIRTUAL_ENV"] = str(runtime.root)

    proc = subprocess.run([options.cmd, *options.args], env=env)
    return proc.returncode
