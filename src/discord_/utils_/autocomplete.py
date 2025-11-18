import functools
import typing as t
from collections import defaultdict

import discord as dc
from discord import app_commands as acmds

type ChoiceValueT = int | float | str
type ChoiceT = acmds.Choice[ChoiceValueT]


@functools.lru_cache(maxsize=2**20)
def _same_chars_contained(container: str, s: str) -> bool:
    chars: dict[str, int] = defaultdict(int)

    for char in container:
        chars[char] += 1

    for char in s:
        chars[char] -= 1

        if chars[char] < 0:
            return False

    return True


AUTOCOMPLETE_LIMIT = 25
PAGING_SUFFIX: str = ">"
REVERSE_PAGING_SUFFIX: str = "<"
MAX_PAGE: int = 99_999

BEST_MATCH_CRITERIAS: tuple[t.Callable[[str, str], bool], ...] = (
    lambda elem, current: elem == current,
    lambda elem, current: elem.startswith(current),
    lambda elem, current: current in elem,
    # _same_chars_contained
)


def _convert_to_choices(elems: t.Sequence[ChoiceValueT]) -> list[ChoiceT]:
    return [acmds.Choice(name=str(elem), value=elem) for elem in elems]


def _convert_to_choice_values(
    elems: t.Sequence[ChoiceT | ChoiceValueT],
) -> list[ChoiceValueT]:
    return [elem.value if isinstance(elem, acmds.Choice) else elem for elem in elems]


def _verify_limit(limit: int) -> None:
    if limit > AUTOCOMPLETE_LIMIT:
        raise errors.ImpossibleError("discord limit of 25 choices surpassed")

    if limit < 1:
        raise errors.ImpossibleError("at least 1 element required for autocomplete")


def _save_ceildiv(a: int | float, b: int | float) -> int:
    return int(-(a // -b))


def _get_page(s: str) -> tuple[int, bool, str]:
    DEFAULT = (1, False, s)
    page: int = DEFAULT[0]

    for suf, reverse in ((PAGING_SUFFIX, False), (REVERSE_PAGING_SUFFIX, True)):
        left, sep, n = s.rpartition(suf)

        if sep and n.isdigit():
            # 0 converts to 1
            page = int(n) or 1

            if page > MAX_PAGE:
                return DEFAULT

            return page, reverse, left.rstrip()

    return DEFAULT


def _open_page(
    elems: t.Sequence[ChoiceValueT], page: int, reverse: bool, per_page_limit: int
) -> list[ChoiceValueT]:
    elems = list(elems)

    if len(elems) == 0:
        return elems

    total_pages: int = _save_ceildiv(len(elems), per_page_limit)

    if reverse:
        start: int = (total_pages - page) * per_page_limit
    else:
        start: int = (page - 1) * per_page_limit

    end: int = start + per_page_limit

    return elems[start:end]  # or elems[:per_page_limit]


def _best_match(
    current: str, elems: t.Sequence[ChoiceValueT], limit: int
) -> list[ChoiceValueT]:
    results: list[list[ChoiceValueT]] = [[] for _ in range(len(BEST_MATCH_CRITERIAS))]
    current = current.casefold()

    normalized_to_v: dict[str, ChoiceValueT] = {
        str(elem).casefold(): elem for elem in elems
    }

    for k, v in normalized_to_v.items():
        for i, criteria in enumerate(BEST_MATCH_CRITERIAS):
            if criteria(k, current):
                results[i].append(v)
                break

    result = []
    for res in results:
        for elem in res:
            # negative limit = unbounded
            if len(result) == limit:
                return result
            result.append(elem)

    return result


def best_match(
    elems: t.Sequence[ChoiceT | ChoiceValueT], *, limit: int = AUTOCOMPLETE_LIMIT
):
    _verify_limit(limit)
    elems = _convert_to_choice_values(elems)

    async def autocomplete(ia: dc.Interaction, current: str) -> list[ChoiceT]:
        new_elems = _best_match(current, elems, limit)
        return _convert_to_choices(new_elems)

    return autocomplete


def paged(
    elems: t.Sequence[ChoiceT | ChoiceValueT],
    *,
    per_page_limit: int = AUTOCOMPLETE_LIMIT,
):
    _verify_limit(per_page_limit)
    elems = _convert_to_choice_values(elems)

    async def autocomplete(ia: dc.Interaction, current: str) -> list[ChoiceT]:
        page, reverse, _ = _get_page(current)
        new_elems = _open_page(elems, page, reverse, per_page_limit)
        return _convert_to_choices(new_elems)

    return autocomplete


def best_match_paged(
    elems: t.Sequence[ChoiceT | ChoiceValueT],
    *,
    per_page_limit: int = AUTOCOMPLETE_LIMIT,
):
    async def autocomplete(ia: dc.Interaction, current: str) -> list[ChoiceT]:
        _verify_limit(per_page_limit)
        new_elems = _convert_to_choice_values(elems)

        page, reverse, left = _get_page(current)
        new_elems = _best_match(left, new_elems, -1)
        new_elems = _open_page(new_elems, page, reverse, per_page_limit)
        return _convert_to_choices(new_elems)

    return autocomplete
