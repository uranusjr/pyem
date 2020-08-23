"""Project-level Python virtual environment management tool.
"""

__version__ = "2.1.0"


def main() -> int:
    from .cmds import dispatch

    return dispatch(None)
