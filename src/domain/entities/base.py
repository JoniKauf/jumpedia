

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BaseEntity:
    id: int

    def __eq__(self, other: object) -> bool:
        return isinstance(other, self.__class__) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)