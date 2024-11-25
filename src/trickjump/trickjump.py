from enum import Enum, auto
from typing import Any, Optional, Sequence, overload, override
from dataclasses import dataclass

from trickjump import attributes as attrs
from discordtools.errors import AttributeMissingFeedbackError, FeedbackError, InvalidAttributeFeedbackError, SameAttributeFeedbackError
from trickjump import attributes
from trickjump.attributes import ATTR_ITEMS, AttrBase, Attributes, Generate
from discordtools import messagetools as msgt


type TrickjumpDataT = dict[str, Any]



@dataclass(init=False, slots=True, unsafe_hash=True)
class Trickjump(Attributes):
    def __init__(self, data: TrickjumpDataT, *, strict: bool = True, syns: bool = True) -> None:
        if syns:
            old_data, data = data, {}
            duplicates: dict[str, list[str]] = {}
            
            try:
                for k, v in old_data.items():
                    attr_name = attrs.syn_to_name(k)

                    duplicates.setdefault(attr_name, []).append(k)

                    if attr_name in data:
                        raise SameAttributeFeedbackError(attr_name, duplicates[attr_name])
                    
                    data[k] = v
            except KeyError:
                raise InvalidAttributeFeedbackError(k)
        
        missing: list[str] = []

        for name, cls in ATTR_ITEMS:
            if issubclass(cls, Generate):
                val = cls.generate(self)
            else:
                val = data.get(name, None)
            
            if strict and val is None and cls.REQUIRED:
                missing.append(name)
            
            setattr(self, name, cls.get(val))  # type: ignore

        if missing:
            raise AttributeMissingFeedbackError(missing)


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