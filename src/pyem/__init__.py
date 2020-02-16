"""Project-level Python virtual environment management tool.
"""

__version__ = "2.0.0b2"


def main() -> int:
    from .cmds import dispatch

    return dispatch(None)
