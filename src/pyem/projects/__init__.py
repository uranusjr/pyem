__all__ = ["Project", "Runtime"]

from .base import BaseProject
from .runtimes import ProjectRuntimeManagementMixin, Runtime


class Project(ProjectRuntimeManagementMixin, BaseProject):
    pass
