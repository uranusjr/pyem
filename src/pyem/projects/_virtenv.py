from __future__ import print_function

__all__ = ["create", "VirtualenvNotFound"]

import os
import subprocess
import sys

try:
    import venv
except ImportError:
    venv = None
else:

    class _EnvBuilder(venv.EnvBuilder):
        """Custom environment builder to ensure libraries are up-to-date.

        Also add support to custom prompt, and some output to make the process
        more verbose, matching virtualenv's behavior.
        """

        def __init__(self, **kwargs):
            if sys.version_info < (3, 6):
                self.prompt = kwargs.pop("prompt", None)
            super(_EnvBuilder, self).__init__(**kwargs)

        def ensure_directories(self, env_dir):
            context = super(_EnvBuilder, self).ensure_directories(env_dir)
            if sys.version_info < (3, 6) and self.prompt is not None:
                context.prompt = self.prompt
            return context

        def setup_python(self, context):
            super(_EnvBuilder, self).setup_python(context)
            print("New Python executable in", context.env_exe)

        def post_setup(self, context):
            if not self.with_pip:
                return
            print(
                "Ensuring up-to-date setuptools, pip, and wheel...",
                end="",
                flush=True,
            )
            env = os.environ.copy()
            env.update(
                {
                    "PIP_DISABLE_PIP_VERSION_CHECK": "1",
                    "PIP_NO_WARN_CONFLICTS": "1",
                }
            )
            returncode = subprocess.call(
                [
                    context.env_exe,
                    "-m",
                    "pip",
                    "install",
                    "--upgrade",
                    "--quiet",
                    "setuptools",
                    "pip",
                    "wheel",
                ],
                env=env,
            )
            if returncode == 0:
                print("done")
            else:
                # If update fails, there should already be a nice error message
                # from pip present. Just carry on.
                print()


def get_script(module=None):
    if module:
        script = os.path.realpath(module.__file__)
    else:
        script = os.path.realpath(__file__)
    if script.endswith(".pyc") and os.path.exists(script[:-1]):
        return os.path.realpath(script[:-1])
    return script


def _create_venv(env_dir, system_site_packages, prompt, bare):
    builder = _EnvBuilder(
        prompt=prompt,  # Supported by custom builder.
        system_site_packages=system_site_packages,
        symlinks=(os.name != "nt"),  # Copied from venv logic.
        with_pip=(not bare),  # OK since we only enter here for Python 3.4+.
    )
    builder.create(env_dir)


class VirtualenvNotFound(EnvironmentError):
    pass


def _create_virtualenv(virtualenv_py, env_dir, system, prompt, bare):
    if not virtualenv_py:
        try:
            import virtualenv
        except ImportError:
            raise VirtualenvNotFound
        else:
            virtualenv_py = get_script(virtualenv)
    if not prompt:
        prompt = os.path.basename(env_dir)
    cmd = [
        sys.executable,
        virtualenv_py,
        str(env_dir),
        "--prompt",
        "({}) ".format(prompt),
    ]
    if system:
        cmd.append("--system-site-packages")
    if bare:
        cmd.extend(["--no-pip", "--no-setuptools", "--no-wheel"])
    subprocess.check_call(cmd)


def _is_venv_usable(needs_pip):
    if not venv:
        if sys.version_info >= (3, 3):
            print("venv not available, falling back to virtualenv")
        else:
            print("Using virtualenv")
        return False
    if needs_pip:
        try:
            import ensurepip  # noqa
        except ImportError:
            print(
                "venv without ensurepip is unuseful, "
                "falling back to virtualenv"
            )
            return False
    if sys.version_info < (3, 4):
        print("venv in Python 3.3 is unuseful, falling back to virtualenv")
        return False
    try:
        sys.real_prefix
    except AttributeError:
        print("Using venv")
        return True
    print("venv breaks when nested in virtualenv, falling back to virtualenv")
    return False


def _create_with_this(env_dir, system, prompt, bare, virtualenv_py):
    if _is_venv_usable(not bare):
        _create_venv(env_dir, system, prompt, bare)
    else:
        _create_virtualenv(virtualenv_py, env_dir, system, prompt, bare)


def _create_with_python(python, env_dir, system, prompt, bare, virtualenv_py):
    # Delegate everything into a subprocess. Trick learned from virtualenv.
    cmd = [python, get_script(), str(env_dir)]
    if system:
        cmd.append("--system")
    if prompt:
        cmd.extend(["--prompt", prompt])
    if bare:
        cmd.append("--bare")
    if virtualenv_py:
        cmd.extend(["--virtualenv.py", virtualenv_py])
    subprocess.check_call(cmd)


def create(python, env_dir, system, prompt, bare, virtualenv_py=None):
    """Main entry point to use this as a module.
    """
    if not python or python == sys.executable:
        _create_with_this(
            env_dir=env_dir,
            system=system,
            prompt=prompt,
            bare=bare,
            virtualenv_py=virtualenv_py,
        )
    else:
        _create_with_python(
            python=python,
            env_dir=env_dir,
            system=system,
            prompt=prompt,
            bare=bare,
            virtualenv_py=virtualenv_py,
        )


def _main(args=None):
    # Handles the delegation from _create_with_python.
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("env_dir")
    parser.add_argument("--bare", default=False, action="store_true")
    parser.add_argument("--system", default=False, action="store_true")
    parser.add_argument("--virtualenv.py", dest="script", default=None)
    parser.add_argument("--prompt", default=None)
    opts = parser.parse_args(args)
    try:
        _create_with_this(
            env_dir=opts.env_dir,
            system=opts.system,
            prompt=opts.prompt,
            bare=opts.bare,
            virtualenv_py=opts.script,
        )
    except VirtualenvNotFound:
        print("virtualenv not available")
        sys.exit(1)


if __name__ == "__main__":
    _main()
