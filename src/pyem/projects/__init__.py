from __future__ import annotations

__all__ = ["Project", "ProjectNotFound", "Runtime", "looks_like_path"]

import dataclasses
import itertools
import pathlib

from .base import BaseProject
from .envs import looks_like_path
from .runtimes import ProjectRuntimeManagementMixin, Runtime


@dataclasses.dataclass()
class ProjectNotFound(Exception):
    start: pathlib.Path


def _is_project_root(path: pathlib.Path, marker: str) -> bool:
    # TODO: We might need to check the content to make sure it's valid?
    # This would even be REQUIRED if pyproject.toml implements workspace mode.
    return path.joinpath(marker).is_file()


class Project(ProjectRuntimeManagementMixin, BaseProject):
    @classmethod
    def discover(cls, start=None, *, up=None) -> Project:
        if not start:
            start = pathlib.Path()
        else:
            start = pathlib.Path(start)
        start = start.resolve(strict=False)

        if start.is_file():
            marker = start.name
            start = start.parent
        else:
            marker = "pyproject.toml"

        for path in [start, *itertools.islice(start.parents, up)]:
            if _is_project_root(path, marker):
                return cls(root=path)
        raise ProjectNotFound(start)
