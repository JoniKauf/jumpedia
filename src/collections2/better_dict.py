import collections2

class BetterDict[KT, VT](dict[KT, VT]):
    def key_at(self, index: int) -> KT:
        return collections2._get_iterable_index(self.keys(), index)
    
    def value_at(self, index: int) -> VT:
        return collections2._get_iterable_index(self.values(), index)
    
    def item_at(self, index: int) -> tuple[KT, VT]:
        return collections2._get_iterable_index(self.items(), index)