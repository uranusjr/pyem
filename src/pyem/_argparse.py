import argparse


class _AliasedSubParsersAction(argparse._SubParsersAction):
    """Custom subparser to also register subcommand aliases.

    This relies heavily on argparse internals, but I guess it's good enough.
    Base on <https://gist.github.com/sampsyo/471779> but vastly simplified:

    * Only support Python 3.
    * Does not override the help message so aliases *do not* show.

    I use this mostly for backward compatibility purposes (change subcommand
    names without disrupting old users) so the second point it actually a plus.
    """

    def add_parser(self, name, *, aliases=(), **kwargs):
        parser = super().add_parser(name, **kwargs)
        for alias in aliases:
            self._name_parser_map[alias] = parser
        return parser


class PyEMArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register("action", "parsers", _AliasedSubParsersAction)
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
