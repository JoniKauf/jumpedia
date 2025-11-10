import typing as t

from src.utils import text

from . import BaseStructure, errors


def handled_unique_reals_and_norms(
    iterable: t.Iterable[str],
) -> tuple[tuple[text.RealStr, ...], tuple[text.NormStr, ...]]:
    try:
        return text.NormStr.unique_reals_and_norms(iterable)
    except ValueError as e:
        if not e.args:
            raise errors.EmptyStringError()
        else:
            raise errors.NotUniqueStringError(e.args[0], e.args[1])
