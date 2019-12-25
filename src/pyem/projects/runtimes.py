__all__ = [
    # Exceptions.
    "EnvironmentCreationError",
    "FailedToRemove",
    "InterpreterNotFound",
    "MultipleRuntimeMatches",
    "NoRuntimeMatch",
    "PyUnavailable",
    "RuntimeActive",
    "RuntimeInvalid",
    "RuntimeExists",
    "VirtualenvNotFound",
    # Functionalities.
    "ProjectRuntimeManagementMixin",
    "Runtime",
]

import dataclasses
import os
import pathlib
import shutil
import typing

from .base import BaseProject
from .envs import (
    EnvironmentCreationError,
    PyUnavailable,
    create_venv,
    get_interpreter_quintuplet,
    resolve_python,
)
from ._virtenv import VirtualenvNotFound


_VENV_CONTAINER_NAME = ".venvs"

_VENV_MARKER_NAME = ".venv"


@dataclasses.dataclass()
class _VirtualEnvironmentInvalid(Exception):
    root: pathlib.Path


@dataclasses.dataclass()
class _VirtualEnvironment:
    """Represents a virtual environment.

    The root MUST be a directory (or a symlink to a directory). For now this
    does not ensure the environment is working though; maybe we should.
    """

    root: pathlib.Path

    @typing.overload
    def derive_environ_path(self) -> str:
        ...

    @typing.overload
    def derive_environ_path(self, *, path: str) -> str:
        ...

    def derive_environ_path(self, *, path=None) -> str:
        """Derive this virtual environment's supposed PATH environ.

        If `base` is not passed, all entries in the virtual environment and
        the default PATH are searched.

        If `base` is given, it should be a string to override the environment's
        default PATH. This is useful if you don't want to search in the global
        (non-venv) PATH -- pass in an empty string so the command is only
        searched in the virtual environment.
        """
        if path is None:
            path = os.environ.get("PATH")
        paths = [
            os.fspath(path)
            for path in (self.root.joinpath(n) for n in ["bin", "Scripts"])
            if path.is_dir()
        ]
        if path:
            paths.append(path)
        return os.pathsep.join(paths)

    @property
    def name(self) -> str:
        return self.root.name

    @property
    def python(self) -> pathlib.Path:
        python = shutil.which("python", path=self.derive_environ_path(path=""))
        if python is None:
            raise _VirtualEnvironmentInvalid(self.root)
        return pathlib.Path(python).resolve()

    @property
    def site_packages(self) -> pathlib.Path:
        patterns = [
            "lib/python*.*/site-packages",  # POSIX.
            "Lib/site-packages",  # Windows.
        ]
        for pattern in patterns:
            for path in self.root.glob(pattern):
                if path.is_dir():
                    return path
        raise _VirtualEnvironmentInvalid(self.root)


Runtime = _VirtualEnvironment
RuntimeInvalid = _VirtualEnvironmentInvalid


@dataclasses.dataclass()
class InterpreterNotFound(Exception):
    spec: str


@dataclasses.dataclass()
class RuntimeExists(Exception):
    runtime: Runtime


@dataclasses.dataclass()
class RuntimeActive(Exception):
    runtime: Runtime


def _looks_like_path(v: str) -> bool:
    """A string looks like a path if it contains one or more path separators.
    """
    if os.sep in v:
        return True
    if os.altsep and os.altsep in v:
        return True
    return False


class _QuintapletMatcher:
    """Helper class to simplify quintaplet matching logic in `find_runtime`.
    """

    def __init__(self, parts, hash_=""):
        self._parts = [p.lower() for p in parts]
        self._hash = hash_.lower()

    @classmethod
    def _from_5(cls, v):
        return cls(v[:4], v[4])

    @classmethod
    def _from_4(cls, v):
        return cls(v)

    @classmethod
    def _from_3(cls, v):
        return cls(v[:2] + [""] + v[2:])

    @classmethod
    def _from_2(cls, v):
        return cls(v + ["", ""])

    @classmethod
    def _from_1(cls, v):
        return cls([""] + v + ["", ""])

    @classmethod
    def from_alias(cls, alias: str):
        # Only treat the input as a path if it contains a path sep. This deals
        # with the edge case that there is a file in cwd with the same name as
        # the supplied alias. We prioritize resolving the alias over the file.
        if _looks_like_path(alias) and os.path.isfile(alias):
            alias = get_interpreter_quintuplet(alias)

        parts = alias.split("-")
        try:
            ctor = {
                5: cls._from_5,
                4: cls._from_4,
                3: cls._from_3,
                2: cls._from_2,
                1: cls._from_1,
            }[len(parts)]
        except KeyError:
            raise ValueError(alias)
        return ctor(parts)

    def match(self, runtime):
        parts = runtime.name.split("-")
        if len(parts) != 5:
            return False
        hash_ = parts.pop()
        if self._hash and self._hash != hash_:
            return False
        return all(a == b for a, b in zip(parts, self._parts) if a and b)


