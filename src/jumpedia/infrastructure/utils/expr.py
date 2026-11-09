"""Utility functions for extracting source strings from Python expressions.

This module provides a few functions that enable it to convert expressions embedded in
:class:`~string.templatelib.Template` interpolations into their source strings, with
optional access to the evaluated value or support for lazy expressions represented by
parameterless lambda functions.
"""

# This was coded by JoniKauf, but he was too lazy to release it as its own 
# repository yet.
 
__version__ = "1.0.0"

__all__ = ["expr", "expr_eval", "expr_lazy"]

import types as ts
import typing as t
from string.templatelib import Interpolation, Template


def validate_template_for_expr(
    template: Template[t.Any], *, lazy: bool
) -> Interpolation[t.Any]:
    """Validate if a template has the right structure for expr functions.

    Args:
        template (:class:`Template`):
            The template of one interpolation to validate.

        lazy (:class:`~builtins.bool`):
            Whether it is a lazy operation and the template should therefore contain a
            valid lambda function as its first interpolation's value.

    Raises:
        TypeError (:class:`~builtins.TypeError`):
            If `template` is not a :class:`Template` or the template does not exactly
            have one interpolation or `lazy` is True and the first  interpolation's
            value is not a lambda function.

        ValueError (:class:`~builtins.ValueError`):
            The template's strings are not empty or whitespace-only.

    Returns:
        :class:`Interpolation`: The first interpolation of the template, if the template
        is valid.
    """
    if not isinstance(template, Template):
        raise TypeError("Not a template")

    if len(template.interpolations) != 1:
        raise TypeError("Not exactly one interpolation")

    if template.strings[0].strip() or template.strings[1].strip():
        raise ValueError("Surrounding strings not empty or whitespace")

    interp = template.interpolations[0]

    if not lazy:
        return interp

    v = interp.value

    if not isinstance(v, ts.FunctionType) or v.__name__ != "<lambda>":
        raise TypeError("Interpolation value is not a lambda function")

    code = v.__code__

    if code.co_argcount != 0 or code.co_kwonlyargcount != 0:
        raise TypeError("Lambda function value has parameters")

    return interp


def zero_arg_interpolation_lambda_expr_to_return_value_expr(s: str) -> str:
    """Shorten the source string of an interpolation's 0 argument lambda function value
    into the source string of the return value of that lambda function.

    Args:
        s (:class:`~builtins.str`):
            The string of an interpolation lambda expression.

    Returns:
        str (:class:`~builtins.str`):
            The string of the return value of the specified lambda expression.
    """
    # Worst possible start: "  (  lambda  :  10  )  "
    # Whitespace after ')' is technically stripped by Python already, but let's not make
    # this an assumption.

    return (
        s.strip()  # "  (  lambda  :  1 + 1  )  "  #   "(  lambda  :  1 + 1  )"
        .removeprefix("(")  #    "  lambda  :  1 + 1  )"
        .removesuffix(")")  #    "  lambda  :  1 + 1  "
        .strip()  #      "lambda  :  1 + 1"
        .removeprefix("lambda")  #            "  :  1 + 1"
        .lstrip()  #              ":  1 + 1"
        .removeprefix(":")  #               "  1 + 1"
        .lstrip()  #                 "1 + 1"
    )


def expr(t: Template[t.Any]) -> str:
    """Turn an expression into source string.

    This also has the side effect, that the expression gets evaluated. Use
    :func:`expr_lazy` to avoid this if necessary.

    Args:
        t (:class:`Template`):
            A single-interpolation literal template with empty or whitespace-only
            strings. The interpolation's value is turned into its source string.

    Returns:
        str (:class:`~builtins.str`):
            The source string of the expression in the template's single interpolation's
            value.
    """
    return validate_template_for_expr(t, lazy=False).expression


def expr_eval[T](t: Template[T]) -> tuple[str, T]:  # type: ignore
    """Turn an expression into its source string and evaluated value.

    This expression is only evaluated once.

    Args:
        t (:class:`Template` of `T`):
            A single-interpolation literal template with empty or whitespace-only
            strings. The interpolation's value is turned into its source string and
            returned together with its evaluated value.

    Returns:
        tuple[str, T] (:class:`~builtins.tuple` of :class:`~builtins.str`, `T`):
            A tuple containing the source string of the expression in the  template's
            single interpolation's value and that value itself.
    """
    interp = validate_template_for_expr(t, lazy=False)
    return interp.expression, interp.value


def expr_lazy(t: Template[t.Callable[[], t.Any]]) -> str:
    """Turn an expression into its source string without evaluating it.

    Unlike :func:`expr`, this function expects the template's interpolation value to be
    a parameterless lambda function. The source string of that lambda's return value is
    returned without evaluating the expression.

    Args:
        t (:class:`Template`):
            A single-interpolation literal template with empty or whitespace-only
            strings. The interpolation's value must be a parameterless lambda function
            whose return expression is turned into its source string.

    Returns:
        str (:class:`~builtins.str`):
            The source string of the return expression of the template's single
            interpolation's lambda function return value.
    """
    return zero_arg_interpolation_lambda_expr_to_return_value_expr(
        validate_template_for_expr(t, lazy=True).expression
    )
