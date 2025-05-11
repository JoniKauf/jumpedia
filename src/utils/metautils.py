"""Anything to do with metaprogramming.

"""

from typing import Any

def _express_inner(f_string_expr: str, full: bool, second_val: bool) -> tuple[str, ...]:
    expr, found, result = f_string_expr.partition("=")

    if not found:
        raise ValueError("should be an expression of form 'f\"{expr=}\"'")
    
    expr = expr.strip()

    if not full:
        expr = expr.rsplit('.', 1)[-1]

    return (expr, result.strip()) if second_val else (expr,)

def varname(f_string_expr: str, full: bool) -> str:
    return _express_inner(f_string_expr, full, False)[0]

def express(f_string_expr: str, full: bool) -> tuple[str, str]:
    result = _express_inner(f_string_expr, full, True)
    return (result[0], result[1])



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