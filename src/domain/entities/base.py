

from dataclasses import dataclass

@dataclass(kw_only=True, slots=True)
class BaseEntity:
    _id: int

    def __post_init__(self) -> None:
        if type(self) is BaseEntity:
            raise TypeError
        
    @property
    def id(self) -> int:
        return self._id
    
    def __eq__(self, other: object) -> bool:
        return isinstance(other, self.__class__) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)