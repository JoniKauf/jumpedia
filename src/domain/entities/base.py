

from dataclasses import dataclass

@dataclass(slots=True)
class BaseEntity:
    _id: int | None

    def __post_init__(self) -> None:
        if type(self) is BaseEntity:
            raise TypeError
        
    @property
    def id(self) -> int:
        if self._id is None:
            raise RuntimeError("ID not set")
        
        return self._id
    
    def __eq__(self, other: object) -> bool:
        assert self._id is not None

        if not isinstance(other, self.__class__):
            return False
        return self._id == other._id

    def __hash__(self) -> int:
        assert self._id is not None

        return hash(self.id)