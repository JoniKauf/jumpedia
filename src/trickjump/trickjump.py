from enum import Enum, auto
from typing import Any, Optional, Sequence, overload, override
from dataclasses import dataclass

from trickjump import attributes as attrs
from discordtools.errors import RequiredAttributesMissingFeedbackError, FeedbackError, InvalidAttributeFeedbackError, SameAttributeFeedbackError
from trickjump import attributes
from trickjump.attributes import ATTR_ITEMS, AttrBase, Attributes, Generate
from discordtools import messagetools as msgt


type TrickjumpDataT = dict[str, Any]



@dataclass(init=False, slots=True, unsafe_hash=True)
class Trickjump(Attributes):
    def __init__(self, data: TrickjumpDataT, *, required: bool = True, syns: bool = True, cf: bool = True) -> None:
        if not syns:
            if cf:
                same: set[str] = set()

                for name in data:
                    casefolded: str = name.casefold()
                    
                    if casefolded in same:
                        raise SameAttributeFeedbackError(casefolded)
                    
                    same.add(casefolded)

            new_data: TrickjumpDataT = data
        else:
            new_data: TrickjumpDataT = {}

            for syn, val in data.items():
                try:
                    name = attributes.syn_to_name(syn, cf)
                except KeyError:
                    raise InvalidAttributeFeedbackError(syn)

                if name in new_data:
                    raise SameAttributeFeedbackError(name)
                
                new_data[name] = val

        missing: set[str] = set()
        
        for attr in attributes.ATTR_CLASSES:
            try:
                val = new_data[attr.NAME]
            except KeyError:
                if required:
                    missing.add(attr.NAME)
                continue

            setattr(self, attr.NAME, attr.get(val))  # type: ignore

        if missing:
            raise RequiredAttributesMissingFeedbackError(tuple(missing))


    def as_info(self) -> str:
        ...
    

    def _ftp_to_line(self) -> str:
        def join_humanly(elems: Sequence[str]):
            if len(elems) < 2:
                return ''.join(elems)
            return ', '.join(elems[:-1]) + f" & {elems[-1]}"
        
        MAP: dict[str, Any] = {
            "Found": self.finder.unpacked,
            "Tased": self.taser.unpacked,
            "Proven": self.prover.unpacked
        }

        REV_MAP: dict[Optional[tuple[str, ...]], list[str]] = {}

        for title, value in MAP.items():
            REV_MAP.setdefault(value, []).append(title)

        # Remove empty values
        REV_MAP.pop(None, None)
        REV_MAP.pop((), None)

        return ', '.join(
            f"{join_humanly(titles)} by {join_humanly(value)}"  # type: ignore
            for value, titles in REV_MAP.items()
        )