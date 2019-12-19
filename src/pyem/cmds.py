__all__ = ["dispatch"]

import dataclasses
import functools
import logging
import pathlib
import sys
import typing

from . import __version__, procs, venvs
from ._argparse import PyEMArgumentParser
from ._logging import configure_logging
from .errs import Error
from .projects import Project


_ArgIter = typing.Iterator[str]
_ArgList = typing.List[str]

_Options = typing.Any


logger = logging.getLogger(__name__)


def _iter_until_subcommand(iterator: _ArgIter) -> _ArgIter:
    next(iterator)  # Skip argv[0].
    keep_next = False
    for arg in iterator:
        yield arg
        if keep_next:
            keep_next = False
        elif not arg.startswith("-"):  # Subcommand met.
            return
        elif "=" not in arg:
            keep_next = True
    yield ""  # Stub subcommand if the arg list is completely empty.


def _partition_argv(argv: _ArgList) -> typing.Tuple[_ArgList, str, _ArgList]:
    argv_iterator = iter(argv)
    *before_cmd, cmd = _iter_until_subcommand(argv_iterator)
    return before_cmd, cmd, list(argv_iterator)


_MISSING_PARSER_EPILOG = (
    "A special command `venv` can be used to configure virtual environments. "
    "Run `pyem venv --help` for details."
)


def _parse_missing(argv: _ArgList) -> _Options:
    parser = PyEMArgumentParser(epilog=_MISSING_PARSER_EPILOG)
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
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
        "remove",
        aliases=["rm"],
        description="Remove a virtual environment from this project.",
    )
    parser_rm.add_argument("spec", help="venv specifier")
    parser_rm.set_defaults(func=venvs.remove)

    parser_set = subparsers.add_parser(
        "set",
        aliases=["use"],
        description="Set the project's default virtual environment.",
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


@dataclasses.dataclass()
class _ProjectNotFound(Exception):
    start: pathlib.Path


# Ways to specify a project root. The .venvs directory is checked before
# pyproject.toml, so an outer .venvs directory has precedence over an inner
# pyproject.toml. This is important to resolve nested projects, where we
# usually want to reach environments set up in the outmost project, instead of
# creating new ones for each inner project.

_DiscoveryVariant = typing.Tuple[str, typing.Callable[[pathlib.Path], bool]]

_DISCOVERY_VARIANTS: typing.List[_DiscoveryVariant] = [
    (".venvs", pathlib.Path.is_dir),
    ("pyproject.toml", pathlib.Path.is_file),
]


def _project_from_path(start: pathlib.Path) -> Project:
    path = start.resolve()
    if any(path.name == n and f(path) for n, f in _DISCOVERY_VARIANTS):
        path = path.parent
    if path.is_dir():
        return Project(path)
    raise _ProjectNotFound(start)


def _project_from_discovery() -> Project:
    start = pathlib.Path.cwd()
    for marker, check in _DISCOVERY_VARIANTS:
        for path in start.joinpath(marker).parents:
            if check(path.joinpath(marker)):
                return Project(path)
    raise _ProjectNotFound(start)


def dispatch(argv: typing.Optional[_ArgList]) -> int:
    configure_logging(logging.INFO)  # TODO: Make this configurable.

    if argv is None:
        argv = sys.argv
    opts = _parse_args(argv)

    try:
        if opts.project is not None:
            project = _project_from_path(pathlib.Path(opts.project))
        else:
            project = _project_from_discovery()
    except _ProjectNotFound as e:
        logger.error("No valid project from %s", e.start)
        return Error.project_not_found

    return opts.func(project, opts)
