__all__ = ["run"]

import dataclasses
import errno
import logging
import os
import pathlib
import re
import shutil
import subprocess
import typing

from .errs import Error
from .projects import Project
from .projects.runtimes import MultipleRuntimeMatches, NoRuntimeMatch, Runtime


logger = logging.getLogger(__name__)


class _NoActiveRuntime(Exception):
    pass


def _find_runtime(project: Project, options) -> Runtime:
    if options.spec:
        return project.find_runtime(options.spec)
    runtime = project.get_active_runtime()
    if not runtime:
        raise _NoActiveRuntime()
    return runtime


@dataclasses.dataclass(init=False)
class _Runnable:
    _cmd: str
    _args: typing.List[str]
    _env: typing.Dict[str, str]

    def __init__(self, runtime: Runtime, cmd: str, args: typing.List[str]):
        self._cmd = cmd
        self._args = args

        env = os.environ.copy()
        env["PATH"] = runtime.derive_environ_path()
        env["VIRTUAL_ENV"] = os.fspath(runtime.root)
        self._env = env

    def _resolve_command(self) -> typing.Optional[str]:
        command = shutil.which(self._cmd, path=self._env["PATH"])
        if not command:
            return None
        path = pathlib.Path(command)
        if not path.is_file():
            return None

        # Clean up the executable path if possible. It is important to NOT
        # resolve symlinks here because venv relies on the symlink's location
        # to detect venv invocation.
        if not path.is_symlink():
            command = os.fspath(path.resolve())

        return command

    def run(self) -> int:
        raise NotImplementedError()


class _POSIXRunnable(_Runnable):
    def run(self) -> int:
        cmd = self._resolve_command()
        if not cmd:
            logger.error("Command not found: %r", self._cmd)
            return errno.ENOENT
        # This should never return.
        os.execlpe(cmd, self._cmd, *self._args, self._env)


def _quote_if_contains(value: str, pattern: str) -> str:
    if not re.search(pattern, value):
        return value
    v = re.sub(r'(\\*)"', r'\1\1\\"', value)
    return f'"{v}"'


class _NTRunnable(_Runnable):
    def _cmdify(self) -> str:
        """Encode into a cmd-executable string.

        This re-implements CreateProcess's quoting logic to turn a list of
        arguments into one single string for the shell to interpret.

        * All double quotes are escaped with a backslash.
        * Existing backslashes before a quote are doubled, so they are all
          escaped properly.
        * Backslashes elsewhere are left as-is; cmd will interpret them
          literally.

        The result is then quoted into a pair of double quotes to be grouped.

        An argument is intentionally not quoted if it does not contain
        foul characters. This is done to be compatible with Windows built-in
        commands that don't work well with quotes, e.g. everything with `echo`,
        and DOS-style (forward slash) switches.

        Foul characters include:

        * Whitespaces.
        * Parentheses in the command. (pypa/pipenv#3168)

        The intended use of this function is to pre-process an argument list
        before passing it into ``subprocess.Popen(..., shell=True)``.

        See also: https://docs.python.org/3/library/subprocess.html
        """
        cmd = _quote_if_contains(self._cmd, r"[\s()]")
        arg = " ".join(_quote_if_contains(arg, r"\s") for arg in self._args)
        return f"{cmd} {arg}"

    def run(self) -> int:
        proc = self._resolve_command()
        if proc:
            return subprocess.call([proc, *self._args], env=self._env)
        return subprocess.call(self._cmdify(), shell=True)


def run(project: Project, options) -> int:
    try:
        runtime = _find_runtime(project, options)
    except _NoActiveRuntime:
        logger.error(
            "No active runtime. Set with `venv use` first, or select one "
            "explicitly with `--spec`"
        )
        return Error.runtime_no_active
    except MultipleRuntimeMatches as e:
        logger.error(
            "Specifier %r is ambiguous; choose from:\n %s",
            e.alias,
            "\n".join(f"  {m.name}" for m in e.matches),
        )
        return Error.runtime_multiple_matches
    except NoRuntimeMatch as e:
        logger.error(
            "Specifier %r does not match any runtimes; tried:\n %s",
            e.alias,
            "\n".join(f"  {m.name}" for m in e.tried),
        )
        return Error.runtime_no_match

    klass: typing.Type[_Runnable]
    if os.name == "nt":
        klass = _NTRunnable
    else:
        klass = _POSIXRunnable

    return klass(runtime, options.cmd, options.args).run()
