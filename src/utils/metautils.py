"""Anything to do with metaprogramming.

"""

from typing import Any


def express(f_string_expr: str) -> tuple[str, str]:
    expr, found, result = f_string_expr.partition("=")

    if not found:
        raise ValueError("should be an expression of form 'f\"{expr=}\"'")
    
    return expr.strip(), result.strip()




# From: https://stackoverflow.com/a/6798042/20895654
class Singleton(type):
    """If a class uses this metaclass, it will behave like a singleton.
    
    More specifically, any object "created" by this class will be the same
    object and there will always only be exactly that one instance.
    """
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]