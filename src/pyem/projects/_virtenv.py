from __future__ import print_function

__all__ = ["create", "VirtualenvNotFound"]

import logging
import os
import subprocess
import sys

try:
    import venv
except ImportError:
    venv = None
else:
    BACKPORT_PROMPT = sys.version_info < (3, 6)

    class _EnvBuilder(venv.EnvBuilder):
        """Custom environment builder to ensure libraries are up-to-date.

        Also add support to custom prompt, and some output to make the process
        more verbose, matching virtualenv's behavior.
        """

        def __init__(self, **kwargs):
            if BACKPORT_PROMPT:
                self.prompt = kwargs.pop("prompt", None)
            super(_EnvBuilder, self).__init__(**kwargs)

        def ensure_directories(self, env_dir):
            context = super(_EnvBuilder, self).ensure_directories(env_dir)
            if BACKPORT_PROMPT and self.prompt is not None:
                context.prompt = self.prompt
            return context

        def setup_python(self, context):
            super(_EnvBuilder, self).setup_python(context)


logger = logging.getLogger(__name__)


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


def _find_virtualenv_py():
    try:
        import virtualenv
    except ImportError:
        raise VirtualenvNotFound
    else:
        virtualenv_py = get_script(virtualenv)
    return virtualenv_py


def _create_virtualenv(virtualenv_py, env_dir, system, prompt, bare):
    if not virtualenv_py:
        virtualenv_py = _find_virtualenv_py()
    if not prompt:
        prompt = os.path.basename(env_dir)
    cmd = [
        sys.executable,
        virtualenv_py,
        os.fspath(env_dir),
        "--quiet",
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
            logger.debug("venv not available, falling back to virtualenv")
        else:
            logger.debug("Using virtualenv")
        return False
    if needs_pip:
        try:
            import ensurepip  # noqa
        except ImportError:
            logger.debug(
                "venv without ensurepip is unuseful, "
                "falling back to virtualenv"
            )
            return False
    if sys.version_info < (3, 4):
        logger.debug(
            "venv in Python 3.3 is unuseful, falling back to virtualenv"
        )
        return False
    try:
        sys.real_prefix
    except AttributeError:
        logger.debug("Using venv")
        return True
    logger.debug(
        "venv breaks when nested in virtualenv, falling back to virtualenv"
    )
    return False


def _create_with_this(env_dir, system, prompt, bare, virtualenv_py):
    if _is_venv_usable(not bare):
        _create_venv(env_dir, system, prompt, bare)
    else:
        _create_virtualenv(virtualenv_py, env_dir, system, prompt, bare)


VIRTUALENV_NOT_FOUND_CODE = 714  # Arbitrary for IPC.


def _create_with_python(python, env_dir, system, prompt, bare, virtualenv_py):
    # Delegate everything into a subprocess. Trick learned from virtualenv.
    cmd = [python, get_script(), os.fspath(env_dir)]
    if system:
        cmd.append("--system")
    if prompt:
        cmd.extend(["--prompt", prompt])
    if bare:
        cmd.append("--bare")

    if not virtualenv_py:
        try:
            virtualenv_py = _find_virtualenv_py()
        except VirtualenvNotFound:
            virtualenv_py = None

    if virtualenv_py:
        cmd.extend(["--virtualenv.py", virtualenv_py])
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as e:
        if e.returncode == VIRTUALENV_NOT_FOUND_CODE:
            raise VirtualenvNotFound
        raise  # Don't know what happened, none can do.


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
        sys.exit(VIRTUALENV_NOT_FOUND_CODE)


if __name__ == "__main__":
    _main()
