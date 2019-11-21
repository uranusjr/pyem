import enum
import functools
import typing


class Error(enum.IntEnum):
    interpreter_not_found = enum.auto()
    project_not_found = enum.auto()
    py_unavailable = enum.auto()
    runtime_invalid = enum.auto()
    runtime_multiple_matches = enum.auto()
    runtime_no_active = enum.auto()
    runtime_no_match = enum.auto()
    virtualenv_unavailable = enum.auto()


_Error = typing.TypeVar("_Error")
_ErrorHandler = typing.Callable[[_Error], int]
_ErrorLogged = typing.Callable[..., int]
_ErrorLogger = typing.Callable[[_ErrorLogged], _ErrorLogged]


def errorlog(etype: typing.Type[_Error], hndl: _ErrorHandler) -> _ErrorLogger:
    def decorator(f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except etype as e:
                return hndl(e)

        return wrapped

    return decorator
