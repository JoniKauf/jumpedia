from typing import Iterable

class Counter:
    def __init__(self, start: int = 0, step: int = 1) -> None:
        self.n = self.start = start
        self.step = step

    def next(self) -> int:
        ret = self.n
        self.n += self.step
        return ret
    
    def __call__(self) -> int:
        return self.next()

    def reset(self) -> None:
        self.n = self.start



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