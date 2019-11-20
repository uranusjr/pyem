__all__ = ["run"]

import subprocess


def run(project, options):
    if options.spec:
        runtime = project.find_runtime(options.spec)
    else:
        runtime = project.get_active_runtime()
    args = [options.cmd, *options.args]
    subprocess.run(args, env=runtime.derive_environ(), check=True)
