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
    out = subprocess.check_output(*args, **kwargs)
    out = out.decode(sys.stdout.encoding)
    out = out.strip()
    return out


_PY_VER_RE = re.compile(r"^(?P<major>\d+)(:?\.(?P<minor>\d+))?")


def _find_python_with_py(python: str) -> typing.Optional[pathlib.Path]:
    py = shutil.which("py")
    if not py:
        raise PyUnavailable()
    code = "import sys; print(sys.executable)"
    out = _get_command_output([str(py), f"-{python}", "-c", code])
    if not out:
        return None
    return pathlib.Path(out)


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
    return shutil.which(python)


# The prefix part is adopted from Virtualenv's approach. This allows us to find
# the most "base" prefix as possible, going through both virtualenv and venv
# boundaries. In particular `real_prefix` must be tried first since virtualenv
# does not preserve any other values.
# https://github.com/pypa/virtualenv/blob/16.7.7/virtualenv.py#L1419-L1426
_VENV_NAME_CODE = """
from __future__ import print_function
import hashlib
import sys
import platform

try:
    prefix = sys.real_prefix
except AttributeError:
    try:
        prefix = sys.base_prefix
    except AttributeError:
        prefix = sys.prefix

prefix = prefix.encode(sys.getfilesystemencoding(), "ignore")

print("{0}-{1[0]}.{1[1]}-{2[0]}-{2[4]}-{3}".format(
    platform.python_implementation(),
    sys.version_info,
    platform.uname(),
    hashlib.sha256(prefix).hexdigest()[:8],
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


def create_venv(python, env_dir, prompt):
    _virtenv.create(
        python=python, env_dir=env_dir, system=False, prompt=prompt, bare=False
    )
