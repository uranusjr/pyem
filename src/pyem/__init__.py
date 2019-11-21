"""Project-level Python virtual environment management tool.
"""

__version__ = "0.2.0"


def main() -> int:
    from .cmds import dispatch

    return dispatch(None)
