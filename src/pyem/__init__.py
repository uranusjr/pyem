"""Project-level Python virtual environment management tool.
"""

__version__ = "0.4.0"


def main() -> int:
    from .cmds import dispatch

    return dispatch(None)
