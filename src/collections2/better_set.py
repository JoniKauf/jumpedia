import collections2

class BetterSet[T](set[T]):
    def at(self, index: int) -> T:
        return collections2._get_iterable_index(self, index)
    
    def freeze(self) -> frozenset[T]:
        return frozenset(self)