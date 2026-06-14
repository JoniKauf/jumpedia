import typing as t

from domain import errors
from domain.types.id import ID


class BaseEntity:
    def __init__(self, id: ID) -> None:
        if type(self) is BaseEntity:
            raise TypeError

        if id < 1:
            raise RuntimeError("ID must be higher than 0")

        self._id = id

    @property
    def id(self) -> ID:
        return self._id

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self.id)