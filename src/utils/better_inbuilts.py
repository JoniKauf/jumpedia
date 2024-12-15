

from typing import Iterable


def _get_iterable_index[T](iterable: Iterable[T], index: int) -> T:
    if index < 0:
        return tuple(iterable)[index]
    
    iterator = iter(iterable)

    try:
        for _ in range(index + 1):
            value: T = next(iterator)
    except StopIteration:
        raise IndexError("Index out of range") from None
    
    return value  # type: ignore


class BetterSet[T](set[T]):
    def at(self, index: int) -> T:
        return _get_iterable_index(self, index)
    
    def freeze(self) -> frozenset[T]:
        return frozenset(self)
    
class BetterDict[KT, VT](dict[KT, VT]):
    def key_at(self, index: int) -> KT:
        return _get_iterable_index(self.keys(), index)
    
    def value_at(self, index: int) -> VT:
        return _get_iterable_index(self.values(), index)
    
    def item_at(self, index: int) -> tuple[KT, VT]:
        return _get_iterable_index(self.items(), index)