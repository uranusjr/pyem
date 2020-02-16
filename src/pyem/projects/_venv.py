import dataclasses
import os
import pathlib
import subprocess
import sys
import typing


@dataclasses.dataclass()
class EnvironmentCreationError(Exception):
    context: Exception


class VirtualenvNotFound(EnvironmentError):
    pass


def _detect_virtualenv_20() -> typing.Optional[typing.Any]:
    """Detect virtualenv >=20.0 which has PEP 405 support.
    """
    try:
        import virtualenv
    except ImportError:
        return None
    try:
        version = int(virtualenv.__version__.split(".", 1)[0])
    except (AttributeError, TypeError, ValueError):
        return None
    if version < 20:
        return None
    return virtualenv


def _run_virtualenv(python: pathlib.Path, env_dir: pathlib.Path, prompt: str):
    import virtualenv

    args = [
        "--python",
        os.fspath(python),
        "--prompt",
        prompt,
        os.fspath(env_dir),
    ]
    try:
        virtualenv.cli_run(args)
    except Exception as e:
        raise EnvironmentCreationError(e)


_VENV_NOT_AVAILABLE = 715  # Arbitrary for IPC.


_CREATE_VENV_CODE = f'''\
def create_venv(sys, env_dir, prompt):
    try:
        import ensurepip
        import venv
    except ImportError:
        return {_VENV_NOT_AVAILABLE}

    # venv breaks when nested in virtualenv<20.
    if (getattr(sys, "real_prefix", None)
            and not os.path.isfile(os.path.join(sys.prefix, "pyenv.cfg"))):
        return {_VENV_NOT_AVAILABLE}

    backports_prompt = sys.version_info < (3, 6)

    class EnvBuilder(venv.EnvBuilder):
        """Custom environment builder to add custom prompt support.
        """
        def __init__(self, **kwargs):
            if backports_prompt:
                self.prompt = kwargs.pop("prompt", None)
            super().__init__(**kwargs)

        def ensure_directories(self, env_dir):
            context = super().ensure_directories(env_dir)
            if backports_prompt and self.prompt is not None:
                context.prompt = self.prompt
            return context

    builder = EnvBuilder(prompt=prompt)
    builder.create(env_dir)
'''

_CREATE_VENV_INVOKE_CODE = f"""\
{_CREATE_VENV_CODE}
import sys
sys.exit(create_venv(sys, sys.argv[1], sys.argv[2]))
"""


def _create_with_this(env_dir: pathlib.Path, prompt: str):
    env: typing.Dict[str, typing.Any] = {}
    exec(_CREATE_VENV_CODE, env)
    try:
        returncode = env["create_venv"](sys, os.fspath(env_dir), prompt)
    except Exception as e:
        raise EnvironmentCreationError(e)
    return returncode


def _create_with(python: pathlib.Path, env_dir: pathlib.Path, prompt: str):
    args = [
        os.fspath(python),
        "-c",
        _CREATE_VENV_INVOKE_CODE,
        os.fspath(env_dir),
        prompt,
    ]
    proc = subprocess.run(args)
    return proc.returncode


def create(python: pathlib.Path, env_dir: pathlib.Path, prompt: str):
    if _detect_virtualenv_20():
        _run_virtualenv(python, env_dir, prompt)
        return

    if python.samefile(sys.executable):
        returncode = _create_with_this(env_dir, prompt)
    else:
        returncode = _create_with(python, env_dir, prompt)

    if not returncode:
        return
    if returncode != _VENV_NOT_AVAILABLE:
        context = RuntimeError(f"unknown error {returncode}")
        raise EnvironmentCreationError(context)
    raise VirtualenvNotFound()
