import typing as t
from dataclasses import dataclass, field

from typing_extensions import Sentinel

from utils import text

from .slot_str import SlotStr

if t.TYPE_CHECKING:
    from . import BaseAttribute

# Collection
MAX_ENTRIES: t.Final[int] = 1024


class CollectionEntry(t.NamedTuple):
    id: int
    collection_index: int
    value: SlotStr
    aliases: frozenset[SlotStr]


@dataclass(frozen=True, slots=True)
class Collection(t.Sequence[CollectionEntry]):
    attribute: BaseAttribute
    entries: tuple[CollectionEntry, ...]
    _syn_to_entry: dict[text.NormStr, CollectionEntry] = field(
        init=False, default_factory=dict
    )

    def __post_init__(self) -> None:
        for i, entry in enumerate(self.entries):
            if entry.collection_index != i:
                raise ValueError(
                    f"Index in collection ({i!r}) is not equal to index of entry {entry.collection_index}"
                )

            for syn in (entry.value, *entry.aliases):
                norm_syn = text.NormStr(syn)

                if norm_syn in self._syn_to_entry:
                    raise ValueError(
                        f"Normed value {norm_syn!r} appeared twice in {self.entries!r}"
                    )

                self._syn_to_entry[norm_syn] = entry

    def __len__(self) -> int:
        return self.entries.__len__()

    @t.overload
    def __getitem__(self, index: int) -> CollectionEntry: ...

    @t.overload
    def __getitem__(
        self, index: slice[int, int, int]
    ) -> tuple[CollectionEntry, ...]: ...

    def __getitem__(self, index) -> CollectionEntry | tuple[CollectionEntry, ...]:
        return self.entries.__getitem__(index)

    _NO_DEFAULT = Sentinel("_NO_DEFAULT")

    @t.overload
    def get_entry_by_syn(self, norm_syn: text.NormStr, /) -> CollectionEntry: ...

    @t.overload
    def get_entry_by_syn[TDefault](
        self, norm_syn: text.NormStr, /, default: TDefault
    ) -> CollectionEntry | TDefault: ...

    def get_entry_by_syn[TDefault](
        self, norm_syn: text.NormStr, /, default: TDefault = _NO_DEFAULT
    ) -> CollectionEntry | TDefault:
        if default is self.__class__._NO_DEFAULT:
            return self._syn_to_entry[norm_syn]

        return self._syn_to_entry.get(norm_syn, default)

    def __eq__(self, value: object) -> bool:
        if self.__class__ is not value.__class__:
            return NotImplemented

        return self.attribute.id == value.attribute.id  # type: ignore

    def __hash__(self) -> int:
        return hash(self.attribute.id)
