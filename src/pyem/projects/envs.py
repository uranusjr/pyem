__all__ = [
    "PyUnavailable",
    "create_venv",
    "get_interpreter_quintuplet",
    "looks_like_path",
    "resolve_python",
]

import os
import pathlib
import re
import shutil
import subprocess
import sys
import typing

from . import _virtenv


class PyUnavailable(Exception):
    pass


def _get_command_output(*args, **kwargs) -> str:
    proc = subprocess.run(*args, **kwargs, stdout=subprocess.PIPE)
    if proc.returncode:
        return ""
    return proc.stdout.decode(sys.stdout.encoding).strip()


_PY_VER_RE = re.compile(
    r"""
    ^
    (\d+)           # Major.
    (:?\.(\d+))?    # Minor.
    (:?\-(32|64))?  # Either -32 or -64.
    $
    """,
    re.VERBOSE,
)


def _find_python_with_py(python: str) -> typing.Optional[pathlib.Path]:
    py = shutil.which("py")
    if not py:
        raise PyUnavailable()
    code = "import sys; print(sys.executable)"
    out = _get_command_output([py, f"-{python}", "-c", code])
    if not out:
        return None
    return pathlib.Path(out).resolve()


def looks_like_path(v: typing.Union[pathlib.Path, str]) -> bool:
    if isinstance(v, pathlib.Path):
        return True
    if os.sep in v:
        return True
    if os.altsep and os.altsep in v:
        return True
    return False


def resolve_python(python: str) -> typing.Optional[pathlib.Path]:
    match = _PY_VER_RE.match(python)
    if match:
        return _find_python_with_py(python)
    if looks_like_path(python):
        return pathlib.Path(python)
    resolved = shutil.which(python)
    if not resolved:
        return None
    return pathlib.Path(resolved)


# The prefix part is adopted from Virtualenv's approach. This allows us to find
# the most "base" prefix as possible, going through both virtualenv and venv
# boundaries. In particular `real_prefix` must be tried first since virtualenv
# does not preserve any other values.
# https://github.com/pypa/virtualenv/blob/16.7.7/virtualenv.py#L1419-L1426
_VENV_NAME_CODE = """
from __future__ import print_function
import hashlib
import sys
import sysconfig
import platform

try:
    prefix = sys.real_prefix
except AttributeError:
    try:
        prefix = sys.base_prefix
    except AttributeError:
        prefix = sys.prefix

prefix = prefix.encode(sys.getfilesystemencoding(), "ignore")

print("{impl}-{vers}-{syst}-{plat}-{hash}".format(
    impl=platform.python_implementation(),
    vers=sysconfig.get_python_version(),
    syst=platform.uname().system,
    plat=sysconfig.get_platform().split("-")[-1],
    hash=hashlib.sha256(prefix).hexdigest()[:8],
).lower())
"""


def get_interpreter_quintuplet(python: os.PathLike) -> str:
    """Build a unique identifier for the interpreter to place the venv.

    This is done by asking the interpreter to format a string containing the
    following parts, lowercased and joined with `-` (dash):

    * Python inplementation.
    * Python version (major.minor).
    * Plarform name.
    * Processor type.
    * A 8-char hash of the interpreter prefix for disambiguation.

    Example: `cpython-3.7-darwin-x86_64-3d3725a6`.
    """
    return _get_command_output([str(python), "-c", _VENV_NAME_CODE])


def create_venv(python: os.PathLike, env_dir: pathlib.Path, prompt: str):
    _virtenv.create(
        python=str(python),
        env_dir=env_dir,
        system=False,
        prompt=prompt,
        bare=False,
    )
