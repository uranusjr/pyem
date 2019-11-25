__all__ = ["dispatch"]

import argparse
import functools
import logging
import sys
import typing

from . import procs, venvs
from ._logging import configure_logging
from .errs import Error
from .projects import Project, ProjectNotFound


_ArgIter = typing.Iterator[str]
_ArgList = typing.List[str]

_Options = typing.Any


logger = logging.getLogger(__name__)


def _iter_until_subcommand(iterator: _ArgIter) -> _ArgIter:
    next(iterator)  # Skip argv[0].
    for arg in iterator:
        yield arg
        if not arg.startswith("-"):  # Subcommand met.
            return
    yield ""


def _partition_argv(argv: _ArgList) -> typing.Tuple[_ArgList, str, _ArgList]:
    argv_iterator = iter(argv)
    *before_cmd, cmd = _iter_until_subcommand(argv_iterator)
    return before_cmd, cmd, list(argv_iterator)


_MISSING_PARSER_EPILOG = (
    "A special command `venv` can be used to configure virtual environments. "
    "Run `pyem venv --help` for details."
)


class PyEMArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_argument(
            "--project",
            help="alternative path marking the project root",
            metavar="PATH",
            default=None,
        )

    def add_subparsers(self, **kwargs):
        # Revert to the basic parser class to avoid root arguments from being
        # defined in subparsers.
        if "parser_class" not in kwargs:
            kwargs["parser_class"] = argparse.ArgumentParser
        return super().add_subparsers(**kwargs)


def _parse_missing(argv: _ArgList) -> _Options:
    parser = PyEMArgumentParser(epilog=_MISSING_PARSER_EPILOG)
    parser.add_argument("cmd", help="command to run")
    parser.add_argument("arg", nargs="*", help="command argument")
    return parser.parse_args(argv)


def _handle_missing(parser, project, options):
    parser.print_help()


def _parse_for_venv(argv: _ArgList) -> _Options:
    parser = PyEMArgumentParser()
    parser.set_defaults(func=functools.partial(_handle_missing, parser))

    subparsers = parser.add_subparsers()

    parser_add = subparsers.add_parser(
        "add", description="Create a virtual environment for this project."
    )
    parser_add.add_argument("python", help="base interpreter to use")
    parser_add.set_defaults(func=venvs.add)

    parser_rm = subparsers.add_parser(
        "remove", description="Remove a virtual environment from this project."
    )
    parser_rm.add_argument("spec", help="venv specifier")
    parser_rm.set_defaults(func=venvs.remove)

    parser_set = subparsers.add_parser(
        "set", description="Set the project's default virtual environment."
    )
    parser_set.add_argument("spec", help="venv specifier")
    parser_set.set_defaults(func=venvs.activate)

    parser_show = subparsers.add_parser(
        "show", description="Show the project's default virtual environment."
    )
    parser_show.set_defaults(func=venvs.show_active)

    parser_list = subparsers.add_parser(
        "list", description="List virtual environments in this project."
    )
    parser_list.add_argument("--format", choices=["table"])
    parser_list.set_defaults(func=venvs.show_all)

    return parser.parse_args(argv)


def _parse_for_bridge(flags: _ArgList, cmd: str, args: _ArgList) -> _Options:
    parser = PyEMArgumentParser()
    parser.add_argument("--spec", help="venv context to use", default=None)

    options = parser.parse_args(flags)
    options.cmd = cmd
    options.args = args
    options.func = procs.run

    return options


def _parse_args(argv: _ArgList) -> _Options:
    before_cmd, cmd, after_cmd = _partition_argv(argv)
    if cmd == "venv":
        return _parse_for_venv(before_cmd + after_cmd)
    if not cmd:
        return _parse_missing(before_cmd)
    return _parse_for_bridge(before_cmd, cmd, after_cmd)


def dispatch(argv: typing.Optional[_ArgList]) -> int:
    configure_logging(logging.INFO)  # TODO: Make this configurable.

    if argv is None:
        argv = sys.argv

    opts = _parse_args(argv)

    # If we specify an explicit path, we only want to search the specified
    # directory (or the directory containing the specified file), i.e. up 0
    # times. Otherwise we search indefinitely (up=None).
    up = 0 if opts.project else None

    try:
        project = Project.discover(opts.project, up=up)
    except ProjectNotFound as e:
        logger.error("No pyproject.toml found in %s", e.start)
        return Error.project_not_found

    return opts.func(project, opts)
