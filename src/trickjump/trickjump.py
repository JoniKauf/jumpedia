from enum import Enum, auto
from typing import Any, Optional, Sequence, overload, override
from dataclasses import dataclass

from trickjump import attributes as attrs
from discordtools.errors import RequiredAttributesMissingFeedbackError, FeedbackError, InvalidAttributeFeedbackError, SameAttributeFeedbackError
from trickjump import attributes
from trickjump.attributes import ATTR_CLASSES, ATTR_ITEMS, Attr, AttributeComboClass, Finder, Taser, Prover
from discordtools import messagetools as msgt


type TrickjumpDataT = dict[str, Any]


class Trickjump(AttributeComboClass):
    ATTRS_ORDERED: tuple[type[Attr], ...] = tuple(elem for elem in ATTR_CLASSES if elem.USER_ATTR is not False)

    def as_info(self) -> str:
        return "\n".join(f"{elem.NAME}: {elem.value}" for elem in self.__dict__.values())
    
    # TODO: Fix issue that the attr could be of type multivalue

    def _ftp_to_line(self) -> str:
        def join_grammatically(elems: Sequence[str]):
            if len(elems) < 2:
                return ''.join(elems)
            return ', '.join(elems[:-1]) + f" & {elems[-1]}"
        
        MAP: dict[str, Any] = {
            "Found": self.get(Finder).unpacked, # type: ignore
            "Tased": self.get(Taser).unpacked,  # type: ignore
            "Proven": self.get(Prover).unpacked  # type: ignore
        }

        REV_MAP: dict[Optional[tuple[str, ...]], list[str]] = {}

        for title, value in MAP.items():
            REV_MAP.setdefault(value, []).append(title)

        # Remove empty values
        REV_MAP.pop(None, None)
        REV_MAP.pop((), None)

        return ', '.join(
            f"{join_grammatically(titles)} by {join_grammatically(value)}"  # type: ignore
            for value, titles in REV_MAP.items()
        )