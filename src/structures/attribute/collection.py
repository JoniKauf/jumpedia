

from dataclasses import field
from typing import Final, NamedTuple, Sequence, overload
from typing_extensions import Sentinel
from structures.attribute import BaseAttribute
from structures.attribute.slot_type import SlotTypeT
from structures import BaseStructure

# Collection
MAX_ENTRIES: Final[int] = 1024

class CollectionEntry[T: SlotTypeT](NamedTuple):
    id: int
    collection_index: int
    value: T
    aliases: frozenset[T]

class Collection[T: SlotTypeT](BaseStructure, Sequence[CollectionEntry[T]]):
    attribute: BaseAttribute[T]
    entries: tuple[CollectionEntry[T], ...]
    _syn_to_entry: dict[T, CollectionEntry[T]] = field(init=False, default_factory=dict)

    def __post_init__(self) -> None:
        for i, entry in enumerate(self.entries):
            if entry.collection_index != i:
                raise ValueError(f"Index in collection ({i!r}) is not equal to index of entry {entry.collection_index}")
            
            for syn in (entry.value, *entry.aliases):
                norm = self.attribute.slot_type.norm(syn)

                if norm in self._syn_to_entry:
                    raise ValueError(f"Normed value {norm!r} appeared twice in {self.entries!r}")
                
                self._syn_to_entry[norm] = entry

    @property
    def identity(self) -> tuple[int, ...]:
        return (0, *self.attribute.identity)

    def __len__(self) -> int:
        return self.entries.__len__()

    @overload
    def __getitem__(self, index: int) -> CollectionEntry[T]:
        ...

    @overload
    def __getitem__(self, index: slice[int, int, int]) -> tuple[CollectionEntry[T], ...]:
        ...

    def __getitem__(self, index: int | slice[int, int, int]) -> CollectionEntry[T] | tuple[CollectionEntry[T], ...]:
        return self.entries.__getitem__(index)
    
    _NO_DEFAULT = Sentinel('_NO_DEFAULT')

    @overload
    def get_entry_by_syn(self, syn: T, /) -> CollectionEntry[T]:
        ...

    @overload
    def get_entry_by_syn[TDefault](self, syn: T, /, default: TDefault) -> CollectionEntry[T] | TDefault:
        ...

    def get_entry_by_syn[TDefault](self, syn: T, /, default: TDefault = _NO_DEFAULT) -> CollectionEntry[T] | TDefault:
        norm = self.attribute.slot_type.norm(syn)

        if default is self.__class__._NO_DEFAULT:
            return self._syn_to_entry[norm]
        
        return self._syn_to_entry.get(norm, default)



    

    