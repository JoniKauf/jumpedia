

import inspect
from typing import Any, Callable

def get_relevant_kwargs(kwargs: dict[str, Any], func: Callable[..., Any]) -> dict[str, Any]:
    """Get all kwargs a given function accepts."""
    sig = inspect.signature(func)
    return {k: v for k, v in kwargs.items() if k in sig.parameters}
