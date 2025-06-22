

import functools
from typing import Any


@functools.total_ordering
class Uniqueness:
    _value_mapping: dict[int, 'Uniqueness'] = {}

    def __init__(self, value: int) -> None:
        self.value = value

        if self.value in self.__class__._value_mapping:
            raise RuntimeError
        
        self.__class__._value_mapping[value] = self

    @classmethod
    def _init_cls(cls):
        cls.none = cls(0)
        cls.per_value = cls(1)

        for subcls in cls.__subclasses__():
            subcls._init_cls()
            
    def __lt__(self, other: Any):
        if isinstance(other, Uniqueness):
            return self.value < other.value
        
        return NotImplemented
    

@functools.total_ordering
class UniquenessExtended(Uniqueness):
    @classmethod
    def _init_cls(cls):
        cls.per_list = cls(2)


Uniqueness._init_cls()