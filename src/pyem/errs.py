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


_Exc = typing.TypeVar("_Exc", bound=Exception)
_ExcHandler = typing.Callable[[_Exc], int]
_ExcLogged = typing.Callable[..., int]
_ExcLogger = typing.Callable[[_ExcLogged], _ExcLogged]


def errorlog(etype: typing.Type[_Exc], hndl: _ExcHandler[_Exc]) -> _ExcLogger:
    """Decorator to wrap the function in a try-except block.

    This is essentially equivalent to::

        try:
            return f(*args, **kwargs)
        except etype as e:
            return hndl(e)

    The intent is to convert a bubbled-up exception into a human-readable log
    message and a proper error code, similar to how a web server converts an
    exception into a 500 response.
    """

    def decorator(f: _ExcLogged) -> _ExcLogged:
        @functools.wraps(f)
        def wrapped(*args, **kwargs) -> int:
            try:
                return f(*args, **kwargs)
            except etype as e:
                return hndl(e)

        return wrapped

    return decorator
