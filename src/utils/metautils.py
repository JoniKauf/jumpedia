"""
Anything to do with metaprogramming.
"""

from string.templatelib import Template
from typing import Literal, overload


@overload
def expr[T](e: Template[T], eval: Literal[True], /) -> tuple[str, T]: ...

@overload
def expr(e: Template, eval: Literal[False], /) -> str: ...

@overload
def expr(e: Template, /) -> str: ...

def expr[T](e: Template[T], eval: bool = False, /) -> str | tuple[str, T]:
    if len(e.interpolations) != 1:
        raise ValueError("interpolation count must be 1") 
    
    if e.strings[0] or e.strings[1]:
        raise ValueError("strings must be empty")
    
    interp = e.interpolations[0]

    if interp.conversion or interp.format_spec:
        raise ValueError("format specifier not allowed")
    
    if eval:
        return (interp.expression, interp.value)
    
    return interp.expression