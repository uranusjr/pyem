"""Project-level Python virtual environment management tool.
"""

__version__ = "1.0.2"


def main() -> int:
    from .cmds import dispatch

    return dispatch(None)
