from collections import defaultdict
import functools
import math
from numbers import Real
from typing import Any, Callable, Coroutine, Iterable
import discord as dc
from discord import app_commands as acmds
from discordtools import errors
from discord.app_commands.commands import Coro
import string

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
_PAGING_SUFFIX: str = ">"
_REVERSE_PAGING_SUFFIX: str = "<"
_MAX_PAGE_ORDER_OF_MAGNITUDE: int = 6
_BEST_MATCH_CRITERIAS: tuple[Callable[[str, str], bool], ...] = (
    lambda elem, current: elem == current,
    lambda elem, current: elem.startswith(current),
    _same_chars_contained
)

def _convert_to_choices(elems: Iterable[ChoiceValueT]) -> list[ChoiceT]:
    return [
        acmds.Choice(name=str(elem), value=elem) for elem in elems
    ]

def _verify_limit(limit: int):
    if limit > AUTOCOMPLETE_LIMIT:
        raise errors.ProgrammingError("discord limit of 25 choices surpassed")

    if limit < 1:
        raise errors.ProgrammingError("at least 1 element required for autocomplete")
    
def _save_ceildiv(a: int | float, b: int | float) -> int:
    return int(-(a // -b)) 

def _get_page(s: str) -> tuple[int, bool, str]:
    page = 1
    reverse = False
    left, _, n = s.rpartition(_PAGING_SUFFIX)

    if n.isdigit():
        if len(n) <= _MAX_PAGE_ORDER_OF_MAGNITUDE:
            page = int(n)
    else:
        left, _, n = s.rpartition(_REVERSE_PAGING_SUFFIX)
        
        if n.isdigit() and len(n) <= _MAX_PAGE_ORDER_OF_MAGNITUDE:
            page = int(n)
            reverse = True
    
    assert page >= 1

    return page, reverse, left.rstrip()

def _open_page(elems: Iterable[ChoiceValueT], page: int, reverse: bool, per_page_limit: int) -> tuple[ChoiceValueT, ...]:
    elems = tuple(elems)

    if len(elems) == 0 or len(elems) <= per_page_limit:
        return elems

    total_pages: int = _save_ceildiv(len(elems), per_page_limit)

    if reverse:
        start: int = total_pages - page
    else:
        start: int = (page - 1) * per_page_limit

    end: int = start + per_page_limit 

    return elems[start:end] or elems[:per_page_limit]


def _best_match(
    current: str,
    elems: Iterable[ChoiceValueT],
    limit: int
) -> list[ChoiceValueT]:
    results: list[list[ChoiceValueT]] = [[] for _ in range(3)]
    current = current.casefold()

    k_to_v: dict[str, ChoiceValueT] = {
        str(elem).casefold(): elem for elem in elems
    }

    for k, v in k_to_v.items():
        for i, criteria in enumerate(_BEST_MATCH_CRITERIAS):
            if criteria(k, current):
                results[i].append(v)
                break
    
    if limit < 0:
        return [elem for result in results for elem in result]
    
    result: list[ChoiceValueT] = []

    for res in results:
        for elem in res:
            if len(result) == limit:
                break
            result.append(elem)

    return result


def best_match(elems: Iterable[ChoiceValueT], *, limit: int = AUTOCOMPLETE_LIMIT):
    _verify_limit(limit)

    async def autocomplete(
        ia: dc.Interaction, 
        current: str
    ) -> list[ChoiceT]:
        new_elems = _best_match(current, elems, limit)
        return _convert_to_choices(new_elems)
            
    return autocomplete

def paged(
    elems: Iterable[ChoiceValueT], *, per_page_limit: int = AUTOCOMPLETE_LIMIT
):
    _verify_limit(per_page_limit)

    async def autocomplete(
        ia: dc.Interaction, 
        current: str
    ) -> list[ChoiceT]:
        page, reverse, _ = _get_page(current)
        new_elems = _open_page(elems, page, reverse, per_page_limit)
        return _convert_to_choices(new_elems)
    
    return autocomplete


def best_match_paged(elems: Iterable[ChoiceValueT], *, per_page_limit: int = AUTOCOMPLETE_LIMIT):
    async def autocomplete(
        ia: dc.Interaction,
        current: str
    ) -> list[ChoiceT]:
        page, reverse, left = _get_page(current)
        new_elems = _best_match(left, elems, -1)
        new_elems = _open_page(new_elems, page, reverse, per_page_limit)
        return _convert_to_choices(new_elems)
    
    return autocomplete