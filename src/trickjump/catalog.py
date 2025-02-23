import ast
from dataclasses import astuple
import sys
from typing import Any, Callable, Iterable, Literal, Optional, Self, Sequence, TypeAlias, cast, get_args, TYPE_CHECKING
from discordtools import feedbackerrors as fbe
from trickjump import attributes
from trickjump.trickjump import Trickjump

class FilterSyntaxError(Exception):
    pass


class Catalog(list[Trickjump]):

    AttrT: TypeAlias = str
    KeyT: TypeAlias = str | Trickjump
    
    _RAISE_KEY_ERROR = object()

    def __init__(self, data: Optional[Iterable[Trickjump]] = None):
        super().__init__(data or ())

    @classmethod
    def get_all_trickjumps(cls, **tj_kwargs: Any) -> Self:
        ...

    def sort(self, bad_attrs: Optional[Sequence[str]] = None) -> None:
        """
        Sorts the base defined by the attributes specified with priority.
        """
        
        # No sorting required for 0 or 1 elems or no sorting requirements
        if not bad_attrs or len(self) <= 1:
            return
        
        SIGN_SYMBOL = "-"
        attrs_sign: dict[type[AttrBase], Literal[1, -1]] = {}

        for attr in bad_attrs:
            try:
                attr_cls = attributes.syn_to_cls(attr.removeprefix(SIGN_SYMBOL).casefold())
            except KeyError:
                raise InvalidAttributeFeedbackError(attr)
            
            attrs_sign[attr_cls] = -1 if attr.startswith(SIGN_SYMBOL) else +1

        
        def get_sort_val(jump: Trickjump) -> tuple:
            return tuple(jump.get_by_name(attr_cls).sort_key(sign) for attr_cls, sign in attrs_sign.items())
        
        super().sort(key=get_sort_val)


    def get_yield(self, bad_attrs: Optional[Sequence[AttrT]], replace: Callable[[Any], Any]) -> list[tuple[Any, ...]]:
        attrs = Catalog._resolve_bad_attrs(bad_attrs, [attributes.Name])

        yield_ = []
        
        for tj in self:
            values: tuple[AttrBase, ...] = astuple(tj)
            
            yield_.append(
                tuple(replace(v.value) for v in values)
            )
        
        return yield_