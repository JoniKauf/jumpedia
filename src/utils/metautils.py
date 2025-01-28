from typing import Any


def express(f_string_expr: str) -> tuple[str, str]:
    expr, found, result = f_string_expr.partition("=")

    if not found:
        raise ValueError("should be an expression of form 'f\"{expr=}\"'")
    
    return expr.strip(), result.strip()