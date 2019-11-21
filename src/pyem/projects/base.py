__all__ = ["BaseProject"]

import dataclasses
import pathlib


@dataclasses.dataclass()
class BaseProject:
    root: pathlib.Path

    @property
    def name(self):
        # TODO: Make this configurable.
        return self.root.name
