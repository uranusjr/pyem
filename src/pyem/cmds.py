__all__ = ["dispatch"]


import argparse
import functools
import sys
import typing

from . import procs, venvs
from .projects import Project


_ArgIter = typing.Iterator[str]
_ArgList = typing.List[str]

_Options = typing.Any


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


def _handle_missing(parser, project, options):
    parser.print_help()


def _parse_missing(argv: _ArgList) -> _Options:
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd", help="command to run")
    parser.add_argument("arg", nargs="*", help="command argument")
    return parser.parse_args(argv)


def _parse_for_venv(argv: _ArgList) -> _Options:
    parser = argparse.ArgumentParser()
    parser.set_defaults(func=functools.partial(_handle_missing, parser))

    subparsers = parser.add_subparsers()

    parser_add = subparsers.add_parser("add", usage="create venv")
    parser_add.add_argument("python", help="base interpreter to use")
    parser_add.set_defaults(func=venvs.add)

    parser_rm = subparsers.add_parser("remove", usage="remove venv")
    parser_rm.add_argument("spec", help="venv specifier")
    parser_rm.set_defaults(func=venvs.remove)

    parser_set = subparsers.add_parser("set", usage="set default venv")
    parser_set.add_argument("spec", help="venv specifier")
    parser_set.set_defaults(func=venvs.activate)

    parser_list = subparsers.add_parser("list", usage="list available venvs")
    parser_list.add_argument("--format", choices=["table"])
    parser_list.set_defaults(func=venvs.show_all)

    return parser.parse_args(argv)


def _parse_for_bridge(flags: _ArgList, cmd: str, args: _ArgList) -> _Options:
    parser = argparse.ArgumentParser()
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


def dispatch(argv: typing.Optional[_ArgList]):
    if argv is None:
        argv = sys.argv
    project = Project.discover()
    opts = _parse_args(argv)
    return opts.func(project, opts)
