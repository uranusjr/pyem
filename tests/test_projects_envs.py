import pytest

from pyem.projects.envs import _PY_VER_RE


@pytest.mark.parametrize(
    "argument, matched",
    [
        ("3", True),
        ("4.5", True),
        ("3.10", True),
        ("3.7-32", True),
        ("3.11-64", True),
        ("pypy3", False),
        ("4.2-54", False),
    ],
)
def test_py_version_argument(argument, matched):
    assert bool(_PY_VER_RE.match(argument)) == matched