@dataclasses.dataclass()
class NoRuntimeMatch(Exception):
    alias: str
    tried: typing.List[Runtime]


@dataclasses.dataclass()
class MultipleRuntimeMatches(Exception):
    alias: str
    matches: typing.List[Runtime]


@dataclasses.dataclass()
class FailedToRemove(UserWarning):
    path: pathlib.Path
    reason: str


class ProjectRuntimeManagementMixin(BaseProject):
    """Runtime management functionalities for project.
    """

    @property
    def _runtime_marker(self) -> pathlib.Path:
        return self.root.joinpath(_VENV_MARKER_NAME)

    @property
    def _runtime_container(self) -> pathlib.Path:
        return self.root.joinpath(_VENV_CONTAINER_NAME)

    def iter_runtimes(self) -> typing.Iterator[Runtime]:
        if not self._runtime_container.is_dir():
            return
        for entry in self._runtime_container.iterdir():
            if not entry.is_dir():
                continue
            # TODO: Should be only list valid runtimes with quintuplet name?
            yield Runtime(entry)

    def create_runtime(self, interpreter_spec: str) -> Runtime:
        """Create a new runtime based on given base interpreter.
        """
        python = resolve_python(interpreter_spec)
        if not python:
            raise InterpreterNotFound(interpreter_spec)

        env_name = get_interpreter_quintuplet(python)
        env_dir = self._runtime_container.joinpath(env_name)
        if env_dir.exists():
            raise RuntimeExists(Runtime(env_dir))

        # TODO: Make prompt configurable? Include quintuplet in prompt?
        create_venv(python=python, env_dir=env_dir, prompt=self.name)

        return Runtime(env_dir)

    def find_runtime(self, alias: str) -> Runtime:
        """Choose exactly one matching runtime from an alias.

        An alias can take one of the following forms:

        * Python version (``3.7``)
        * Python implementation + version (``cpython-3.7``)
        * Python implementation + version + bitness (`cpython-3.7-x86_64`)
        * Full identifier minus the hash (`cpython-3.7-darwin-x86_64`)
        * Full identifier + hash (`cpython-3.7-darwin-x86_64-3d3725a6`)
        * Path to a Python interpreter

        The retuend runtime is guarenteed to exist. Raises `NoRuntimeMatch` if
        no match is found, `MultipleRuntimeMatches` if the alias is ambiguous.
        """
        # TODO: Should we check the runtime to return is valid?
        try:
            matcher = _QuintapletMatcher.from_alias(alias)
        except ValueError:
            raise NoRuntimeMatch(alias, list(self.iter_runtimes()))
        matches = [
            runtime
            for runtime in self.iter_runtimes()
            if matcher.match(runtime)
        ]
        if not matches:
            raise NoRuntimeMatch(alias, list(self.iter_runtimes()))
        if len(matches) > 1:
            raise MultipleRuntimeMatches(alias, matches)
        return matches[0]

    def activate_runtime(self, runtime: Runtime):
        """Set runtime as active.

        This simply writes the runtime venv's path to a file named `.venv`.
        This is intentionally designed to be compatibile with Pipenv because
        why not.

        See: https://github.com/pypa/pipenv/issues/2680
        """
        marker = self._runtime_marker
        with marker.open("w", newline="\n", encoding="utf8") as f:
            f.write(f"{_VENV_CONTAINER_NAME}/{runtime.name}")

    def deactivate_runtime(self):
        self._runtime_marker.unlink()

    def get_active_runtime(self) -> typing.Optional[Runtime]:
        """Get the active runtime.
        """
        # Normal case: marker is a file. It should contain a relative path
        # pointing to a venv in `{root}/.venvs`.
        if self._runtime_marker.is_file():
            content = self._runtime_marker.read_text(encoding="utf8").strip()
            prefix, name = content.split("/", 1)
            if prefix != _VENV_CONTAINER_NAME:
                return None
            path = self._runtime_container.joinpath(name)
            if not path.exists():
                return None
            return Runtime(path)

        # Compatibility case: .venv is a link to a dir in `{root}/.venvs`.
        # Use that if it's managed.
        if self._runtime_marker.is_symlink():
            if not self._runtime_marker.is_dir():
                return None
            path = self._runtime_marker.resolve()
            if self._runtime_container not in path.parents:
                return None
            return Runtime(path)

        return None

    def remove_runtime(self, runtime: Runtime):
        if self.get_active_runtime() == runtime:
            raise RuntimeActive(runtime)
        if runtime.root.is_symlink():
            runtime.root.unlink()
        else:
            shutil.rmtree(runtime.root)
