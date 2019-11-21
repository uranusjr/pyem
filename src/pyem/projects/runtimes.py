__all__ = [
    # Exceptions.
    "FailedToRemove",
    "InterpreterNotFound",
    "MultipleRuntimes",
    "NoRuntimes",
    "PyUnavailable",
    "RuntimeExists",
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
from ._envs import (
    PyUnavailable,
    create_venv,
    get_interpreter_quintuplet,
    looks_like_path,
    resolve_python,
)


_VENV_CONTAINER_NAME = ".venvs"

_VENV_MARKER_NAME = ".venv"


def _paths(*entries):
    return os.pathsep.join(str(e) for e in entries)


@dataclasses.dataclass()
class _VirtualEnvironmentInvalid(Exception):
    root: pathlib.Path


@dataclasses.dataclass()
class _VirtualEnvironment:
    root: pathlib.Path

    def exists(self) -> bool:
        return self.root.is_dir()

    @property
    def name(self) -> str:
        return self.root.name

    @property
    def python(self) -> pathlib.Path:
        path = _paths(self.root.joinpath("bin"), self.root.joinpath("Scripts"))
        python = shutil.which("python", path=path)
        if python is None:
            raise _VirtualEnvironmentInvalid(self.root)
        return python

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

    def derive_environ(self, base=None):
        if base is None:
            base = os.environ
        environ = base.copy()
        environ["PATH"] = _paths(
            self.root.joinpath("bin"),
            self.root.joinpath("Scripts"),
            environ["PATH"],
        )
        environ["VIRTUAL_ENV"] = str(self.root)
        return environ


Runtime = _VirtualEnvironment


@dataclasses.dataclass()
class InterpreterNotFound(Exception):
    spec: str


@dataclasses.dataclass()
class RuntimeExists(Exception):
    runtime: Runtime


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
    def from_alias(cls, alias):
        if looks_like_path(alias):
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
class NoRuntimes(Exception):
    alias: str
    tried: typing.List[Runtime]


@dataclasses.dataclass()
class MultipleRuntimes(Exception):
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

    def _get_runtime(self, name: str) -> Runtime:
        """Get a runtime with name.

        This does not check whether the runtime actually exists.
        """
        return Runtime(self._runtime_container.joinpath(name))

    def iter_runtimes(self) -> typing.Iterator[Runtime]:
        if not self._runtime_container.is_dir():
            return
        for entry in self._runtime_container.iterdir():
            if not entry.is_dir():
                continue
            yield Runtime(entry)

    def create_runtime(self, interpreter_spec: str) -> Runtime:
        """Create a new runtime based on given base interpreter.
        """
        python = resolve_python(interpreter_spec)
        if not python:
            raise InterpreterNotFound(interpreter_spec)

        runtime = self._get_runtime(get_interpreter_quintuplet(python))
        if runtime.exists():
            raise RuntimeExists(runtime)

        # TODO: Make prompt configurable? Include quintuplet in prompt?
        create_venv(python=python, env_dir=runtime.root, prompt=self.name)

        return runtime

    def find_runtime(self, alias: str) -> Runtime:
        """Choose exactly one matching runtime from an alias.

        An alias can take one of the following forms:

        * Python version (``3.7``)
        * Python implementation + version (``cpython-3.7``)
        * Python implementation + version + bitness (`cpython-3.7-x86_64`)
        * Full identifier minus the hash (`cpython-3.7-darwin-x86_64`)
        * Full identifier + hash (`cpython-3.7-darwin-x86_64-3d3725a6`)
        * Path to a Python interpreter

        The retuend runtime is guarenteed to exist. Raises `NoRuntimes` if
        no match is found, `MultipleRuntimes` if the alias is ambiguous.
        """
        try:
            matcher = _QuintapletMatcher.from_alias(alias)
        except ValueError:
            raise NoRuntimes(alias, list(self.iter_runtimes()))
        matches = [
            runtime
            for runtime in self.iter_runtimes()
            if matcher.match(runtime)
        ]
        if not matches:
            raise NoRuntimes(alias, list(self.iter_runtimes()))
        if len(matches) > 1:
            raise MultipleRuntimes(alias, matches)
        return matches[0]

    def activate_runtime(self, runtime: Runtime):
        """Set runtime as active.

        This simply writes the runtime venv's path to a file named `.venv`.
        This is intentionally designed to be compatibile with Pipenv because
        why not.

        See: https://github.com/pypa/pipenv/issues/2680
        """
        marker = self._runtime_marker
        if marker.exists() and not marker.is_file():
            raise PermissionError(f"Not a file: {repr(str(marker))}")
        with marker.open("w", newline="\n", encoding="utf8") as f:
            f.write(f"{_VENV_CONTAINER_NAME}/{runtime.name}")

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
            # TODO: Check the name is a valid quintuplet.
            runtime = self._get_runtime(name)
            if not runtime.exists():
                return None
            return runtime

        # Compatibility case: .venv is a link to a dir in `{root}/.venvs`.
        # Use that if it's managed.
        if self._runtime_marker.is_symlink():
            if not self._runtime_marker.is_dir():
                return None
            path = self._runtime_marker.resolve()
            if self._runtime_container not in path.parents:
                return None
            # TODO: Check the name is a valid quintuplet.
            return Runtime(path)

        return None

    def remove_runtime(self, runtime: Runtime):
        # Deactivate env if it is going to be removed.
        if self.get_active_runtime() == runtime:
            self._runtime_marker.unlink()
        if runtime.exists():
            shutil.rmtree(runtime.root)
