import typing as t

from utils import text

from . import errors


def handled_unique_reals_and_norms(
    iterable: t.Iterable[str],
) -> tuple[tuple[text.RealStr, ...], tuple[text.NormStr, ...]]:
    try:
        return text.NormStr.unique_reals_and_norms(iterable)
    except ValueError as e:
        raise errors.SynNotUniqueError(e.args[0], e.args[1])


def first_or_none[T](seq: t.Iterable[T]) -> T | None:
    return next(iter(seq), None)


def first_or_none_of_item_vk_of_mapping[TK, TV](
    mapping: t.Mapping[TK, TV],
) -> tuple[TV, TK] | None:
    first = first_or_none(mapping.items())

    if first is None:
        return None

    return first[1], first[0]
