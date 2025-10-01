import functools
import inspect
from typing import Any, Callable, MutableMapping, Protocol


def get_relevant_kwargs(
    kwargs: dict[str, Any], func: Callable[..., Any]
) -> dict[str, Any]:
    """Get all kwargs a given function accepts."""
    sig = inspect.signature(func)
    return {k: v for k, v in kwargs.items() if k in sig.parameters}


class classproperty[TOwner: Any, TValue: Any]:
    def __init__(self, wrapped: Callable[[type[TOwner]], TValue]) -> None:
        self.__wrapped__ = wrapped

    def __get__(self, instance: None, owner: type[TOwner]) -> TValue:
        return self.__wrapped__(owner)


class Singleton(type):
    """If a class uses this metaclass, it will behave like a singleton.

    More specifically, any object "created" by this class will be the same
    object and there will always only be exactly that one instance.
    """

    _instance = None

    def __call__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instance
