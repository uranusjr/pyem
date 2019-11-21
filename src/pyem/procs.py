__all__ = ["run"]

import os
import subprocess


def run(project, options):
    if options.spec:
        runtime = project.find_runtime(options.spec)
    else:
        runtime = project.get_active_runtime()

    env = os.environ.copy()
    env["PATH"] = runtime.derive_environ_path()
    env["VIRTUAL_ENV"] = str(runtime.root)

    subprocess.run([options.cmd, *options.args], env=env, check=True)
