from dataclasses import field
from typing import Final, NamedTuple, Sequence, overload
from discord import TYPE_CHECKING
from typing_extensions import Sentinel
from structures.attribute.slot_type import TypeStr
from structures import BaseStructure
from utils import text

if TYPE_CHECKING:
    from structures.attribute import BaseAttribute

# Collection
MAX_ENTRIES: Final[int] = 1024


class CollectionEntry(NamedTuple):
    id: int
    collection_index: int
    value: TypeStr
    aliases: frozenset[TypeStr]


class Collection(BaseStructure, Sequence[CollectionEntry]):
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
                norm = text.raw_to_norm(syn)

                if norm in self._syn_to_entry:
                    raise ValueError(
                        f"Normed value {norm!r} appeared twice in {self.entries!r}"
                    )

                self._syn_to_entry[norm] = entry

    @property
    def identity(self) -> tuple[int, ...]:
        return (0, *self.attribute.identity)

    def __len__(self) -> int:
        return self.entries.__len__()

    @overload
    def __getitem__(self, index: int) -> CollectionEntry: ...

    @overload
    def __getitem__(
        self, index: slice[int, int, int]
    ) -> tuple[CollectionEntry, ...]: ...

    def __getitem__(
        self, index: int | slice[int, int, int]
    ) -> CollectionEntry | tuple[CollectionEntry, ...]:
        return self.entries.__getitem__(index)

    _NO_DEFAULT = Sentinel("_NO_DEFAULT")

    @overload
    def get_entry_by_syn(self, syn: str, /) -> CollectionEntry: ...

    @overload
    def get_entry_by_syn[TDefault](
        self, syn: str, /, default: TDefault
    ) -> CollectionEntry | TDefault: ...

    def get_entry_by_syn[TDefault](
        self, syn: str, /, default: TDefault = _NO_DEFAULT
    ) -> CollectionEntry | TDefault:
        norm = text.raw_to_norm(syn)

        if default is self.__class__._NO_DEFAULT:
            return self._syn_to_entry[norm]

        return self._syn_to_entry.get(norm, default)
