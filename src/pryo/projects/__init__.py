__all__ = [
    "MultipleRuntimes",
    "NoRuntimes",
    "Project",
    "ProjectNotFound",
    "Runtime",
]

import pathlib

from .base import BaseProject
from .runtimes import (
    MultipleRuntimes,
    NoRuntimes,
    ProjectRuntimeManagementMixin,
    Runtime,
)


class ProjectNotFound(Exception):
    pass


def _is_project_root(path):
    # TODO: We might need to check the content to make sure it's valid?
    # This would even be REQUIRED if pyproject.toml implements workspace mode.
    return path.joinpath("pyproject.toml").is_file()


class Project(ProjectRuntimeManagementMixin, BaseProject):
    @classmethod
    def discover(cls, start=None):
        if not start:
            start = pathlib.Path()
        else:
            start = pathlib.Path(start)
        for path in start.resolve().joinpath("pyproject.toml").parents:
            if _is_project_root(path):
                return cls(root=path)
        raise ProjectNotFound()
